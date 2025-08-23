filetype plugin indent on
syntax on
set number
set encoding=utf-8

" Highlight matching brackets on cursor
set showmatch

" Save swap files here instead of alongside the file
set directory=~/.vim-backup

" From https://dougblack.io/words/a-good-vimrc.html
" Show a menu when autocompleting file names.
set wildmenu

" Make backspace work as expected.
"
" https://vi.stackexchange.com/questions/2162/
set backspace=indent,eol,start

" Key bindings and settings for working with buffers
" Courtesy of https://joshldavis.com/2014/04/05/vim-tab-madness-buffers-vs-tabs/
set hidden
" Open a new buffer
nmap <leader>T :enew<CR>
" Move to the nex buffer
nmap <leader>l :bnext<CR>
" Move to the previous buffer
nmap <leader>h :bprevious<CR>
" Close the current buffer
nmap <leader>bq :bp <BAR> bd #<CR>

" Disable netrw pages for directories.
" Courtesy of https://stackoverflow.com/questions/21686729/
let loaded_netrwPlugin = 1

" jj to escape editing mode
inoremap jj <ESC>
" Ctrl+J to insert line break in normal mode
nnoremap <NL> i<CR><ESC>

" Courtesy of vi.stackexchange.com/questions/454/
fun! TrimWhitespace()
  let l:save = winsaveview()
  %s/\s\+$//e
  call winrestview(l:save)
endfun
command! TrimWhitespace call TrimWhitespace()

augroup foundation_language_settings
  autocmd!
  autocmd FileType c,cpp,css,fortran,html,javascript,json,rust,sh,typescript,vue,zsh setlocal expandtab shiftwidth=2 tabstop=2
  autocmd FileType python setlocal expandtab shiftwidth=4 tabstop=4
  " Highlight when line in git commit > 72 chars
  au FileType gitcommit set tw=72
augroup END
