#!/usr/bin/env python3
"""Orchestrator: async plan-and-execute pipeline via Anthropic API.

Dispatches tasks to a thinking model for planning, then to a smaller model
for execution. All work happens in background processes — the CLI never blocks.

State: flat JSON files in ~/.local/share/shellsmith/orchestrator/tasks/<id>.json
Logs:  ~/.local/share/shellsmith/orchestrator/logs/<id>-{plan,execute}.log
"""

import argparse
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import yaml

# ── paths ────────────────────────────────────────────────────────────────────
DATA_DIR = Path.home() / ".local" / "share" / "shellsmith" / "orchestrator"
TASKS_DIR = DATA_DIR / "tasks"
LOGS_DIR = DATA_DIR / "logs"
PIPELINE_DIR = Path(__file__).resolve().parent / "pipelines"
DEFAULT_PIPELINE = "plan-execute"

# ── pipeline config ─────────────────────────────────────────────────────────
def load_pipeline(name=DEFAULT_PIPELINE):
    path = PIPELINE_DIR / f"{name}.yaml"
    if not path.exists():
        die(f"Pipeline config not found: {path}")
    with open(path) as f:
        return yaml.safe_load(f)


def get_model(step_name, pipeline):
    """Return model ID for a pipeline step, respecting env var overrides."""
    env_map = {"plan": "ORCH_PLANNER_MODEL", "execute": "ORCH_EXECUTOR_MODEL"}
    env_var = env_map.get(step_name)
    if env_var and os.environ.get(env_var):
        return os.environ[env_var]
    for step in pipeline["steps"]:
        if step["name"] == step_name:
            return step["model"]
    die(f"Unknown step: {step_name}")


def get_step(step_name, pipeline):
    for step in pipeline["steps"]:
        if step["name"] == step_name:
            return step
    die(f"Unknown step: {step_name}")


# ── task state ───────────────────────────────────────────────────────────────
def ensure_dirs():
    TASKS_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)


def task_path(task_id):
    return TASKS_DIR / f"{task_id}.json"


