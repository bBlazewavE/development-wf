local opt = vim.opt

-- Line numbers
opt.number = true
opt.relativenumber = true

-- Indentation
opt.tabstop = 2
opt.shiftwidth = 2
opt.softtabstop = 2
opt.expandtab = true
opt.smartindent = true
opt.autoindent = true

-- Search
opt.ignorecase = true
opt.smartcase = true
opt.hlsearch = false
opt.incsearch = true

-- Appearance
opt.termguicolors = true
opt.cursorline = true
opt.signcolumn = "yes"
opt.scrolloff = 8
opt.sidescrolloff = 8
opt.colorcolumn = "80"
opt.cmdheight = 1
opt.showmode = false

-- Splits
opt.splitright = true
opt.splitbelow = true

-- Clipboard
opt.clipboard = "unnamedplus"

-- Undo
opt.undofile = true
opt.undolevels = 10000

-- Misc
opt.wrap = false
opt.updatetime = 250
opt.timeoutlen = 300
opt.mouse = "a"
opt.completeopt = "menu,menuone,noselect"
opt.pumheight = 10
opt.conceallevel = 0
opt.fileencoding = "utf-8"
opt.confirm = true
opt.backup = false
opt.writebackup = false
opt.swapfile = false

-- Performance
opt.lazyredraw = false
opt.synmaxcol = 240
