#!/usr/bin/env bash

# Optionally, you can make the server use specific ca and pva server ports by specifying the following two env variables:
#   LINAC_SIM_SERVER_CA_PORT -> sets EPICS_CA_SERVER_PORT (default: 10512)
#   LINAC_SIM_SERVER_PVA_PORT -> sets EPICS_PVA_SERVER_PORT (default: 10415)
# (Note: setting EPICS_[CA|PVA]_SERVER_PORT directly in your own shell will not z
# -----------------------------------------------------------------------------

LINAC_SIM_SERVER_CA_PORT=${LINAC_SIM_SERVER_CA_PORT:-10512} # `:-` is bash syntax, not negative num
LINAC_SIM_SERVER_PVA_PORT=${LINAC_SIM_SERVER_PVA_PORT:-10415}

if [ -f /sdf/group/cds/sw/epics/setup/setupEpics.bash ]; then
     echo "Sourcing EPICS and conda from /sdf/group/cds/sw/epics"
     source /sdf/group/cds/sw/epics/setup/setupEpics.bash
     source /sdf/sw/epics/package/anaconda/envs/rhel7_devel/bin/activate
else 
     echo "Activating Conda from the Users environment"
     conda activate linac-simulation || (echo "Could not activate conda environment 'linac-simulation'. Did you run 'conda env create -f environment.yml'?" && exit 1)
fi

# Configures EPICS CA and PVA for use with Linac-Simulation-Server
# Channel access settings

echo "Using EPICS_CA_SERVER_PORT=$LINAC_SIM_SERVER_CA_PORT and EPICS_PVA_SERVER_PORT=$LINAC_SIM_SERVER_PVA_PORT"
export EPICS_CA_SERVER_PORT=$LINAC_SIM_SERVER_CA_PORT
export EPICS_CA_ADDR_LIST=127.0.0.1
export EPICS_CA_AUTO_ADDR_LIST=NO
# Ensure we have enough space for large arrays
export EPICS_CA_MAX_ARRAY_BYTES=80000000

# PVA settings
export EPICS_PVA_SERVER_PORT=$LINAC_SIM_SERVER_PVA_PORT
export EPICS_PVA_ADDR_LIST=127.0.0.1
export EPICS_PVA_AUTO_ADDR_LIST=YES
