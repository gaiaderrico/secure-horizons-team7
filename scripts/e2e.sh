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
MINE=/srv/share/00_passwords_backup.txt
fail() { echo "FAIL: $*"; exit 1; }

docker compose exec -T guard python guard.py restore >/dev/null || fail "restore"
docker compose exec -T guard python guard.py check || fail "share not clean before start"
REAL=$($SSH "md5sum $JEWEL" | cut -d' ' -f1)

echo "== test 1: ssh ls"
$SSH "ls share/clinical" || fail "ssh ls"

echo "== test 2: 3 commands -> 3 log lines"
before=$(docker compose exec -T guard sh -c 'wc -l < /var/log/mirage/commands.jsonl')
for c in id hostname "ls -la share"; do $SSH "$c" >/dev/null; done
after=$(docker compose exec -T guard sh -c 'wc -l < /var/log/mirage/commands.jsonl')
[ $((after - before)) -eq 3 ] || fail "expected 3 new log lines, got $((after - before))"
docker compose exec -T guard tail -n 3 /var/log/mirage/commands.jsonl

for i in $(seq 1 "$ROUNDS"); do
  echo "== round $i, test 3: open the mine -> swap"
  t0=$(date +%s.%N)
  # odd rounds open the mine by name (command detector), even rounds via grep -r (atime detector)
  if [ $((i % 2)) -eq 1 ]; then $SSH "cat $MINE" >/dev/null; else $SSH "grep -ril vpn share >/dev/null"; fi
  ok=""
  for _ in $(seq 1 20); do
    st=$(docker compose exec -T guard python guard.py status | grep '"state"')
    case "$st" in *swapped*|*contained*) ok=1; break ;; esac
    sleep 0.1
  done
  t1=$(date +%s.%N)
  [ -n "$ok" ] || fail "no swap after mine"
  NOW=$($SSH "md5sum $JEWEL" | cut -d' ' -f1)
  [ "$NOW" != "$REAL" ] || fail "jewel still real after swap"
  echo "swapped, seen by the attacker after $(awk "BEGIN{printf \"%.2f\", $t1 - $t0}") s; jewel now:"
  $SSH "head -2 $JEWEL"

  echo "== round $i, test 4: restore"
  docker compose exec -T guard python guard.py restore | grep -E '"restored"|leftovers' -A0
  docker compose exec -T guard python guard.py check || fail "leftovers after restore"
  [ "$($SSH "md5sum $JEWEL" | cut -d' ' -f1)" = "$REAL" ] || fail "jewel not restored"
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
[ "$($SSH "md5sum $JEWEL" | cut -d' ' -f1)" = "$REAL" ] || fail "jewel not restored by /restore"
docker compose exec -T guard python guard.py check || fail "leftovers after /restore"

echo "ALL PASSED ($ROUNDS rounds + control API)"
