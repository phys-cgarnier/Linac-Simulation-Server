import pytest

from simulation_server.factory import get_virtual_accelerator
import matplotlib.pyplot as plt
import numpy as np

class TestInjectorVA:
    @pytest.fixture(autouse=True)
    def setup_method(self):
        # Create an instance of the virtual accelerator for the injector
        self.va = get_virtual_accelerator(name="nc_injector")

    def test_otr_image(self):
        otr_pv = "OTRS:IN20:571:Image:ArrayData"
        output = self.va.get_pvs([
            otr_pv,
            "OTRS:IN20:571:Image:ArraySize1_RBV",
            "OTRS:IN20:571:Image:ArraySize0_RBV",
        ])
        image = output[otr_pv]
        size_x = output["OTRS:IN20:571:Image:ArraySize0_RBV"]
        size_y = output["OTRS:IN20:571:Image:ArraySize1_RBV"]
        image = np.array(image).reshape((size_y, size_x))

        plt.figure()
        plt.imshow(image, cmap='gray')
        plt.title("OTR Image at OTR2")
        plt.colorbar(label='Intensity')
        plt.savefig("otr_image.png")
        plt.show()
