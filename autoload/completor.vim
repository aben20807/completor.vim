" vim: et ts=2 sts=2 sw=2

let s:save_cpo = &cpo
set cpo&vim

let s:completions = []
let s:daemon = {}
let s:status = {'pos': [], 'nr': -1, 'input': ''}

function s:daemon.respawn(cmd, name)
  if self.status(a:name) == 'run'
    call job_stop(self.job)
  endif

  let self.job = job_start(a:cmd, {
        \   "out_cb": {c,m->s:trigger(m)},
        \   "err_io": 'out',
        \   "mode": 'nl'
        \ })
  let self.ft = a:name
endfunction

function s:daemon.write(data)
  let ch = job_getchannel(self.job)
  call ch_sendraw(ch, a:data."\n")
endfunction

function s:daemon.status(name)
  if !exists('self.job')
    return 'none'
  endif

  let s = job_status(self.job)
  if exists('self.ft') && self.ft != a:name
    if s == 'run'
      call job_stop(self.job)
    endif
    return 'none'
  endif

  return s
endfunction


function! completor#omnifunc(findstart, base)
  if a:findstart
    let word = matchstr(getline('.'), '\w*\%'.col('.').'c')
    return col('.') - 1 - len(word)
  endif
  return s:completions
endfunction


function! s:trigger(msg)
  if s:status.nr != bufnr('') || s:status.pos != getcurpos()
    let s:completions = []
  else
    let s:completions = completor#utils#get_completions(a:msg, s:status.input)
  endif
  if empty(s:completions) | return | endif

  setlocal omnifunc=completor#omnifunc
  setlocal completeopt-=longest
  setlocal completeopt+=menuone
  setlocal completeopt-=menu
  if &completeopt !~# 'noinsert\|noselect'
    setlocal completeopt+=noselect
  endif
  call feedkeys("\<C-x>\<C-o>", 'n')
endfunction


function! s:handle(ch)
  let msg = []
  while ch_status(a:ch) == 'buffered'
    call add(msg, ch_read(a:ch))
  endwhile
  call s:trigger(msg)
endfunction


function! s:reset()
  let s:completions = []
  if exists('s:job') && job_status(s:job) == 'run'
    call job_stop(s:job)
  endif
endfunction


function! s:process_daemon(cmd, name)
  if s:daemon.status(a:name) != 'run'
    call s:daemon.respawn(a:cmd, a:name)
  endif
  let filename = expand('%:p')
  let content = join(getline(1, '$'), "\n")
  let req = {
        \   "line": line('.') - 1,
        \   "col": col('.') - 1,
        \   "filename": filename,
        \   "content": content
        \ }
  call s:daemon.write(json_encode(req))
endfunction


function! s:complete()
  call s:reset()

  let end = col('.') - 2
  let inputted = end >= 0 ? getline('.')[:end] : ''

  let info = completor#utils#get_completer(&filetype, inputted)
  if empty(info) | return | endif
  let [cmd, name, daemon, is_sync] = info

  let s:status = {'input': inputted, 'pos': getcurpos(), 'nr': bufnr('')}

  if is_sync
    call s:trigger(inputted)
  elseif !empty(cmd)
    if daemon
      call s:process_daemon(cmd, name)
    else
      let s:job = job_start(cmd, {
            \   "close_cb": {c->s:handle(c)},
            \   "in_io": 'null',
            \   "err_io": 'out'
            \ })
    endif
  endif
endfunction


function! s:on_text_change()
  if exists('s:timer')
    let info = timer_info(s:timer)
    if !empty(info)
      call timer_stop(s:timer)
    endif
  endif

  let s:timer = timer_start(16, {t->s:complete()})
endfunction


function! s:set_events()
  augroup completor
    autocmd!
    autocmd TextChangedI * call s:on_text_change()
  augroup END
endfunction


function! completor#disable()
  augroup completor
    autocmd!
  augroup END
endfunction


function! completor#enable()
  if &diff
    return
  endif

  if get(g:, 'completor_auto_close_doc', 1)
    autocmd! CompleteDone * if pumvisible() == 0 | pclose | endif
  endif

  call s:set_events()
endfunction

let &cpo = s:save_cpo
unlet s:save_cpo
