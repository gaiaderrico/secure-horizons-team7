#!/bin/bash
# MIRAGE end-to-end check of victim + guard (acceptance tests 1-4). Needs the stack up and keys/test_key.
#   bash scripts/e2e.sh [rounds]        (from the repo root; Git Bash or WSL bash on Windows)
set -u
export MSYS_NO_PATHCONV=1   # Git Bash: don't rewrite /srv/... paths
ROUNDS=${1:-3}
# Windows drive files show as 0777 in WSL and ssh refuses such a key: use a private 600 copy.
KEY=$(mktemp "$HOME/.mirage_test_key.XXXXXX") || { echo "FAIL: mktemp"; exit 1; }
trap 'rm -f "$KEY"' EXIT
cp keys/test_key "$KEY" && chmod 600 "$KEY" || { echo "FAIL: copy keys/test_key"; exit 1; }
# BatchMode: fail instead of falling back to a password prompt
SSH="ssh -i $KEY -o BatchMode=yes -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -p 2222 svc_backup@localhost"
JEWEL=/srv/share/clinical/patients.csv
# Checksums are read from the guard container, not over SSH: svc_backup naming a crown jewel
# now makes the guard swap first, which would turn the baseline itself into the fake.
jewel_md5() { docker compose exec -T guard md5sum "$JEWEL" | cut -d' ' -f1; }
MINE=/srv/share/00_passwords_backup.txt
fail() { echo "FAIL: $*"; exit 1; }
SWAP_WAIT=${E2E_SWAP_WAIT:-10}   # seconds; generous for loaded machines (local LLM eating CPU)
guard_state() { docker compose exec -T guard python guard.py status | sed -n 's/.*"state": "\([a-z]*\)".*/\1/p' | head -1; }
# wait_swapped: until the guard reports swapped/contained, or SWAP_WAIT seconds
wait_swapped() {
  local end=$(( $(date +%s) + SWAP_WAIT ))
  while [ "$(date +%s)" -le "$end" ]; do
    case "$(guard_state)" in swapped|contained) return 0 ;; esac
    sleep 0.2
  done
  return 1
}
open_mine_unnamed() { $SSH "grep -ril vpn share >/dev/null"; }  # never names the mine

docker compose exec -T guard python guard.py restore >/dev/null || fail "restore"
docker compose exec -T guard python guard.py check || fail "share not clean before start"
docker compose exec -T guard python guard.py status | grep -A6 '"detectors"' | tr -d '
 ' ; echo
REAL=$(jewel_md5)

echo "== test 1: ssh ls"
$SSH "ls share/clinical" || fail "ssh ls"

echo "== test 2: 3 commands -> 3 log lines"
before=$(docker compose exec -T guard sh -c 'wc -l < /var/log/mirage/commands.jsonl')
for c in id hostname "ls -la share"; do $SSH "$c" >/dev/null; done
after=$(docker compose exec -T guard sh -c 'wc -l < /var/log/mirage/commands.jsonl')
[ $((after - before)) -eq 3 ] || fail "expected 3 new log lines, got $((after - before))"
docker compose exec -T guard tail -n 3 /var/log/mirage/commands.jsonl
# the guard must have identified each one: user, session and source IP all set
docker compose exec -T guard python -c '
import json
for r in [json.loads(x) for x in open("/var/log/mirage/commands.jsonl").readlines()[-3:]]:
    assert r["user"] == "svc_backup" and r["session"].startswith("s-") and r["src_ip"], r
' || fail "command records missing user/session/src_ip"

for i in $(seq 1 "$ROUNDS"); do
  echo "== round $i, test 3: open the mine -> swap"
  t0=$(python3 -c 'import time; print(time.time())')
  # odd rounds open the mine by name (command detector), even rounds via grep -r (inotify/atime)
  if [ $((i % 2)) -eq 1 ]; then $SSH "cat $MINE" >/dev/null; else open_mine_unnamed; fi
  wait_swapped || fail "no swap after mine (round $i, waited ${SWAP_WAIT}s)"
  t1=$(python3 -c 'import time; print(time.time())')
  NOW=$(jewel_md5)
  [ "$NOW" != "$REAL" ] || fail "jewel still real after swap"
  echo "swapped, seen by the attacker after $(python3 -c "print(f'{$t1 - $t0:.2f}')") s; jewel now:"
  $SSH "head -2 $JEWEL"

  echo "== round $i, test 4: restore"
  docker compose exec -T guard python guard.py restore | grep -E '"restored"|leftovers' -A0
  docker compose exec -T guard python guard.py check || fail "leftovers after restore"
  [ "$(jewel_md5)" = "$REAL" ] || fail "jewel not restored"
