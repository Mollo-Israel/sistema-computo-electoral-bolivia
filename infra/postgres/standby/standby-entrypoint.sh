#!/bin/bash
set -e

if [ -z "$PGPASSWORD" ]; then
  echo "ERROR: POSTGRES_PASSWORD is required"
  exit 1
fi

if [ ! -s "$PGDATA/PG_VERSION" ] || [ ! -e "$PGDATA/standby.signal" ]; then
  echo "Waiting for primary database to become available..."
  until pg_isready -h postgres-oficial-primary -p 5432 -U replica >/dev/null 2>&1; do
    sleep 1
  done

  echo "Initializing standby from primary..."
  rm -rf "$PGDATA"/*
  PGPASSWORD="$PGPASSWORD" pg_basebackup -h postgres-oficial-primary -D "$PGDATA" -U replica -Fp -Xs -P -R
fi

chown -R postgres:postgres "$PGDATA"
chmod 700 "$PGDATA"

exec gosu postgres /usr/lib/postgresql/16/bin/postgres -D "$PGDATA" \
  -c listen_addresses='*' \
  -c hot_standby=on \
  -c max_wal_senders=3 \
  -c wal_keep_size=64
