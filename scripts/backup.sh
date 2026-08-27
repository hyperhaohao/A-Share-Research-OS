#!/usr/bin/env bash
# Backup: SQLite snapshot (safe via WAL checkpoint) + configuration.
# Usage: ./scripts/backup.sh [output_dir]
set -euo pipefail

OUT_DIR="${1:-./backups}"
STAMP="$(date +%Y%m%d-%H%M%S)"
DB="${ASRO_DB_FILE:-./asro_dev.db}"

mkdir -p "$OUT_DIR"

if [[ -f "$DB" ]]; then
  # checkpoint WAL so the copied file is complete
  sqlite3 "$DB" "PRAGMA wal_checkpoint(TRUNCATE);" 2>/dev/null || true
  cp "$DB" "$OUT_DIR/asro-$STAMP.db"
  echo "database → $OUT_DIR/asro-$STAMP.db"
else
  echo "database file not found at $DB (nothing to back up)" >&2
  exit 1
fi

if [[ -f ".env" ]]; then
  cp .env "$OUT_DIR/env-$STAMP.txt"
  echo "config   → $OUT_DIR/env-$STAMP.txt"
fi

echo "backup complete: $OUT_DIR/asro-$STAMP.db"
