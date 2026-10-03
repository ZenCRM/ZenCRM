#!/bin/sh
# Run scheduled backups by default; "backup" and "restore <archive>" run once.
set -eu

case "${1:-schedule}" in
    schedule)
        schedule="${BACKUP_SCHEDULE:-0 2 * * *}"
        echo "$schedule /usr/local/bin/backup.sh > /proc/1/fd/1 2> /proc/1/fd/2" > /etc/crontabs/root
        echo "Scheduled backups: $schedule (TZ=${TZ:-UTC})"
        exec crond -f -l 8
        ;;
    backup)
        exec /usr/local/bin/backup.sh
        ;;
    restore)
        shift
        exec /usr/local/bin/restore.sh "$@"
        ;;
    *)
        exec "$@"
        ;;
esac
