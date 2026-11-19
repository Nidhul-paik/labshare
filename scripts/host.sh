#!/usr/bin/env sh
# Start LabShare (host). Extra arguments are passed through, e.g.  ./scripts/host.sh --help
DIR="$(cd "$(dirname "$0")/.." && pwd)"
exec python3 "$DIR/run_labshare.py" host "$@"
