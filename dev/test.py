import os

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from cheetah.particles import ParticleBeam
from cheetah.accelerator import Screen
from matplotlib import pyplot as plt
import torch
from virtual_accelerator.virtual_accelerator import VirtualAccelerator
import os

incoming_beam = ParticleBeam.from_twiss(
    beta_x=torch.tensor(9.34),
    alpha_x=torch.tensor(-1.6946),
    emittance_x=torch.tensor(1e-7),
    beta_y=torch.tensor(9.34),
    alpha_y=torch.tensor(-1.6946),
    emittance_y=torch.tensor(1e-7),
    energy=torch.tensor(90e6),
    num_particles=1000,
    total_charge=torch.tensor(1e-9),
)

# Initialize the virtual accelerator with a the diag0 lattice file and mapping file
va = VirtualAccelerator(
    lattice_file=os.path.join(
        os.path.split(os.path.abspath(__file__))[0],
        "virtual_accelerator",
        "tests",
        "resources",
        "diag0.json",
    ),
    mapping_file=os.path.join(
        os.path.split(os.path.abspath(__file__))[0],
        "virtual_accelerator",
        "tests",
        "resources",
        "lcls_elements.csv",
    ),
    initial_beam_distribution=incoming_beam,
)

plt.imshow(va.lattice.otrdg02.reading)

va.set_pvs({"QUAD:DIAG0:190:BCTRL": 0.0})

plt.figure()
plt.imshow(va.lattice.otrdg02.reading)
plt.show()
