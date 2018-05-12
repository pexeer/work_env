alias  screen="screen -U"
alias  tmux="tmux -u"
alias sh=bash
export PS1="[\h:\[\e[32m\]\w\[\e[m\]]$"
alias free="free -m"
alias fm="free =m"
alias ls='ls --color=auto'
alias ll="ls -al"
alias gh="cd ~"

export LESSCHARSET=utf-8

export MARKPATH=$HOME/.marks
export LASTMARK=..last..

function g {
local m=$1
if [ "$m" = "" ]; then m=$LASTMARK; fi
cd -P "$MARKPATH/$m" 2>/dev/null || echo "No such mark: $m"
        }

        function m {
        local m=$1
        if [ "$m" != "" ]; then
            rm -f "$MARKPATH/$m"
            ln -s "$(pwd)" "$MARKPATH/$m"
        fi
        m=$LASTMARK;
        rm -f "$MARKPATH/$m"
        ln -s "$(pwd)" "$MARKPATH/$m"
    }

    function um {
    local m=$1
    if [ "$m" = "" ]; then m=$LASTMARK; fi
    rm -f "$MARKPATH/$m"
}

function lm {
    for item in `ls $MARKPATH`; do
        printf "\033[31m%-7s\033[0m\t=>" "$item"
        readlink -f "$item"
    done
}

# for auto-completion
_completemarks() {
    local curw=${COMP_WORDS[COMP_CWORD]}
    local wordlist=$(ls -l "$MARKPATH" | grep ^l | cut -d ' ' -f 10)
    COMPREPLY=($(compgen -W '${wordlist[@]}' -- "$curw"))
    return 0
}
complete -F _completemarks g
# make mark dir
mkdir -p $MARKPATH

