# === AI Dev Workflow ===

# Default editor
export EDITOR='nvim'
export VISUAL='nvim'

# PATH additions
export PATH="$HOME/.local/bin:$PATH"

# fzf shell integration (Ctrl-R history, Ctrl-T files, Alt-C dirs)
source <(fzf --zsh)

# Starship prompt
eval "$(starship init zsh)"

# Aliases
alias lg='lazygit'
alias y='yazi'
alias v='nvim'
alias cc='claude'

# Dev session: opens tmux with Neovim + Claude Code + lazygit + shell
dev() {
  local session="${1:-dev}"
  tmux new-session -d -s "$session" -n code 'nvim'
  tmux split-window -h -t "$session" 'claude'
  tmux split-window -v -t "$session"
  tmux select-pane -t "$session:1.1"
  tmux split-window -v -t "$session" 'lazygit'
  tmux select-pane -t "$session:1.2"
  tmux attach -t "$session"
}
