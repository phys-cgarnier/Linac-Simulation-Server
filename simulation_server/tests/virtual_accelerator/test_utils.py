import numpy as np
from simulation_server.virtual_accelerator.utils import add_noise


class TestUtils:
    def test_add_noise(self):
        # Test with 1D array
        data_1d = np.ones(100)
        noisy_1d = add_noise(data_1d, noise_level=0.1)
        assert noisy_1d.shape == data_1d.shape
        assert not np.array_equal(noisy_1d, data_1d)

        # Test with 2D array
        data_2d = np.ones((50, 50))
        noisy_2d = add_noise(data_2d, noise_level=0.1)
        assert noisy_2d.shape == data_2d.shape
        assert not np.array_equal(noisy_2d, data_2d)

        # Check that noise is within expected range
        assert np.all(noisy_1d >= 0)
        assert np.all(noisy_2d >= 0)
