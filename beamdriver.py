from pcaspy import Driver, SimpleServer
from cheetah.particles import ParticleBeam
from cheetah.accelerator import Segment, Screen
import numpy as np
import torch
from scipy.stats import cauchy
import pprint
import math
from p4p.server.thread import SharedPV
from p4p.nt import NTScalar, NTNDArray, NTEnum
import p4p
from typing import Dict, Callable, Any
from virtual_accelerator.virtual_accelerator import VirtualAccelerator
class SimServer(SimpleServer):
    def __init__(self, pvdb: dict, prefix: str = ''):
        super().__init__()
        self.createPV(prefix, pvdb)

    def run(self):
        while True:
            self.process(0.1)

# TODO: set defaults for all tcav enum pvs
#  
class SimDriver(Driver):
    def __init__(self,
                 server: SimServer,
                 devices: dict,
                 mapping_file: str,
                 particle_beam: ParticleBeam = None,
                 lattice_file: str = None,
                  
                 ):
        super().__init__()
        self.virtual_accelerator = VirtualAccelerator(lattice_file=lattice_file,initial_beam_distribution=particle_beam,mapping_file=mapping_file)
        self.server = server
        self.devices = devices

    def read(self, reason):
        try:
            #TODO: If you try and get the beamspot here its as expected but the second you step in .get_pvs the beamspot is gone
            #TODO: that is a clue as to what is going on.
            #TODO: can prove this with plotting
            value_dict = self.virtual_accelerator.get_pvs([reason])
            value = value_dict[reason]
            try:
                return value
            except TypeError as e:
                print(f'type of value is {type(value)} with error {e}')
        except ValueError as e:
            print(e)
            return None


    def write(self, reason, value):
        try:
            self.virtual_accelerator.set_pvs({reason:value})
        except ValueError as e:
           print(e)
           




#TODO: add functionality to pop screens in and out