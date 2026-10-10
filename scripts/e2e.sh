#!/bin/bash
# MIRAGE end-to-end check of victim + guard (acceptance tests 1-4). Needs the stack up and keys/test_key.
#   bash scripts/e2e.sh [rounds]        (from the repo root; Git Bash on Windows is fine)
set -u
export MSYS_NO_PATHCONV=1   # Git Bash: don't rewrite /srv/... paths
ROUNDS=${1:-3}
SSH="ssh -i keys/test_key -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -p 2222 svc_backup@localhost"
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
echo "ALL PASSED ($ROUNDS rounds)"
