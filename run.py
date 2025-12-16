import os
import pathlib
import argparse

from simulation_server.utils.load_yaml import load_relevant_controls
from simulation_server.utils.pvdb import create_pvdb
from simulation_server.beamdriver import SimDriver, SimServer
from simulation_server.factory import get_virtual_accelerator
import simulation_server.utils.default_params as DEFAULTS
import lcls_tools.common.devices.yaml as yaml_directory
import pprint

FILEPATH= pathlib.Path(yaml_directory.__file__).parent.resolve()
#FP= pathlib.Path(__file__).parent.resolve()
def run_simulation_server(name, monitor_overview, measurement_noise_level, threaded):
    if name == "diag0":
        devices = load_relevant_controls(
            os.path.join( FILEPATH, "DIAG0.yaml")
        )
        default_params = DEFAULTS.default_sc_diag0

    elif name in ("nc_injector", 'nc_hxr'):
        devices = load_relevant_controls(
            os.path.join( FILEPATH, "DL1.yaml")
            #os.path.join(FP,"simulation_server","yaml_configs", "DL1.yaml")
        )
        default_params = DEFAULTS.default_nc_hxr

    else:
        raise ValueError(f"Unknown virtual accelerator name: {name}")

    PVDB = create_pvdb(devices,default_params)
    
    va = get_virtual_accelerator(name, monitor_overview, measurement_noise_level)
    server = SimServer(PVDB, threading=threaded)
    driver = SimDriver(server=server, virtual_accelerator=va)

    print("Starting simulated server")
    server.run()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the simulation server.")
    parser.add_argument(
        "--name",
        type=str,
        choices=["diag0", "nc_injector"],
        required=True,
        help="Name of the virtual accelerator to simulate.",
    )
    parser.add_argument(
        "--monitor_overview",
        type=bool,
        default=False,
        help="Print out an overview plot of the accelerator simulation each time a PV is changed.",
    )
    parser.add_argument(
        "--measurement_noise_level",
        type=float,
        default=None,
        help="If provided, adds realistic noise to measurements. See `simulation_server.virtual_accelerator.utils.add_noise` for details.",
    )
    parser.add_argument(
        "--threaded",
        action="store_true",
        help="Enable threaded evaluation of the model, triggered with the VIRT:BEAM:SIMULATE PV"
    )

    args = parser.parse_args()
    run_simulation_server(
        args.name, args.monitor_overview, args.measurement_noise_level, args.threaded
    )
