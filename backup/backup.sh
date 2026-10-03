#!/bin/sh
# Write one consistent ZenCRM backup archive (the instance directory with databases, keys and attachments,
# plus uploads) and prune old ones.
set -eu
# Archives contain the application signing keys; keep them readable by the owner only.
umask 077

INSTANCE_DIR="${INSTANCE_DIR:-/data/instance}"
UPLOADS_DIR="${UPLOADS_DIR:-/data/uploads}"
BACKUP_DIR="${BACKUP_DIR:-/backups}"
BACKUP_RETENTION="${BACKUP_RETENTION:-14}"
DATABASE_FILE="${DATABASE_FILE:-zencrm.db}"

case "$BACKUP_RETENTION" in
    ''|*[!0-9]*|0) echo "BACKUP_RETENTION must be a positive number" >&2; exit 1 ;;
esac
case "$INSTANCE_DIR$BACKUP_DIR" in
    *"'"*) echo "INSTANCE_DIR and BACKUP_DIR must not contain single quotes" >&2; exit 1 ;;
esac
if [ ! -f "$INSTANCE_DIR/$DATABASE_FILE" ]; then
    echo "No database at $INSTANCE_DIR/$DATABASE_FILE" >&2
    exit 1
fi

mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"
# Work directories left behind by an interrupted run.
find "$BACKUP_DIR" -mindepth 1 -maxdepth 1 -name '.zencrm-*' -mmin +1440 -exec rm -rf {} +

stamp=$(date -u +%Y%m%d-%H%M%S)
work=$(mktemp -d "$BACKUP_DIR/.zencrm-$stamp.XXXXXX")
trap 'rm -rf "$work"' EXIT
trap 'exit 1' INT TERM
mkdir "$work/instance"

find "$INSTANCE_DIR" -mindepth 1 -maxdepth 1 | while IFS= read -r entry; do
    name=$(basename "$entry")
    case "$name" in
        # Databases are snapshotted below; journals, locks, pre-migration copies and earlier restores are not needed.
        *.db|*.sqlite|*.sqlite3|*-journal|*-wal|*-shm|*.migrate.lock|*.bak|replaced-*|.restore-*) ;;
        *) cp -R "$entry" "$work/instance/" ;;
    esac
done

find "$INSTANCE_DIR" -mindepth 1 -maxdepth 1 -type f \( -name '*.db' -o -name '*.sqlite' -o -name '*.sqlite3' \) |
while IFS= read -r database; do
    name=$(basename "$database")
    # VACUUM INTO writes a consistent snapshot while the application keeps running.
    sqlite3 -cmd '.timeout 30000' "$database" "VACUUM INTO '$work/instance/$name'"
    result=$(sqlite3 "$work/instance/$name" 'PRAGMA integrity_check')
    if [ "$result" != ok ]; then
        echo "Integrity check failed for $name: $result" >&2
        exit 1
    fi
done

mkdir "$work/uploads"
if [ -d "$UPLOADS_DIR" ]; then
    # Skip staging directories left by an interrupted restore.
    find "$UPLOADS_DIR" -mindepth 1 -maxdepth 1 ! -name '.restore-*' -exec cp -R {} "$work/uploads/" \;
fi
if [ -n "$(find "$work" -type l)" ]; then
    echo "Warning: the data contains symbolic links; restore.sh refuses archives that contain them" >&2
fi

archive="$BACKUP_DIR/zencrm-$stamp.tar.gz"
[ ! -e "$archive" ] || archive="$BACKUP_DIR/zencrm-$stamp-$$.tar.gz"
tar -czf "$work/archive.tar.gz" -C "$work" instance uploads
mv "$work/archive.tar.gz" "$archive"
echo "Backup written: $archive"

ls -1 "$BACKUP_DIR"/zencrm-*.tar.gz | sort -r | tail -n "+$((BACKUP_RETENTION + 1))" | while IFS= read -r old; do
    rm -f "$old"
    echo "Removed old backup: $old"
done
