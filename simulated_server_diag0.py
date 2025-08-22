from cheetah.particles import ParticleBeam
from beamdriver import SimDriver, SimServer
import torch
from utils.load_yaml import load_relevant_controls
from utils.pvdb import create_pvdb

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

devices = load_relevant_controls("yaml_configs/DIAG0.yaml")
PVDB = create_pvdb(devices)

# TODO: add these back in
custom_pvs = {
#    "VIRT:BEAM:EMITTANCES": {"type": "float", "count": 2},
#    "VIRT:BEAM:MU:XY": {"type": "float", "count": 2},
#    "VIRT:BEAM:SIGMA:XY": {"type": "float", "count": 2},
#    "VIRT:BEAM:RESET_SIM": {"value": 0},
}
PVDB.update(custom_pvs)
mapping_file = "mappings/lcls_elements.csv"
lattice_file = "lattices/new_diag0.json"
server = SimServer(PVDB)
driver = SimDriver(
    server=server,
    devices=devices,
    particle_beam=incoming_beam,
    lattice_file=lattice_file,
    mapping_file=mapping_file,
    monitor_overview=False,
)

print("Starting simulated server")
server.run()
