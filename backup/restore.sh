#!/bin/sh
# Restore a ZenCRM backup archive. Stop the application first. The restored files are staged next to the
# targets and swapped in by renames; the replaced files are kept in instance/replaced-<timestamp>.
set -eu
umask 077

INSTANCE_DIR="${INSTANCE_DIR:-/data/instance}"
UPLOADS_DIR="${UPLOADS_DIR:-/data/uploads}"
DATABASE_FILE="${DATABASE_FILE:-zencrm.db}"
APP_UID="${APP_UID:-1000}"

archive="${1:-}"
if [ -z "$archive" ] || [ ! -f "$archive" ]; then
    echo "Usage: restore.sh /backups/zencrm-YYYYmmdd-HHMMSS.tar.gz" >&2
    exit 1
fi

stamp=$(date -u +%Y%m%d-%H%M%S)
work=$(mktemp -d)
stage_instance="$INSTANCE_DIR/.restore-$stamp"
stage_uploads="$UPLOADS_DIR/.restore-$stamp"
aside="$INSTANCE_DIR/replaced-$stamp"
trap 'rm -rf "$work" "$stage_instance" "$stage_uploads"' EXIT
trap 'exit 1' INT TERM

tar -xzf "$archive" -C "$work"
if [ ! -f "$work/instance/$DATABASE_FILE" ]; then
    echo "The archive contains no instance/$DATABASE_FILE" >&2
    exit 1
fi
if [ -n "$(find "$work" -type l)" ]; then
    echo "The archive contains symbolic links; refusing to restore it" >&2
    exit 1
fi
find "$work/instance" -mindepth 1 -maxdepth 1 -type f \( -name '*.db' -o -name '*.sqlite' -o -name '*.sqlite3' \) |
while IFS= read -r database; do
    result=$(sqlite3 "$database" 'PRAGMA integrity_check')
    if [ "$result" != ok ]; then
        echo "Integrity check failed for $(basename "$database"): $result" >&2
        exit 1
    fi
done

# Stage on the target file systems first, so a failure here leaves the current data untouched.
mkdir -p "$UPLOADS_DIR"
# Staging directories left by an interrupted restore.
find "$INSTANCE_DIR" "$UPLOADS_DIR" -mindepth 1 -maxdepth 1 -name '.restore-*' -exec rm -rf {} +
mkdir "$stage_instance" "$stage_uploads"
cp -R "$work/instance/." "$stage_instance/"
[ ! -d "$work/uploads" ] || cp -R "$work/uploads/." "$stage_uploads/"
# An archive without application keys keeps the current ones; new keys would end every session.
[ -f "$stage_instance/security.sqlite" ] && keep_keys= || keep_keys=1
mkdir -p "$aside/instance" "$aside/uploads"

# Move entries of $1 into $2, stopping at the first failure. Skips restore leftovers, pre-migration
# copies and, when the archive has no keys, the current security.sqlite.
move_entries() {
    find "$1" -mindepth 1 -maxdepth 1 ! -name 'replaced-*' ! -name '.restore-*' ! -name '*.bak' |
    while IFS= read -r entry; do
        if [ -n "$keep_keys" ] && [ "$entry" = "$INSTANCE_DIR/security.sqlite" ]; then continue; fi
        mv "$entry" "$2/" || exit 1
    done
}

# Undo a partial swap: drop what came from staging, then move the previous files back.
rollback() {
    echo "Restore failed; putting the previous files back" >&2
    for pair in "$INSTANCE_DIR:instance" "$UPLOADS_DIR:uploads"; do
        target=${pair%:*}
        stage="$target/.restore-$stamp"
        find "$target" -mindepth 1 -maxdepth 1 ! -name 'replaced-*' ! -name '.restore-*' |
        while IFS= read -r entry; do
            name=$(basename "$entry")
            # Archive entries that are no longer staged were moved in by this restore.
            if [ -e "$work/${pair#*:}/$name" ] && [ ! -e "$stage/$name" ]; then
                rm -rf "$entry"
            fi
        done
        find "$aside/${pair#*:}" -mindepth 1 -maxdepth 1 -exec mv {} "$target/" \;
    done
    rm -rf "$aside"
    exit 1
}

move_entries "$INSTANCE_DIR" "$aside/instance" || rollback
move_entries "$UPLOADS_DIR" "$aside/uploads" || rollback
keep_keys=
move_entries "$stage_instance" "$INSTANCE_DIR" || rollback
move_entries "$stage_uploads" "$UPLOADS_DIR" || rollback
if [ "$(id -u)" = 0 ]; then
    chown -R "$APP_UID:$APP_UID" "$INSTANCE_DIR" "$UPLOADS_DIR"
fi

echo "Restored $archive"
echo "Previous files were moved to $aside; delete them once the restored data is verified."
