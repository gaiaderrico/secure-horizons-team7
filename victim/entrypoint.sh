#!/bin/sh
# MIRAGE victim entrypoint: passwords, test keys, log file, then sshd in the foreground.
set -eu

: "${VICTIM_PASSWORD:?VICTIM_PASSWORD is not set (copy .env.example to .env)}"
for u in svc_backup jdupont; do
  echo "$u:$VICTIM_PASSWORD" | chpasswd
  # Optional test key for automated tests (./keys/test_key.pub on the host).
  if [ -f /keys/test_key.pub ]; then
    install -d -m 700 -o "$u" -g lumen "/home/$u/.ssh"
    install -m 600 -o "$u" -g lumen /keys/test_key.pub "/home/$u/.ssh/authorized_keys"
  fi
done

# Command log: users may append (mirage-shell runs as them) but not read it.
mkdir -p /var/log/mirage
chmod 711 /var/log/mirage
touch /var/log/mirage/commands.jsonl
chown root:root /var/log/mirage/commands.jsonl
chmod 622 /var/log/mirage/commands.jsonl

# The guard container owns /srv; just make sure the share path exists.
mkdir -p /srv/share
chmod 755 /srv

exec env -u VICTIM_PASSWORD /usr/sbin/sshd -D -e
