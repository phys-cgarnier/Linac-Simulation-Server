#!/usr/bin/env bash
cd "$(dirname "${BASH_SOURCE[0]}")"
#  Activate conda environment and set EPICS env variables


source setup-epics-conda.sh
LATTICE_FLAG="${1:-0}"
if [ "$LATTICE_FLAG" -eq 1 ]; then
    echo Overriding LCLS_LATTICE to use local copy
    export LCLS_LATTICE=$(pwd)/simulation_server/lattices
# Check for provided arguments or provide defaults
fi
NAME="${2:-diag0}"
OVERVIEW="${3:-False}"
NOISE="${4:-0.0}"

# Start the server
echo "Starting server..."
python3 run.py --name $NAME --monitor_overview $OVERVIEW --measurement_noise_level $NOISE