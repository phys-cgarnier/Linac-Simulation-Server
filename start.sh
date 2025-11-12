#!/usr/bin/env bash
cd "$(dirname "${BASH_SOURCE[0]}")"
#  Activate conda environment and set EPICS env variables


source setup-epics-conda.sh
LATTICE_FLAG="${1:-0}"
if [ "$LATTICE_FLAG" = "0" ]; then
    export LCLS_LATTICE=/sdf/group/ad/sw/scm/repos/optics/lcls-lattice/cheetah
else
    echo Overriding LCLS_LATTICE to use local copy provided: $1
    export LCLS_LATTICE=$1
fi

 
NAME="${2:-diag0}"
OVERVIEW="${3:-}"
NOISE="${4:-0.0}"
# Start the server
echo "Starting server..."
python3 run.py --name "$NAME" --monitor_overview "$OVERVIEW" --measurement_noise_level "$NOISE"
