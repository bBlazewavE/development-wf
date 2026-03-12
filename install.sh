#!/usr/bin/env bash
set -euo pipefail

# ── Colors ────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

info()    { echo -e "${BLUE}[INFO]${NC} $*"; }
success() { echo -e "${GREEN}[OK]${NC}   $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }
error()   { echo -e "${RED}[ERR]${NC}  $*"; exit 1; }

BACKUPS=()
INSTALLED=()

# ── 1. Verify macOS ──────────────────────────────────────────────────
[[ "$(uname)" == "Darwin" ]] || error "This installer only supports macOS."
success "macOS detected ($(sw_vers -productVersion))"

# ── 2. Xcode CLI tools ──────────────────────────────────────────────
if ! xcode-select -p &>/dev/null; then
  info "Installing Xcode Command Line Tools..."
  xcode-select --install
  echo "Press Enter after the Xcode installer finishes."
  read -r
  INSTALLED+=("Xcode CLI Tools")
else
  success "Xcode CLI Tools already installed"
fi

# ── 3. Homebrew ──────────────────────────────────────────────────────
if ! command -v brew &>/dev/null; then
  info "Installing Homebrew..."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  # Add brew to current session PATH
  if [[ -f /opt/homebrew/bin/brew ]]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
  elif [[ -f /usr/local/bin/brew ]]; then
    eval "$(/usr/local/bin/brew shellenv)"
  fi
  INSTALLED+=("Homebrew")
else
  success "Homebrew already installed"
fi

# ── 4. Brew packages ────────────────────────────────────────────────
BREW_PACKAGES=(tmux fd fzf lazygit yazi starship neovim ripgrep gh node)
info "Installing brew packages: ${BREW_PACKAGES[*]}"
for pkg in "${BREW_PACKAGES[@]}"; do
  if brew list "$pkg" &>/dev/null; then
    success "$pkg already installed"
  else
    info "Installing $pkg..."
    brew install "$pkg"
    INSTALLED+=("$pkg")
  fi
done

# ── 5. npm packages ─────────────────────────────────────────────────
NPM_PACKAGES=("@anthropic-ai/claude-code" "@anthropic-ai/claude-code-mcp" "@anthropic-ai/claude-code-sdk" "@anthropic-ai/claude-code-hooks" "@mariozechner/pi-coding-agent")
info "Installing npm packages..."
for pkg in "${NPM_PACKAGES[@]}"; do
  if npm list -g "$pkg" &>/dev/null 2>&1; then
    success "$pkg already installed"
  else
    info "Installing $pkg..."
    npm install -g "$pkg"
    INSTALLED+=("$pkg")
  fi
done

# ── 6. Ralph ─────────────────────────────────────────────────────────
RALPH_DIR="$HOME/.local/share/ralph"
RALPH_BIN="$HOME/.local/bin/ralph"
mkdir -p "$HOME/.local/bin"

if [[ -d "$RALPH_DIR" ]]; then
  success "Ralph already cloned at $RALPH_DIR"
else
  info "Cloning Ralph..."
  git clone https://github.com/cyanheads/ralph.git "$RALPH_DIR"
  INSTALLED+=("Ralph")
fi

if [[ -L "$RALPH_BIN" ]] && [[ "$(readlink "$RALPH_BIN")" == "$RALPH_DIR/ralph.sh" ]]; then
  success "Ralph symlink already correct"
else
  ln -sf "$RALPH_DIR/ralph.sh" "$RALPH_BIN"
  chmod +x "$RALPH_DIR/ralph.sh"
  success "Ralph symlinked to $RALPH_BIN"
fi

# ── 7. Config deployment ────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"

backup_and_link() {
  local source="$1"
  local target="$2"

  # If symlink already points to correct target, skip
  if [[ -L "$target" ]] && [[ "$(readlink "$target")" == "$source" ]]; then
    success "Symlink already correct: $target"
    return
  fi

  # Backup existing file/dir if it exists and is not a symlink to us
  if [[ -e "$target" ]] || [[ -L "$target" ]]; then
    local backup="${target}.backup.${TIMESTAMP}"
    mv "$target" "$backup"
    warn "Backed up $target → $backup"
    BACKUPS+=("$backup")
  fi

  # Create parent directory if needed
  mkdir -p "$(dirname "$target")"

  # Create symlink
  ln -sf "$source" "$target"
  success "Linked $source → $target"
}

# Neovim config
backup_and_link "$SCRIPT_DIR/nvim" "$HOME/.config/nvim"

# tmux config
backup_and_link "$SCRIPT_DIR/tmux/tmux.conf" "$HOME/.tmux.conf"

# ── 8. zshrc injection ──────────────────────────────────────────────
ZSHRC="$HOME/.zshrc"
MARKER_START="# >>> development-wf >>>"
MARKER_END="# <<< development-wf <<<"

inject_zshrc_block() {
  local block_file="$SCRIPT_DIR/shell/zshrc_block.zsh"
  local block_content
  block_content="$(cat "$block_file")"

  local full_block
  full_block="${MARKER_START}
${block_content}
${MARKER_END}"

  # Create .zshrc if it doesn't exist
  touch "$ZSHRC"

  if grep -qF "$MARKER_START" "$ZSHRC"; then
    # Replace existing block (between markers, inclusive)
    local tmpfile
    tmpfile="$(mktemp)"
    awk -v start="$MARKER_START" -v end="$MARKER_END" -v block="$full_block" '
      $0 == start { skip=1; print block; next }
      $0 == end   { skip=0; next }
      !skip       { print }
    ' "$ZSHRC" > "$tmpfile"
    mv "$tmpfile" "$ZSHRC"
    success "Updated existing dev-workflow block in ~/.zshrc"
  else
    # Append block
    printf '\n%s\n' "$full_block" >> "$ZSHRC"
    success "Appended dev-workflow block to ~/.zshrc"
  fi
}

inject_zshrc_block

# ── 9. Summary ───────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}════════════════════════════════════════════${NC}"
echo -e "${BOLD}  AI Dev Workflow — Installation Complete   ${NC}"
echo -e "${BOLD}════════════════════════════════════════════${NC}"
echo ""

if [[ ${#INSTALLED[@]} -gt 0 ]]; then
  echo -e "${GREEN}Installed:${NC}"
  for item in "${INSTALLED[@]}"; do
    echo "  + $item"
  done
  echo ""
fi

if [[ ${#BACKUPS[@]} -gt 0 ]]; then
  echo -e "${YELLOW}Backups created:${NC}"
  for item in "${BACKUPS[@]}"; do
    echo "  → $item"
  done
  echo ""
fi

echo -e "${BOLD}Symlinks:${NC}"
echo "  ~/.config/nvim  → $SCRIPT_DIR/nvim"
echo "  ~/.tmux.conf    → $SCRIPT_DIR/tmux/tmux.conf"
echo ""

echo -e "${BOLD}Next steps:${NC}"
echo "  1. source ~/.zshrc"
echo "  2. Install a Nerd Font for terminal icons:"
echo "     brew install --cask font-jetbrains-mono-nerd-font"
echo "     (Then set it as your terminal's font)"
echo "  3. Open nvim — plugins will auto-install on first launch"
echo "  4. Run 'dev' to start a tmux dev session"
echo "  5. Set your Anthropic API key: export ANTHROPIC_API_KEY=sk-..."
echo ""
echo -e "${GREEN}Happy coding!${NC}"