def save_task(task):
    """Atomic write: tmp file + rename."""
    ensure_dirs()
    path = task_path(task["id"])
    fd, tmp = tempfile.mkstemp(dir=TASKS_DIR, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(task, f, indent=2)
        os.rename(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def load_task(task_id):
    path = task_path(task_id)
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def all_tasks():
    ensure_dirs()
    tasks = []
    for p in sorted(TASKS_DIR.glob("*.json")):
        try:
            with open(p) as f:
                tasks.append(json.load(f))
        except (json.JSONDecodeError, OSError):
            continue
    return tasks


def resolve_id(prefix):
    """Resolve a task ID by prefix match."""
    ensure_dirs()
    matches = [p.stem for p in TASKS_DIR.glob("*.json") if p.stem.startswith(prefix)]
    if len(matches) == 1:
        return matches[0]
    if len(matches) == 0:
        die(f"No task matching prefix: {prefix}")
    if prefix in matches:
        return prefix
    die(f"Ambiguous prefix '{prefix}', matches: {', '.join(matches[:5])}")


def new_task(description):
    task_id = uuid.uuid4().hex[:8]
    now = datetime.now(timezone.utc).isoformat()
    return {
        "id": task_id,
        "description": description,
        "status": "planning",
        "created_at": now,
        "updated_at": now,
        "plan": None,
        "result": None,
        "planner_pid": None,
        "executor_pid": None,
        "error": None,
    }


# ── helpers ──────────────────────────────────────────────────────────────────
def die(msg):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def pid_alive(pid):
    """Check if a PID is still running."""
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False


def check_api_key():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        die("ANTHROPIC_API_KEY not set. Export it before running orchestrator commands.")


def tmux_notify(msg):
    """Send a tmux display-message notification (non-fatal if tmux isn't running)."""
    try:
        subprocess.run(
            ["tmux", "display-message", "-d", "5000", f"[orch] {msg}"],
            capture_output=True,
            timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass


def detect_stale(task):
    """If a worker PID is recorded but dead, mark the task as failed."""
    changed = False
    if task["status"] == "planning" and task.get("planner_pid"):
        if not pid_alive(task["planner_pid"]):
            task["status"] = "failed"
            task["error"] = "Planner process died unexpectedly"
            task["updated_at"] = datetime.now(timezone.utc).isoformat()
            changed = True
    if task["status"] == "executing" and task.get("executor_pid"):
        if not pid_alive(task["executor_pid"]):
            task["status"] = "failed"
            task["error"] = "Executor process died unexpectedly"
            task["updated_at"] = datetime.now(timezone.utc).isoformat()
            changed = True
    if changed:
        save_task(task)
    return task


def format_status(task):
    status = task["status"]
    tid = task["id"]
    desc = task["description"][:60]
    if len(task["description"]) > 60:
        desc += "..."
    worker = ""
    if status == "planning" and task.get("planner_pid"):
        alive = pid_alive(task["planner_pid"])
        worker = f" (pid {task['planner_pid']}, {'alive' if alive else 'dead'})"
    elif status == "executing" and task.get("executor_pid"):
        alive = pid_alive(task["executor_pid"])
        worker = f" (pid {task['executor_pid']}, {'alive' if alive else 'dead'})"
    return f"  {tid}  {status:<12} {desc}{worker}"


# ── commands ─────────────────────────────────────────────────────────────────
def cmd_run(args):
    check_api_key()
    task = new_task(args.task)
    save_task(task)

    log_path = LOGS_DIR / f"{task['id']}-plan.log"
    log_file = open(log_path, "w")

    proc = subprocess.Popen(
        [sys.executable, __file__, "_plan", task["id"]],
        start_new_session=True,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        env={**os.environ},
    )

    task["planner_pid"] = proc.pid
    save_task(task)

    print(f"Task {task['id']} created — planning in background (pid {proc.pid})")
    print(f"  {task['description']}")
    print(f"  Run: orch status")


def cmd_status(args):
    tasks = all_tasks()
    if not tasks:
        print("No tasks.")
        return
    tasks = [detect_stale(t) for t in tasks]
    print("Tasks:")
    for t in sorted(tasks, key=lambda t: t["created_at"], reverse=True):
        print(format_status(t))


def cmd_show(args):
    task_id = resolve_id(args.id)
    task = load_task(task_id)
    if not task:
        die(f"Task not found: {task_id}")
    task = detect_stale(task)

    print(f"Task:    {task['id']}")
    print(f"Status:  {task['status']}")
    print(f"Created: {task['created_at']}")
    print(f"Updated: {task['updated_at']}")
    print()
    print("--- Description ---")
    print(task["description"])

    if task.get("error"):
        print()
        print("--- Error ---")
        print(task["error"])

    if task.get("plan"):
        print()
        print("--- Plan ---")
        print(task["plan"])

    if task.get("result"):
        print()
        print("--- Result ---")
        print(task["result"])


def cmd_approve(args):
    check_api_key()
    task_id = resolve_id(args.id)
    task = load_task(task_id)
    if not task:
        die(f"Task not found: {task_id}")

    if task["status"] != "planned":
        die(f"Task {task_id} is '{task['status']}', must be 'planned' to approve")

    task["status"] = "executing"
    task["updated_at"] = datetime.now(timezone.utc).isoformat()
    save_task(task)

    log_path = LOGS_DIR / f"{task_id}-execute.log"
    log_file = open(log_path, "w")

    proc = subprocess.Popen(
        [sys.executable, __file__, "_execute", task_id],
        start_new_session=True,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        env={**os.environ},
    )

    task["executor_pid"] = proc.pid
    save_task(task)

    print(f"Task {task_id} approved — executing in background (pid {proc.pid})")


def cmd_cancel(args):
    task_id = resolve_id(args.id)
    task = load_task(task_id)
    if not task:
        die(f"Task not found: {task_id}")

    if task["status"] in ("completed", "cancelled"):
        die(f"Task {task_id} is already '{task['status']}'")

    # Kill worker if running
    for pid_key in ("planner_pid", "executor_pid"):
        pid = task.get(pid_key)
        if pid and pid_alive(pid):
            try:
                os.killpg(os.getpgid(pid), signal.SIGTERM)
                print(f"  Sent SIGTERM to process group of pid {pid}")
            except (ProcessLookupError, PermissionError):
                pass

    task["status"] = "cancelled"
    task["updated_at"] = datetime.now(timezone.utc).isoformat()
    save_task(task)
    print(f"Task {task_id} cancelled.")


def cmd_logs(args):
    task_id = resolve_id(args.id)
    task = load_task(task_id)
    if not task:
        die(f"Task not found: {task_id}")

    for suffix in ("plan", "execute"):
        log_path = LOGS_DIR / f"{task_id}-{suffix}.log"
        if log_path.exists():
            print(f"=== {suffix} log ===")
            print(log_path.read_text())
            print()


# ── background workers ───────────────────────────────────────────────────────
def cmd_plan(args):
    """Internal: called as a background worker to run the planner."""
    import anthropic

    task_id = args.id
    task = load_task(task_id)
    if not task:
        print(f"Task not found: {task_id}", file=sys.stderr)
        sys.exit(1)

    pipeline = load_pipeline()
    step = get_step("plan", pipeline)
    model = get_model("plan", pipeline)

    print(f"[plan] Starting planner for task {task_id}")
    print(f"[plan] Model: {model}")
    print(f"[plan] Task: {task['description']}")

    try:
        client = anthropic.Anthropic()
        response = client.messages.create(
            model=model,
            max_tokens=step.get("max_tokens", 4096),
            system=step["system_prompt"].strip(),
            messages=[{"role": "user", "content": task["description"]}],
        )
        plan_text = response.content[0].text

        task = load_task(task_id)  # re-read in case of concurrent update
        task["plan"] = plan_text
        task["status"] = "planned"
        task["planner_pid"] = None
        task["updated_at"] = datetime.now(timezone.utc).isoformat()
        save_task(task)

        print(f"[plan] Done — status set to 'planned'")
        tmux_notify(f"Task {task_id} planned — run: orch show {task_id}")

    except Exception as e:
        error_type = type(e).__name__
        task = load_task(task_id)
        task["status"] = "failed"
        task["error"] = f"{error_type}: {e}"
        task["planner_pid"] = None
        task["updated_at"] = datetime.now(timezone.utc).isoformat()
        save_task(task)

        print(f"[plan] Failed: {error_type}: {e}", file=sys.stderr)
        tmux_notify(f"Task {task_id} FAILED: {error_type}")
        sys.exit(1)


def cmd_execute(args):
    """Internal: called as a background worker to run the executor."""
    import anthropic

    task_id = args.id
    task = load_task(task_id)
    if not task:
        print(f"Task not found: {task_id}", file=sys.stderr)
        sys.exit(1)

    if not task.get("plan"):
        print(f"Task {task_id} has no plan", file=sys.stderr)
        sys.exit(1)

    pipeline = load_pipeline()
    step = get_step("execute", pipeline)
    model = get_model("execute", pipeline)

    print(f"[execute] Starting executor for task {task_id}")
    print(f"[execute] Model: {model}")

    user_message = (
        f"## Task\n{task['description']}\n\n"
        f"## Approved Plan\n{task['plan']}"
    )

    try:
        client = anthropic.Anthropic()
        response = client.messages.create(
            model=model,
            max_tokens=step.get("max_tokens", 8192),
            system=step["system_prompt"].strip(),
            messages=[{"role": "user", "content": user_message}],
        )
        result_text = response.content[0].text

        task = load_task(task_id)
        task["result"] = result_text
        task["status"] = "completed"
        task["executor_pid"] = None
        task["updated_at"] = datetime.now(timezone.utc).isoformat()
        save_task(task)

        print(f"[execute] Done — status set to 'completed'")
        tmux_notify(f"Task {task_id} completed — run: orch show {task_id}")

    except Exception as e:
        error_type = type(e).__name__
        task = load_task(task_id)
        task["status"] = "failed"
        task["error"] = f"{error_type}: {e}"
        task["executor_pid"] = None
        task["updated_at"] = datetime.now(timezone.utc).isoformat()
        save_task(task)

        print(f"[execute] Failed: {error_type}: {e}", file=sys.stderr)
        tmux_notify(f"Task {task_id} FAILED: {error_type}")
        sys.exit(1)


# ── CLI ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        prog="orch",
        description="Async plan-and-execute orchestrator",
    )
    sub = parser.add_subparsers(dest="command")

    p_run = sub.add_parser("run", help="Submit a new task for planning")
    p_run.add_argument("task", help="Task description")

    p_status = sub.add_parser("status", help="List all tasks")

    p_show = sub.add_parser("show", help="Show task details")
    p_show.add_argument("id", help="Task ID (prefix match supported)")

    p_approve = sub.add_parser("approve", help="Approve plan and start execution")
    p_approve.add_argument("id", help="Task ID")

    p_cancel = sub.add_parser("cancel", help="Cancel a task")
    p_cancel.add_argument("id", help="Task ID")

    p_logs = sub.add_parser("logs", help="Show task log files")
    p_logs.add_argument("id", help="Task ID")

    # Internal worker commands (not shown in help)
    p_plan = sub.add_parser("_plan")
    p_plan.add_argument("id")

    p_exec = sub.add_parser("_execute")
    p_exec.add_argument("id")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    dispatch = {
        "run": cmd_run,
        "status": cmd_status,
        "show": cmd_show,
        "approve": cmd_approve,
        "cancel": cmd_cancel,
        "logs": cmd_logs,
        "_plan": cmd_plan,
        "_execute": cmd_execute,
    }

    dispatch[args.command](args)


if __name__ == "__main__":
    main()
