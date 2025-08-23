from cheetah.accelerator import (
    Segment,
    Quadrupole,
    HorizontalCorrector,
    VerticalCorrector,
    BPM,
    Screen,
    TransverseDeflectingCavity,
)
from cheetah.particles import ParticleBeam
import pytest
import torch

from ..pv_mapping import access_cheetah_attribute


class TestPVMapping:
    def setup_method(self):
        # Create a mock lattice with various elements
        quad1 = Quadrupole(name="quad1", length=torch.tensor(1.0), k1=torch.tensor(0.0))
        hcor1 = HorizontalCorrector(
            name="hcor1", angle=torch.tensor(0.0), length=torch.tensor(0.1)
        )
        vcor1 = VerticalCorrector(
            name="vcor1", angle=torch.tensor(0.0), length=torch.tensor(0.1)
        )
        bpm1 = BPM(name="bpm1", is_active=True)
        screen1 = Screen(
            name="screen1",
            is_active=True,
            resolution=[10, 10],
            pixel_size=torch.tensor([0.1, 0.1])*1e-6, # should be in units of meters
        )
        tcav1 = TransverseDeflectingCavity(
            name="tcav1",
            voltage=torch.tensor(0.0),
            phase=torch.tensor(45.0),
            length=torch.tensor(0.1),
        )

        self.lattice = Segment(elements=[quad1, hcor1, vcor1, bpm1, screen1, tcav1])

        # create a mock beam
        beam = ParticleBeam(particles=torch.tensor([[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0]]), energy=torch.tensor(1.0))

        # track the beam through the lattice so the reading attributes are populated
        self.lattice.track(beam)

    def test_set_pvs(self):
        # Set values for various PVS
        values = {
            "quad1:BCTRL": 0.5,
            "hcor1:BCTRL": 0.1,
            "vcor1:BCTRL": 0.2,
            "tcav1:AREQ": 1.0,
            "tcav1:PREQ": 45.0,
        }
        energy = 2e9 / 33.356  # energy in eV such that the magnetic rigidity is 2 kG-m

        for name, value in values.items():
            base_pv_name = name.split(":")[0]
            attribute_name = name.split(":")[1]

            element = getattr(self.lattice, base_pv_name)
            access_cheetah_attribute(element, attribute_name, energy, value)

        # Verify that the values were set correctly
        assert torch.isclose(self.lattice.quad1.k1, torch.tensor(0.5) / 2)
        assert torch.isclose(self.lattice.hcor1.angle, torch.tensor(0.1) / 2)
        assert torch.isclose(self.lattice.vcor1.angle, torch.tensor(0.2) / 2)

        # try setting something that cannot be set
        values = {
            "bpm1:XSCDT1H": 0.5,
            "quad1:BACT": 0.3,
            "hcor1:BACT": 0.4,
            "vcor1:BACT": 0.5,
            "screen1:Image:ArrayData": [1, 2, 3],
            "screen1:RESOLUTION": [0.1, 0.1], # should be in units of microns
            "screen1:Image:ArraySize2_RBV": [4, 5],
        }

        for name, value in values.items():
            base_pv_name = name.split(":")[0]
            attribute_name = name.split(":")[1]

            element = getattr(self.lattice, base_pv_name)

            with pytest.raises(ValueError):
                access_cheetah_attribute(element, attribute_name, energy, value)

    def test_get_pvs(self):
        # Get values for various PVS
        pv_name_values = {
            "quad1:BCTRL": 0.0,
            "hcor1:BACT": 0.0,
            "vcor1:BACT": 0.0,
            "screen1:RESOLUTION": 0.1,
            "screen1:Image:ArraySize1_RBV": 10,
            "tcav1:AREQ": 0.0,
            "tcav1:PREQ": 45.0,
        }
        energy = 1e9 / 33.356  # energy in eV such that the magnetic rigidity is 1 kG-m

        for pv_name, expected_value in pv_name_values.items():
            base_pv_name = pv_name.split(":")[0]
            attribute_name = ":".join(pv_name.split(":")[1:])

            element = getattr(self.lattice, base_pv_name)
            result = access_cheetah_attribute(element, attribute_name, energy)

            assert torch.isclose(torch.tensor(result), torch.tensor(expected_value))
