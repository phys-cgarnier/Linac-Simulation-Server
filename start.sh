#!/usr/bin/env bash
cd "$(dirname "${BASH_SOURCE[0]}")"
#  Activate conda environment and set EPICS env variables
source ./setup_epics_conda.sh
# Check for provided arguments or provide defaults
NAME="${1:-diag0}"
OVERVIEW="${2:-False}"
NOISE="${3:-0.0}"


# Start the server
echo "Starting server..."
python3 run.py --name $NAME --monitor_overview $OVERVIEW --measurement_noise_level $NOISE
