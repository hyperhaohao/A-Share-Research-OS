#!/usr/bin/env bash
# Restore: copy a backup over the database file and verify integrity.
# Usage: ./scripts/restore.sh <backup.db>
set -euo pipefail

BACKUP="${1:?usage: restore.sh <backup.db>}"
DB="${ASRO_DB_FILE:-./asro_dev.db}"

[[ -f "$BACKUP" ]] || { echo "backup not found: $BACKUP" >&2; exit 1; }

if ! command -v sqlite3 >/dev/null 2>&1; then
  # integrity fallback without sqlite3 CLI: file must be valid SQLite header
  head -c 16 "$BACKUP" | grep -q "SQLite format 3" || { echo "not a SQLite file" >&2; exit 1; }
fi

# WAL mode: stale -wal/-shm files would replay the post-backup state over
# the restored database (found during the R5.3 drill). Remove them after
# copying; the backup was checkpointed so it is self-contained.
rm -f "$DB-wal" "$DB-shm"
cp "$BACKUP" "$DB"

if command -v sqlite3 >/dev/null 2>&1; then
  sqlite3 "$DB" "PRAGMA integrity_check;" | grep -q ok || { echo "integrity check FAILED" >&2; exit 1; }
fi

echo "restored $BACKUP → $DB (integrity ok)"
