# MIRAGE victim: the company file server "lumen-fs01" (SSH + file share).
# The share itself (/srv) is a named volume filled by the guard container.
FROM debian:12-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends openssh-server python3 curl procps less vim-tiny file \
 && rm -rf /var/lib/apt/lists/* \
 && mkdir -p /run/sshd

# Fixed uids: the guard (another container) kills sessions by uid on Contain.
RUN groupadd -g 1500 lumen \
 && useradd -m -u 1001 -g lumen -s /bin/bash -c "Backup service" svc_backup \
 && useradd -m -u 1002 -g lumen -s /bin/bash -c "Julien Dupont" jdupont \
 && ln -s /srv/share /home/svc_backup/share \
 && ln -s /srv/share /home/jdupont/company

COPY sshd_config /etc/ssh/sshd_config.d/00-mirage.conf
COPY mirage-shell /usr/local/bin/mirage-shell
COPY cmdlog.py /usr/local/lib/mirage/cmdlog.py
COPY profile-mirage.sh /etc/profile.d/mirage.sh
COPY motd /etc/motd
COPY entrypoint.sh /entrypoint.sh
RUN chmod 755 /usr/local/bin/mirage-shell /entrypoint.sh \
 && chmod 644 /usr/local/lib/mirage/cmdlog.py /etc/profile.d/mirage.sh

EXPOSE 22
ENTRYPOINT ["/entrypoint.sh"]
