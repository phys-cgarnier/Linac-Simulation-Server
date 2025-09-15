#!/usr/bin/env bash

cd "$(dirname "${BASH_SOURCE[0]}")"

#  Activate the conda environment from environment.yml
conda activate linac-simulation || (echo "Could not activate conda environment 'linac-simulation'. Did you run 'conda env create -f environment.yml'?" && exit 1)
# Setup epics vars
source env_vars.sh

# Check for provided arguments or provide defaults
NAME="${1:-diag0}"
OVERVIEW="${2:-False}"
NOISE="${3:-0.0}"


# Start the server
echo "Starting server..."
python3 run.py --name $NAME --monitor_overview $OVERVIEW --measurement_noise_level $NOISE
