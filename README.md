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
***Note: Dev-srv09 has its own epics configuration files and conda environment that natively support the server without the user having to do anything special***

### Accessing PVs

On a separate terminal, the setup-epics-conda.sh script will setup your environment appropriately to access the PVs served by the server.

Make sure you source this script before attempting to access PVs using caget/pvget, or tools like Badger.

```
$ cd Linac-Simulation-Server/
$ source setup-epics-conda.sh
$ caget YOUR_FAVORITE_SIMULATED_PV
```

It is _not_ necessary to source setup-epics-conda.sh before running `./start.sh`, as that setup is handled automatically by `start.sh`. This is simply a way to configure your epics broadcasting to read from the the PVs being served by the Linac Simulation Server.

To confirm the PVs you are accessing are in fact being served by the simulated server, calling `cainfo` on a PV should return a host value of `localhost:<EPICS_CA_SERVER_PORT value set by setup-epics-conda.sh>`. The output should look something like this:

```
  State:            connected
  Host:             localhost:10512
  Access:           read, write
  Native data type: DBF_DOUBLE
  Request type:     DBR_DOUBLE
  Element count:    1
```

When trying to run the server on a shared machine (like dev-srv09), another user may already be running the server on the same ports.
In this case the server will use random ports instead, and you must set both `EPICS_CA_SERVER_PORT` and `EPICS_PVA_SERVER_PORT` again accordingly in any clients.
The server should print the new ports into the terminal.

You can also specify specific ports for the server to try and use (it will fallback to finding random ports if those specified are already taken), by setting the env-vars `LINAC_SIM_SERVER_CA_PORT` and `LINAC_SIM_SERVER_PVA_PORT` before running `setup-epics-conda.sh` or `run.sh`:
```
export LINAC_SIM_SERVER_CA_PORT=5555
export LINAC_SIM_SERVER_PVA_PORT=6666

# if client
source setup-epics-conda.sh
caget <pv>

# if server
./start.sh
```

### About the setup/start scripts
This repo provides two helper scripts:

- **`setup-epics-conda.sh`** – Sets EPICS environment variables and activates the conda environment.  
- **`start.sh`** – Sources `setup-epics-conda.sh` and launches the server.  
  - Supports **default arguments** if none are provided.  
  - Can also take up to four positional command-line arguments.

#### Command-line arguments for `start.sh`

You can pass up to four positional arguments:

```bash
./start.sh $1 $2 $3 $4
```
Missing arguments will fall back to defaults.

| Argument | Description                                          | Options / Type          | Default |
| -------- | ---------------------------------------------------- | ----------------------- | ------- |
| `$1`     | LCLS\_LATTICE override. Use the repo lattice if set. | `0` (default_path), `/abs/path` | `0` (default_path)     |
| `$2`     | Physics model to simulate.                           | `diag0`, `nc_injector`  | `diag0` |
| `$3`     | Print an overview plot each time a PV changes.       | `True`, `False`         | `False` |
| `$4`     | Noise level to add to simulation.                    | Float                   | `0.0`   |

* Example usage: `./start.sh /abs/lattice/path nc_injector`, **note: missing positional arguments resolve to defaults**

### Badger
```
$ source /sdf/sw/epics/package/anaconda/envs/rhel7_devel/bin/activate
$ source setup-epics-conda.sh
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
