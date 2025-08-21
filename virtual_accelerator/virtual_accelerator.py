from copy import deepcopy
from cheetah.accelerator import Segment
from cheetah.particles import ParticleBeam
from matplotlib import pyplot as plt
import torch
from virtual_accelerator.pv_mapping import access_cheetah_attribute, get_pv_mad_mapping


class VirtualAccelerator:
    def __init__(
        self,
        lattice_file,
        mapping_file,
        initial_beam_distribution,
        beam_shutter_pv=None,
        monitor_overview=False,
    ):
        """
        Virtual accelerator class based on cheetah beam dynamics simulations. 
        Runs a new cheetah tracking simulation any time a process variable (PV) is updated.

        Parameters
        ----------
        lattice_file : str
            Path to the cheetah lattice JSON file.
        mapping_file : str
            Path to the mapping CSV file that maps PV base names 
            to corresponding MAD names used in cheetah.
        initial_beam_distribution : ParticleBeam
            Initial beam distribution to be used in the simulation.
        beam_shutter_pv : str, optional
            Process variable (PV) name for the beam shutter.
        monitor_overview : bool, optional
            Whether to monitor the overview of the simulation. If True, the overview 
            plot from cheetah will be generated and saved every time a new simulation is run.

        """
        self.lattice_file = lattice_file
        self.mapping_file = mapping_file

        self.lattice = Segment.from_lattice_json(lattice_file)
        self.mapping = get_pv_mad_mapping(mapping_file)

        self.initial_beam_distribution = initial_beam_distribution
        self.initial_beam_distribution_charge = (
            initial_beam_distribution.particle_charges
        )
        self.monitor_overview = monitor_overview

        # store the beam shutter PV name
        self.beam_shutter_pv = beam_shutter_pv

        # do a first run to populate readings
        self.lattice.track(incoming=self.initial_beam_distribution)

        if self.monitor_overview:
            self._monitor_index = 0
            fig = plt.figure()
            self.lattice.plot_overview(incoming=self.initial_beam_distribution, fig=fig)
            fig.savefig(f"simulation_overview_{self._monitor_index:04d}.png")

    def reset(self):
        """ reset the simulation """
        print("resetting the simulation")

        self.lattice = Segment.from_lattice_json(self.lattice_file)
        self.mapping = get_pv_mad_mapping(self.mapping_file)
        self.lattice.track(incoming=self.initial_beam_distribution)

        if self.monitor_overview:
            self._monitor_index = 0
            fig = plt.figure()
            self.lattice.plot_overview(incoming=self.initial_beam_distribution, fig=fig)
            fig.savefig(f"simulation_overview_{self._monitor_index:04d}.png")

    def get_energy(self):
        """
        Get the energy of the beam in the virtual accelerator simulator at
        every element for use in calculating the magnetic rigidity.
        
        Note: need to track on a copy of the lattice to not influence readings!
        """
        test_beam = ParticleBeam(
            torch.zeros(1, 7), energy=self.initial_beam_distribution.energy
        )
        test_lattice = deepcopy(self.lattice)
        element_names = [e.name for e in test_lattice.elements]
        return dict(
            zip(
                element_names,
                test_lattice.get_beam_attrs_along_segment(("energy",), test_beam)[0],
            )
        )

    def set_shutter(self, value: bool):
        """
        Set the beam shutter state in the virtual accelerator simulator.
        If `value` is True, the shutter is closed (no beam), otherwise it is open (beam present).
        """
        if value:
            self.initial_beam_distribution.particle_charges = torch.tensor(0.0)
        else:
            self.initial_beam_distribution.particle_charges = (
                self.initial_beam_distribution_charge
            )

        # run the simulation to update readings
        self.lattice.track(incoming=self.initial_beam_distribution)

    def set_pvs(self, values: dict):
        """
        Set the corresponding process variable (PV) to the given value on the virtual accelerator simulator.
        """
        for pv_name, value in values.items():
            # handle the beam shutter separately
            if pv_name == self.beam_shutter_pv:
                self.set_shutter(value)
                continue

            if pv_name == "VIRT:BEAM:RESET_SIM":
                self.reset()
                continue

            # get the base pv name
            base_pv_name = ":".join(pv_name.split(":")[:3])
            attribute_name = ":".join(pv_name.split(":")[3:])

            # get the beam energy along the lattice -- returns a dict of element names to energies
            beam_energy_along_lattice = self.get_energy()

            # check if the pv_name is a control variable
            if base_pv_name in self.mapping:
                # set the value in the virtual accelerator simulator
                element = getattr(self.lattice, self.mapping[base_pv_name].lower())

                # get the beam energy for the element
                energy = beam_energy_along_lattice[self.mapping[base_pv_name].lower()]

                # if there are duplicate elements, just grab the first one (both will be adjusted)
                if isinstance(element, list):
                    element = element[0]

                try:
                    access_cheetah_attribute(element, attribute_name, energy, value)
                except ValueError as e:
                    raise ValueError(f"Failed to set PV {pv_name}: {str(e)}") from e

            else:
                raise ValueError(f"Invalid PV base name: {base_pv_name}")

        # at the end of setting all PVs, run the simulation with the initial beam distribution
        # this will update all readings (screens, BPMs, etc.) in the lattice
        self.lattice.track(incoming=self.initial_beam_distribution)

        if self.monitor_overview:
            self._monitor_index += 1
            fig = plt.figure()
            self.lattice.plot_overview(incoming=self.initial_beam_distribution, fig=fig)
            fig.savefig(f"simulation_overview_{self._monitor_index:04d}.png")

    def get_pvs(self, pv_names: list):
        """
        Get the current value of the specified process variable (PV) from the virtual accelerator simulator.
        """
        values = {}
        for pv_name in pv_names:
            # handle the beam shutter separately
            if pv_name == self.beam_shutter_pv:
                values[pv_name] = torch.all(
                    self.initial_beam_distribution.particle_charges == 0.0
                )
                continue

            if pv_name == "VIRT:BEAM:RESET_SIM":
                values[pv_name] = 0
                continue

            # get the base pv name
            base_pv_name = ":".join(pv_name.split(":")[:3])
            print(base_pv_name)
            attribute_name = ":".join(pv_name.split(":")[3:])

            # get the beam energy along the lattice
            beam_energy_along_lattice = self.get_energy()

            # check if the pv_name is a control variable
            if base_pv_name in self.mapping:
                element = getattr(self.lattice, self.mapping[base_pv_name].lower())
                # get the beam energy for the element
                energy = beam_energy_along_lattice[self.mapping[base_pv_name].lower()]

                # if there are duplicate elements, just grab the first one (both will be adjusted)
                if isinstance(element, list):
                    element = element[0]

                print("accessing element " + element.name + " for PV " + pv_name)
                values[pv_name] = access_cheetah_attribute(
                    element, attribute_name, energy
                )

            else:
                raise ValueError(f"Invalid PV base name: {base_pv_name}")

        # sanitize outputs
        for name, ele in values.items():
            if isinstance(ele, torch.Tensor):
                if ele.shape == torch.Size([]):
                    values[name] = ele.item()
                elif len(ele.shape) > 0:
                    values[name] = ele.flatten().tolist()

        return values
