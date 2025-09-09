import os
import pathlib
import argparse

from simulation_server.utils.load_yaml import load_relevant_controls
from simulation_server.utils.pvdb import create_pvdb
from simulation_server.beamdriver import SimDriver, SimServer
from simulation_server.factory import get_virtual_accelerator

FILEPATH = pathlib.Path(__file__).parent.resolve()


def run_simulation_server(name, monitor_overview, measurement_noise_level):
    if name == "diag0":
        devices = load_relevant_controls(
            os.path.join(FILEPATH, "simulation_server", "yaml_configs", "DIAG0.yaml")
        )

    elif name == "nc_injector":
        devices = load_relevant_controls(
            os.path.join(
                FILEPATH, "simulation_server", "yaml_configs", "DL1_2_OTR2.yaml"
            )
        )
    else:
        raise ValueError(f"Unknown virtual accelerator name: {name}")

    PVDB = create_pvdb(devices)

    va = get_virtual_accelerator(name, monitor_overview, measurement_noise_level)
    server = SimServer(PVDB)
    driver = SimDriver(server=server, devices=devices, virtual_accelerator=va)

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
        action="store_true",
        help="If set, print out an overview plot of the accelerator simulation each time a PV is changed.",
    )
    parser.add_argument(
        "--measurement_noise_level",
        type=float,
        default=None,
        help="If provided, adds realistic noise to measurements. See `simulation_server.virtual_accelerator.utils.add_noise` for details.",
    )

    args = parser.parse_args()
    run_simulation_server(
        args.name, args.monitor_overview, args.measurement_noise_level
    )
