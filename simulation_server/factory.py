import torch
import os
import pathlib

from cheetah.particles import ParticleBeam

from simulation_server.virtual_accelerator import VirtualAccelerator

FILEPATH = pathlib.Path(__file__).parent.resolve()

def get_virtual_accelerator(name, monitor_overview=False):
    """
    Create an instance of VirtualAccelerator for a given beamline.

    Parameters
    ----------
    name: str
        The name of the virtual accelerator. Current options are:
            - diag0
            - cu_injector
    monitor_overview: bool, optional
        If True, print out an overview plot of the accelerator 
        simulation each time a PV is changed.

    Returns
    -------
    VirtualAccelerator
        An instance of the VirtualAccelerator class.

    """
    if name == "diag0":
        incoming_beam = ParticleBeam.from_twiss(
            beta_x=torch.tensor(9.34),
            alpha_x=torch.tensor(-1.6946),
            emittance_x=torch.tensor(1e-7),
            beta_y=torch.tensor(9.34),
            alpha_y=torch.tensor(-1.6946),
            emittance_y=torch.tensor(1e-7),
            energy=torch.tensor(90e6),
            num_particles=100000,
            total_charge=torch.tensor(1.0),
        )

        mapping_file = os.path.join(FILEPATH, "mappings", "lcls_elements.csv")
        lattice_file = os.path.join(FILEPATH, "lattices", "new_diag0.json")

    elif name == "nc_injector":
        incoming_beam = ParticleBeam.from_openpmd_file(
            path=os.path.join(FILEPATH, "beams", "impact_inj_output_YAG03.h5"),
            energy = torch.tensor(135e6),
            dtype=torch.float32
        )
        incoming_beam.particle_charges = torch.tensor(1.0)

        mapping_file = os.path.join(FILEPATH, "mappings", "lcls_elements.csv")
        lattice_file = os.path.join(FILEPATH, "lattices", "lcls_cu_segment_otr2.json")

    return VirtualAccelerator(
            lattice_file=lattice_file,
            initial_beam_distribution=incoming_beam,
            mapping_file=mapping_file,
            monitor_overview=monitor_overview,
        )
