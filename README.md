# Simulated Linac using Cheetah and PCASpy

This project provides a simulated EPICS server that hosts PVs using PCASpy. The simulation is designed to work with the Cheetah accelerator framework and includes examples for interfacing with the lcls-tools.


## Setup Instructions
To set up and run the simulated server, follow these steps:
### TL;DR
- **Local**: create a conda env, then `./start.sh`
- **SLAC dev-srv09 server**: EPICS + conda are pre-provisioned; just `./start.sh`

### Setting up the environment and starting the simulation server locally:

#### Clone the Simulation Server
```sh
$ git clone https://github.com/slaclab/Linac-Simulation-Server.git
```
#### Create the conda environment
```sh
$ cd Linac-Simulation-Server
$ conda env create -f environment.yml
```
#### Start the server
```sh
$ source start.sh
```

### Setting up the environment and starting the simulation server on SLACs development servers :

#### Clone the Simulation Server
```sh
$ git clone https://github.com/slaclab/Linac-Simulation-Server.git
```

#### Start the server
```sh
$ source start.sh
```
***Note: Dev-srv09 has its own epics configuration files and conda environment that natively supports the server without the User having to do anything special***

### Accessing PVs

On a separate terminal, the setup-epics-conda.sh script will setup your environment appropriately to access the PVs served by the server.

Make sure you source this script before attempting to access PVs using caget/pvget, or tools like Badger.

```
$ cd Linac-Simulation-Server/
$ source setup-epics-conda.sh
caget YOUR_FAVORITE_SIMULATED_PV
```
It is _not_ necessary to source setup-epics-conda.sh before running `start.sh`, as that setup is handled automatically by `start.sh`. This is simply a way to configure your epics broadcasting to read from the the PVs being served by the Linac Simulation Server.

### About the setup/start scripts
The repo comes with two scripts:
* _setup-epics-conda.sh_ which sets up the epics environment variables and activates the conda environment*
* _start.sh_ calls _setup-epics-conda.sh_ and starts the server with default arguments *

#### Badger
```
$ source /sdf/sw/epics/package/anaconda/envs/rhel7_devel/bin/activate
$ cd Badger-Resources/cu_hxr
$ badger -g -cf config.yaml
```

Please update config.yaml with correct paths. Choose nc_inj_emit environment. Choose process variables and use emittance_x as objective. Before pressing run, set measure_background to false. 

<br/>
<img src="Screenshot.png" alt="drawing" width="1000"/>
<br/><br/>

**Warning** Not all PVs are currently supported in the Linac Simulation Server.

## Examples:

This repository includes example scripts demonstrating how to interface with the simulated EPICS server using the lcls-tools module, which is available in the provided environment. These examples illustrate how to read from and write to process variables (PVs).

## Dependencies:

The required dependencies are listed in environment.yml, ensuring a reproducible setup. The environment includes:

PCASpy for hosting EPICS PVs

Cheetah for beam simulation

lcls-tools for interfacing with EPICS

## Additional Notes

Ensure that all dependencies are installed properly and that the `setup-epics-conda.sh` script is sourced before trying to access PVs exported by the server. Otherwise, you may unexpectedly
access PVs exported by real IOCs on the DEV or PROD networks (depending on your gateway settings).

For any issues, verify that the required environment is activated and that caget and caput can communicate with the hosted PVs.

You will also need to provide your own beam distribution (this setup is designed to run on the LCLS-I Cu Injector)
