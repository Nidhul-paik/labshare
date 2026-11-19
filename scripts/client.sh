#!/usr/bin/env sh
# Start LabShare (client). Extra arguments are passed through, e.g.  ./scripts/client.sh --help
DIR="$(cd "$(dirname "$0")/.." && pwd)"
exec python3 "$DIR/run_labshare.py" client "$@"
