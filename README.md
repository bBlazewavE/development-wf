# AI Dev Workflow

A complete AI-powered development environment for macOS. One command sets up Neovim, Claude Code, Pi, Ralph, tmux, and all supporting tools.

## Quick Start

### Clone and install

```bash
git clone https://github.com/bBlazewavE/development-wf.git ~/.development-wf
cd ~/.development-wf && chmod +x install.sh && ./install.sh
source ~/.zshrc
```

### One-liner (curl)

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/bBlazewavE/development-wf/main/install.sh)
```

> **Note:** The one-liner requires the repo to be cloned first for symlinks to work. Use the clone method above for a full install.

## What Gets Installed

| Tool | Purpose | Installed via |
|------|---------|--------------|
| **Neovim** | Primary editor with LSP, completion, fuzzy finding | Homebrew |
| **tmux** | Terminal multiplexer for multi-pane sessions | Homebrew |
| **Claude Code** | AI coding assistant (CLI) | npm |
| **Pi** | AI coding agent | npm |
| **Ralph** | AI task orchestrator | git clone |
| **lazygit** | Terminal UI for git | Homebrew |
| **fzf** | Fuzzy finder (files, history, dirs) | Homebrew |
| **fd** | Fast file finder (used by fzf/Telescope) | Homebrew |
| **ripgrep** | Fast text search (used by Telescope) | Homebrew |
| **yazi** | Terminal file manager | Homebrew |
| **Starship** | Cross-shell prompt | Homebrew |
| **gh** | GitHub CLI | Homebrew |
| **Node.js** | Required for npm packages & LSP servers | Homebrew |

## Components

### Neovim

Full IDE-like config with lazy.nvim plugin manager. Plugins auto-install on first launch.

**Plugins included:**
- **Theme:** Catppuccin Mocha
- **LSP:** Mason + nvim-lspconfig (auto-installs servers for Lua, Python, TypeScript, Go, Rust, HTML, CSS, JSON, YAML, Bash)
- **Completion:** nvim-cmp with LSP, buffer, path, and snippet sources
- **Fuzzy finding:** Telescope with fzf-native
- **Treesitter:** Syntax highlighting, text objects, incremental selection
- **File tree:** Neo-tree
- **Git:** Gitsigns (inline diff markers)
- **UI:** Bufferline, Lualine, Which-key, dressing.nvim, nvim-notify
- **Editing:** Autopairs, Comment.nvim, nvim-surround, indent-blankline
- **Other:** Smart-splits, auto-save (off by default, toggle with `:ASToggle`)

### tmux

- **Prefix:** `Ctrl-a` (not the default `Ctrl-b`)
- **Mouse:** Enabled (scroll, click, resize)
- **True color:** Configured for 256-color terminals
- **Catppuccin-matching status bar**

### Shell (zsh)

A marker-delimited block is appended to `~/.zshrc` (your existing config is preserved). Includes:
- `EDITOR` / `VISUAL` set to nvim
- fzf shell integration
- Starship prompt
- Aliases and the `dev` function

### Ralph

AI task orchestrator cloned to `~/.local/share/ralph`, symlinked to `~/.local/bin/ralph`.

### Claude Code

Anthropic's CLI AI assistant. After install, set your API key:
```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

### Pi

AI coding agent by mariozechner. Run with `pi` after install.

## Shortcuts & Aliases

### Shell

| Command | Action |
|---------|--------|
| `dev` | Launch tmux session with Neovim + Claude + lazygit + shell |
| `dev myproject` | Same, with custom session name |
| `v` | `nvim` |
| `lg` | `lazygit` |
| `y` | `yazi` |
| `cc` | `claude` |

### tmux

| Key | Action |
|-----|--------|
| `Ctrl-a \|` | Split pane horizontally |
| `Ctrl-a -` | Split pane vertically |
| `Alt-Arrow` | Navigate panes (no prefix) |
| `Ctrl-a c` | New window |
| `Ctrl-a r` | Reload tmux config |

### Neovim

| Key | Action |
|-----|--------|
| `Space` | Leader key |
| `Space e` | Toggle file tree |
| `Space ff` | Find files |
| `Space fg` | Live grep |
| `Space fb` | Find buffers |
| `Space fr` | Recent files |
| `Shift-H/L` | Previous/next buffer |
| `gd` | Go to definition |
| `gr` | Go to references |
| `K` | Hover docs |
| `Space ca` | Code action |
| `Space rn` | Rename symbol |
| `Space d` | Show diagnostics |
| `gc` | Toggle comment |
| `Ctrl-s` | Save file |

## Incident Resolution Playbook

### Neovim plugins fail to install
```bash
rm -rf ~/.local/share/nvim/lazy
nvim  # lazy.nvim will re-bootstrap
```

### LSP server not starting
```bash
# Inside Neovim:
:Mason          # Check server status
:LspInfo        # Check attached clients
:LspLog         # View error logs
```

### tmux not using correct colors
Ensure your terminal emulator supports true color and is set to `xterm-256color`. Add to terminal settings if needed:
```bash
export TERM=xterm-256color
```

### Claude Code not found
```bash
npm list -g @anthropic-ai/claude-code  # Check installation
which claude                            # Check PATH
source ~/.zshrc                         # Reload shell
```

### Ralph not found
```bash
ls -la ~/.local/bin/ralph               # Check symlink
ls ~/.local/share/ralph/ralph.sh        # Check source
echo $PATH | tr ':' '\n' | grep local  # Verify PATH includes ~/.local/bin
```

## Updating

All configs are symlinked, so pulling the repo updates everything:
```bash
cd ~/.development-wf
git pull
```

For tool updates:
```bash
brew upgrade
npm update -g @anthropic-ai/claude-code @mariozechner/pi-coding-agent
```

## Uninstalling

```bash
# Remove symlinks
rm ~/.config/nvim ~/.tmux.conf

# Remove zshrc block (between the >>> and <<< markers)
# Edit ~/.zshrc and delete the block between:
#   # >>> development-wf >>>
#   # <<< development-wf <<<

# Remove installed data
rm -rf ~/.local/share/nvim/lazy    # Neovim plugins
rm -rf ~/.local/share/ralph        # Ralph
rm ~/.local/bin/ralph              # Ralph symlink

# Remove the repo
rm -rf ~/.development-wf
```

## Troubleshooting

**Icons look broken?** Install a Nerd Font:
```bash
brew install --cask font-jetbrains-mono-nerd-font
```
Then set it as your terminal's font.

**Telescope grep not working?** Ensure ripgrep is installed:
```bash
brew install ripgrep
```

**fzf keybindings not working?** Make sure `source <(fzf --zsh)` runs after Oh My Zsh is sourced in your `.zshrc`.

## License

MIT
