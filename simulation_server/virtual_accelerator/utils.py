import numpy as np


def add_noise(data, noise_level=0.1):
    """
    Adds random noise and hot pixels to 1 and 2D signals.

    Parameters:
    -----------
    data : np.ndarray
        1 or 2D array of signal data.
    noise_level : float
        Standard deviation of the Gaussian noise to be
        added.

    Returns:
    --------
    output : np.ndarray
        The input data with added noise and hot pixels.
    """
    max_signal = np.max(data)
    noise = np.random.normal(0, noise_level, data.shape)
    noisy_data = data + noise

    # add hot pixels
    num_hot_pixels = int(0.01 * data.size)  # 1%
    for _ in range(num_hot_pixels):
        x = np.random.randint(0, data.shape[0])
        y = np.random.randint(0, data.shape[1]) if data.ndim > 1 else None

        if data.ndim == 1:
            noisy_data[x] += np.random.uniform(1.1 * max_signal, max_signal)
        else:
            noisy_data[x, y] += np.random.uniform(1.1 * max_signal, max_signal)

    return noisy_data
