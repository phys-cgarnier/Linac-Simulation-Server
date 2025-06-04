#!/usr/bin/env bash

export EPICS_CA_ADDR_LIST=127.0.0.1
export EPICS_CA_AUTO_ADDR_LIST="NO"
export EPICS_CA_MAX_ARRAY_BYTES=1000000000
#export EPICS_CA_SERVER_PORT=12345

caRepeater&

python simulated_server_diag0.py