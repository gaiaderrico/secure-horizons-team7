# MIRAGE: log every interactive command (sessions started by mirage-shell only).
if [ -n "$MIRAGE_SID" ] && [ -n "$BASH_VERSION" ]; then
  __mirage_log() {
    local n c
    read -r n c <<< "$(HISTTIMEFORMAT= history 1)"
    if [ -n "$__mirage_n" ] && [ "$n" != "$__mirage_n" ] && [ -n "$c" ]; then
      /usr/bin/python3 -I /usr/local/lib/mirage/cmdlog.py "$c" interactive >/dev/null 2>&1
    fi
    __mirage_n=$n
  }
  PROMPT_COMMAND="__mirage_log${PROMPT_COMMAND:+;$PROMPT_COMMAND}"
fi