done

echo "== test 5: control API /contain + /restore (as core calls it, from the Docker network)"
TOKEN=$(docker compose exec -T guard printenv GUARD_TOKEN | tr -d '\r')
[ -n "$TOKEN" ] || fail "guard has no GUARD_TOKEN"
if [ -f mirage/core/Dockerfile ]; then
  # one-off core container with the env compose gives core (works even if core is not running)
  CORE_TOKEN=$(docker compose --profile core run --rm --no-deps -T --entrypoint printenv core GUARD_TOKEN 2>/dev/null | tr -d '\r')
  [ "$CORE_TOKEN" = "$TOKEN" ] || fail "core and guard get different GUARD_TOKEN from compose"
  echo "core and guard get the same GUARD_TOKEN from compose"
else
  echo "(mirage/core not in this checkout: skipped the core token comparison)"
fi
# api <path> [token] -> prints "<body> <http code>"
api() {
  docker compose exec -T victim curl -s -X POST -H "Content-Type: application/json" \
    ${2:+-H "X-Guard-Token: $2"} -d '{"user": "svc_backup", "by": "e2e"}' \
    -w ' %{http_code}' "http://victim:8081$1"
}
code() { echo "${1##* }"; }
for path in /contain /restore; do
  for tok in "" "wrong-token"; do
    out=$(api "$path" "$tok")
    [ "$(code "$out")" = 401 ] || fail "$path with token '${tok:-<none>}' gave $out, expected 401"
    echo "$path token=${tok:-<none>} -> 401"
  done
done
docker compose exec -T guard python guard.py check >/dev/null || fail "rejected calls changed the share"

out=$(api /contain "$TOKEN")
[ "$(code "$out")" = 200 ] || fail "/contain with token gave $out"
echo "/contain with token -> $out"
case "$out" in *'"state": "contained"'*) ;; *) fail "/contain did not contain" ;; esac
$SSH id >/dev/null 2>&1 && fail "svc_backup can still log in after /contain"
echo "svc_backup login refused while contained"
[ "$(docker compose exec -T guard python guard.py status | grep -c '"state": "contained"')" = 1 ] \
  || fail "guard status is not contained"

out=$(api /restore "$TOKEN")
[ "$(code "$out")" = 200 ] || fail "/restore with token gave $out"
echo "/restore with token -> $out"
case "$out" in *'"leftovers": []'*) ;; *) fail "/restore left leftovers" ;; esac
$SSH id >/dev/null || fail "svc_backup cannot log in after /restore"
[ "$(jewel_md5)" = "$REAL" ] || fail "jewel not restored by /restore"
docker compose exec -T guard python guard.py check || fail "leftovers after /restore"

echo "== test 6: the attacker can't forge, overwrite or truncate the command log"
LOG=/var/log/mirage/commands.jsonl
lines() { docker compose exec -T guard sh -c "wc -l < $LOG" | tr -d '\r '; }
n0=$(lines)
for attempt in "echo '{\"user\": \"jdupont\", \"cmd\": \"FORGED\"}' >> $LOG" ": > $LOG" "truncate -s 0 $LOG" "cat $LOG"; do
  err=$($SSH "$attempt" 2>&1 >/dev/null) && fail "svc_backup could run: $attempt"
  case "$err" in *"Permission denied"*) echo "svc_backup: $attempt -> Permission denied" ;;
                 *) fail "expected Permission denied for '$attempt', got: $err" ;; esac
done
n1=$(lines)
[ "$n1" -eq $((n0 + 4)) ] || fail "log went from $n0 to $n1 lines, expected +4 (the guard's own records)"
# the attempt's own record has the text JSON-escaped (\"cmd\"), so this only matches a forged line
docker compose exec -T guard grep -qF '"cmd": "FORGED"' $LOG && fail "forged record in log"
echo "log only grew by the guard's 4 records of those attempts"

# Talk to the socket directly, claiming to be jdupont in another session, and fake the env too.
TAG="SPOOF-$$-$RANDOM"
$SSH "python3 -" <<PY || fail "spoof script"
import json, socket
s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.connect("/run/mirage/cmd.sock")
s.sendall(json.dumps({"cmd": "$TAG-raw", "user": "jdupont", "session": "s-evil", "src_ip": "6.6.6.6",
                      "uid": 1002, "ts": 0}).encode() + b"\n")
