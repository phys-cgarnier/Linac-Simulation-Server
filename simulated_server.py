from cheetah.particles import ParticleBeam
from beamdriver import SimDriver, SimServer
import torch
from utils.load_yaml import load_relevant_controls
from utils.pvdb import create_pvdb

incoming_beam = ParticleBeam.from_openpmd_file(
    path='impact_inj_output_YAG03.h5', 
    energy = torch.tensor(135e6),
    dtype=torch.float32
    )
incoming_beam.particle_charges = torch.tensor(1.0)

devices = load_relevant_controls('yaml_configs/DL1_2_OTR2.yaml')
PVDB = create_pvdb(devices)
custom_pvs = {
#    'VIRT:BEAM:EMITTANCES': {'type':'float', 'count': 2},
#    'VIRT:BEAM:RESET_SIM': {'value': 0}   
}
PVDB.update(custom_pvs)
mapping_file = "mappings/lcls_elements.csv"
lattice_file = 'lattices/lcls_cu_segment_otr2.json'
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
