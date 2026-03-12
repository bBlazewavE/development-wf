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

# Dev session: Neovim on top, Pi on bottom
dev() {
  local session="${1:-dev}"
  tmux new-session -d -s "$session" -n code 'nvim +Telescope\ find_files'
  tmux split-window -v -t "$session" -l 30% 'pi'
  tmux select-pane -t "$session:1.1"
  tmux attach -t "$session"
}
