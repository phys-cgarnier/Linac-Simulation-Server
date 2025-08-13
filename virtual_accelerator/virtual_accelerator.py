from cheetah.accelerator import Segment
from cheetah.particles import ParticleBeam
import torch
from virtual_accelerator.pv_mapping import access_cheetah_attribute, get_pv_mad_mapping


class VirtualAccelerator:
    def __init__(
        self,
        lattice_file,
        mapping_file,
        initial_beam_distribution,
        beam_shutter_pv=None,
    ):
        self.lattice = Segment.from_lattice_json(lattice_file)
        self.mapping = get_pv_mad_mapping(mapping_file)
        self.initial_beam_distribution = initial_beam_distribution
        self.initial_beam_distribution_charge = (
            initial_beam_distribution.particle_charges
        )

        # store the beam shutter PV name
        self.beam_shutter_pv = beam_shutter_pv

        # do a first run to populate readings
        self.lattice.track(incoming=self.initial_beam_distribution)

    def get_energy(self):
        """
        Get the energy of the beam in the virtual accelerator simulator at
        every element for use in calculating the magnetic rigidity.
        """
        test_beam = ParticleBeam(
            torch.zeros(1, 7), energy=self.initial_beam_distribution.energy
        )
        element_names = [e.name for e in self.lattice.elements]
        return dict(
            zip(
                element_names,
                self.lattice.get_beam_attrs_along_segment(("energy",), test_beam)[0],
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

    def get_pvs(self, pv_names: list):
        """
        Get the current value of the specified process variable (PV) from the virtual accelerator simulator.
        """

        values = {}
        for pv_name in pv_names:
            # handle the beam shutter separately
            if pv_name == self.beam_shutter_pv:
                values[pv_name] = (
                    self.initial_beam_distribution.particle_charges.item() == 0.0
                )
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

                values[pv_name] = access_cheetah_attribute(
                    element, attribute_name, energy
                )

            else:
                raise ValueError(f"Invalid PV base name: {base_pv_name}")

        return {name: ele.item() for name,ele in values.items()}
