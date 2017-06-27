set nocompatible
set nobackup
set noundofile
set nowb
set noswapfile

set nonumber
set nowrap
"set number
"set wrap


" this is very important
set mouse-=a

filetype plugin on
filetype indent on

set autoread

set ffs=unix,dos,mac
set encoding=utf8
set fileencoding=utf8
set fileencodings=utf-8,gbk
set termencoding=utf-8

set list
set listchars=tab:>`,trail:~

set so=7
set wildmenu
set wildignore=*.o,*~,*.pyc

set ruler

set cmdheight=1
set hid
set backspace=eol,start,indent
set whichwrap+=<,>,h,l
set ignorecase
set smartcase


set hlsearch
set incsearch
set lazyredraw
set colorcolumn=99

set autoindent
set showmatch
set magic
set ai
set si
set cindent



set expandtab
set smarttab
set shiftwidth=4
set tabstop=4

set lbr
set tw=500

set noerrorbells
set novisualbell


syntax enable

set laststatus=2

set statusline=\ %F%m%r%h\ %w\ \ CWD:\ %r%{getcwd()}%h\ \ \ Line:\ %l
set statusline=%<%f%m%r%h[%{&ff}]%r%{getcwd()}%h\ %=\ [%l%V,\ %c%V]\ %P

set cursorline
"highlight CursorLine    cterm=underline
"ctermfg=white ctermbg=red
"highlight CursorColumn
"highlight LineNr        cterm=underline

" customized shortcuts
let mapleader = ";"
let g:mapleader = ";"

nmap <leader>w :w!<cr>
" ????
"command W w !sudo tee % > /dev/null

" move between windows
map <C-h> <C-W>h
map <C-j> <C-W>j
map <C-k> <C-W>k
map <C-l> <C-W>l

nmap <leader>t :TagbarToggle<cr>
" vim tabs
"autocmd BufReadPost * tab ball
map <leader>j :tabp<cr>
map <leader>h :tabp<cr>
map <leader>k :tabn<cr>
map <leader>l :tabn<cr>
map <leader>n :Texplore<cr>
map <leader>. :cd %:p:h<cr>:pwd<cr>

""

""
map <silent> <leader><cr> :noh<cr>

map <leader>bd :Bclose<cr>
map <leader>ba :1,1000 bd!<cr>

"execute pathogen#infect()

