#!/bin/sh
# DF_Unified/BUILD -- df_unified build (offline; NETWORK=deny)
set -eu
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
PY="${PYTHON:-python3}"
exec "$PY" -B "$ROOT/df_unified/cli.py" build "$@"