print("guard said", s.recv(16))
PY
$SSH "env USER=jdupont SSH_CONNECTION='6.6.6.6 1 2 22' MIRAGE_SID=s-evil python3 /usr/local/lib/mirage/cmdlog.py $TAG-env exec" \
  || fail "env spoof"
docker compose exec -T guard python - "$TAG" <<'PY' || fail "spoofed identity accepted"
import json, sys
tag = sys.argv[1]
recs = [json.loads(x) for x in open("/var/log/mirage/commands.jsonl")]
# each spoofed record vs the guard's record of the ssh command that sent it (same connection)
for kind, sent_by in (("raw", lambda c: c == "python3 -"), ("env", lambda c: c.startswith("env USER=jdupont"))):
    i = next(i for i, r in enumerate(recs) if r["cmd"] == f"{tag}-{kind}")
    r = recs[i]
    o = next(x for x in reversed(recs[:i]) if sent_by(x["cmd"]))
    assert (r["user"], r["uid"]) == ("svc_backup", 1001), r
    assert r["session"] == o["session"] and r["session"] not in ("", "s-evil"), (r, o)
    assert r["src_ip"] == o["src_ip"] and r["src_ip"] not in ("", "6.6.6.6"), (r, o)
    assert r["ts"] > 1e9, r
    print(f"{kind} spoof logged as user={r['user']} session={r['session']} src={r['src_ip']} (claims ignored)")
PY

echo "== test 7: mine -> contain -> restore -> mine again must swap again (CLI, then core API)"
# CLI path: restore with docker compose exec (a separate process) must still re-arm the daemon
$SSH "cat $MINE" >/dev/null; wait_swapped || fail "7a: no swap on first mine"
docker compose exec -T guard python guard.py contain svc_backup | grep -q '"state": "contained"' || fail "7a: contain"
out=$(docker compose exec -T guard python guard.py restore)
echo "$out" | grep -q '"via": "daemon"' || fail "7a: CLI restore did not go through the daemon"
echo "$out" | grep -q '"mine_watches_armed": 0' && fail "7a: no mine watches armed after restore"
[ "$(guard_state)" = clean ] || fail "7a: not clean after CLI restore"
open_mine_unnamed; wait_swapped || fail "7a: no swap on second mine after CLI restore"
echo "CLI restore: mine opened again (grep -r, unnamed) -> swapped again"
docker compose exec -T guard python guard.py restore >/dev/null

CORE=${E2E_CORE_URL:-http://localhost:8000}
if curl -fs "$CORE/health" >/dev/null 2>&1; then
  incident() { curl -fs "$CORE/incidents" | python3 -c 'import json,sys; i=json.load(sys.stdin); print(max(i, key=lambda x: x["start_ts"])["id"] if i else "")'; }
  core_post() { curl -fs -X POST -H "Content-Type: application/json" -d '{"user": "e2e-analyst"}' "$CORE/incidents/$1/$2"; }
  $SSH "cat $MINE" >/dev/null; wait_swapped || fail "7b: no swap on first mine"
  sleep 1  # let the guard's events reach core
  INC=$(incident); [ -n "$INC" ] || fail "7b: core has no incident"
  core_post "$INC" contain >/dev/null || fail "7b: core contain on $INC"
  [ "$(guard_state)" = contained ] || fail "7b: guard not contained after core contain"
  $SSH id >/dev/null 2>&1 && fail "7b: svc_backup can still log in after core contain"
  core_post "$INC" restore >/dev/null || fail "7b: core restore on $INC"
  [ "$(guard_state)" = clean ] || fail "7b: guard not clean after core restore"
  $SSH id >/dev/null || fail "7b: svc_backup blocked after core restore"
  open_mine_unnamed; wait_swapped || fail "7b: no swap on second mine after core restore"
  echo "core API ($INC): contain + restore, then mine opened again (unnamed) -> swapped again"
  core_post "$INC" restore >/dev/null || fail "7b: final core restore"
  [ "$(guard_state)" = clean ] || fail "7b: not clean at the end"
else
  echo "(core API not reachable at $CORE: skipped the core variant; start it with --profile core)"
fi
docker compose exec -T guard python guard.py check || fail "leftovers after test 7"

echo "ALL PASSED ($ROUNDS rounds + control API + log integrity + re-arm)"
