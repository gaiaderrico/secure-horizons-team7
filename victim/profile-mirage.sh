# MIRAGE: log every interactive command (sessions started by mirage-shell only).
if [ -n "$MIRAGE_SESSION" ] && [ -n "$BASH_VERSION" ]; then
  __mirage_log() {
    local n c
    read -r n c <<< "$(HISTTIMEFORMAT= history 1)"
    # first prompt: only remember where history starts (don't re-log the previous session)
    if [ -n "$__mirage_init" ] && [ "$n" != "$__mirage_n" ] && [ -n "$c" ]; then
      /usr/bin/python3 -I /usr/local/lib/mirage/cmdlog.py "$c" interactive >/dev/null 2>&1
    fi
    __mirage_n=$n
    __mirage_init=1
  }
  PROMPT_COMMAND="__mirage_log${PROMPT_COMMAND:+;$PROMPT_COMMAND}"
fi
