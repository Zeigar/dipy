from __future__ import division, print_function

import warnings
import numpy as np

from scipy.special import gammainccinv
from scipy.ndimage.filters import convolve
from scipy.stats import mode


def _inv_nchi_cdf(N, K, alpha):
    """Inverse CDF for the noncentral chi distribution
    See [1]_ p.3 section 2.3"""
    return gammainccinv(N * K, 1 - alpha) / K


def piesno(data, N, alpha=0.01, l=100, itermax=100, eps=1e-5, return_mask=False):
    """
    Probabilistic Identification and Estimation of Noise (PIESNO).

    Parameters
    -----------
    data : ndarray
        The magnitude signals to analyse. The last dimension must contain the
        same realisation of the volume, such as dMRI or fMRI data.

    N : int
        The number of phase array coils of the MRI scanner.
        If your scanner does a SENSE reconstruction, ALWAYS use N=1, as the noise
        profile is always Rician.
        If your scanner does a GRAPPA reconstruction, set N as the number
        of phase array coils.

    alpha : float
        Probabilistic estimation threshold for the gamma function.

    l : int
        number of initial estimates for sigma to try.

    itermax : int
        Maximum number of iterations to execute if convergence
        is not reached.

    eps : float
        Tolerance for the convergence criterion. Convergence is
        reached if two subsequent estimates are smaller than eps.

    return_mask : bool
        If True, return a mask identyfing all the pure noise voxel
        that were found.

    Returns
    --------
    sigma : float
        The estimated standard deviation of the gaussian noise.

    mask : ndarray (optional)
        A boolean mask indicating the voxels identified as pure noise.

    Note
    ------
    This function assumes two things : 1. The data has a noisy, non-masked
    background and 2. The data is a repetition of the same measurements
    along the last axis, i.e. dMRI or fMRI data, not structural data like T1/T2.

    This function processes the data slice by slice, as originally designed in
    the paper. Use it to get a slice by slice estimation of the noise, as in
    spinal cord imaging for example.

    References
    ------------

    .. [1] Koay CG, Ozarslan E and Pierpaoli C.
    "Probabilistic Identification and Estimation of Noise (PIESNO):
    A self-consistent approach and its applications in MRI."
    Journal of Magnetic Resonance 2009; 199: 94-103.

    .. [2] Koay CG, Ozarslan E and Basser PJ.
    "A signal transformational framework for breaking the noise floor
    and its applications in MRI."
    Journal of Magnetic Resonance 2009; 197: 108-119.
    """

    # This method works on a 2D array with repetitions as the third dimension,
    # so process the dataset slice by slice.
    if data.ndim < 3:
        raise ValueError("This function only works on datasets of at least 3 dimensions.")

    if data.ndim == 4:

        sigma = np.zeros(data.shape[-2], dtype=np.float32)
        mask_noise = np.zeros(data.shape[:-1], dtype=np.bool)

        for idx in range(data.shape[-2]):
            sigma[idx], mask_noise[..., idx] = _piesno_3D(data[..., idx, :], N,
                                                          alpha=alpha,
                                                          l=l,
                                                          itermax=itermax,
                                                          eps=eps,
                                                          return_mask=True)

    else:
        sigma, mask_noise = _piesno_3D(data, N,
                                       alpha=alpha,
                                       l=l,
                                       itermax=itermax,
                                       eps=eps,
                                       return_mask=True)

    if return_mask:
        return sigma, mask_noise

    return sigma


def _piesno_3D(data, N, alpha=0.01, l=100, itermax=100, eps=1e-5, return_mask=False):
    """
    Probabilistic Identification and Estimation of Noise (PIESNO).
    This is the slice by slice version for working on a 4D array.

    Parameters
    -----------
    data : ndarray
        The magnitude signals to analyse. The last dimension must contain the
        same realisation of the volume, such as dMRI or fMRI data.

    N : int
        The number of phase array coils of the MRI scanner.

    alpha : float
        Probabilistic estimation threshold for the gamma function.

    l : int
        number of initial estimates for sigma to try.

    itermax : int
        Maximum number of iterations to execute if convergence
        is not reached.

    eps : float
        Tolerance for the convergence criterion. Convergence is
        reached if two subsequent estimates are smaller than eps.

    return_mask : bool
        If True, return a mask identyfing all the pure noise voxel
        that were found.

    Returns
    --------
    sigma : float
        The estimated standard deviation of the gaussian noise.

    mask : ndarray
        A boolean mask indicating the voxels identified as pure noise.

    Note
    ------
    This function assumes two things : 1. The data has a noisy, non-masked
    background and 2. The data is a repetition of the same measurements
    along the last axis, i.e. dMRI or fMRI data, not structural data like T1/T2.

    References
    ------------

    .. [1] Koay CG, Ozarslan E and Pierpaoli C.
    "Probabilistic Identification and Estimation of Noise (PIESNO):
    A self-consistent approach and its applications in MRI."
    Journal of Magnetic Resonance 2009; 199: 94-103.

    .. [2] Koay CG, Ozarslan E and Basser PJ.
    "A signal transformational framework for breaking the noise floor
    and its applications in MRI."
    Journal of Magnetic Resonance 2009; 197: 108-119.
    """

>>>>>>> Force merged mdesco example branch on top of arokem branch
    # Get optimal quantile for N if available, else use the median.
    opt_quantile = {1: 0.79681213002002,
                    2: 0.7306303027491917,
                    4: 0.6721952960782169,
                    8: 0.6254030432343569,
                   16: 0.5900487123737876,
                   32: 0.5641772300866416,
                   64: 0.5455611840489607,
                  128: 0.5322811923303339}

    if N in opt_quantile:
        q = opt_quantile[N]
    else:
        q = 0.5

    # Initial estimation of sigma
    denom = np.sqrt(2 * _inv_nchi_cdf(N, 1, q))
    m = np.percentile(data, q * 100) / denom

    # if the percentile is 0, then more than half of the slice is zero and give up
    if m == 0:
        warnings.warn("Initial estmated value of noise is 0 for current slice")
        if return_mask:
            return 0, np.zeros(data.shape[:-1], dtype=np.bool)

        return 0

    phi = np.arange(1, l + 1) * m / l
    K = data.shape[-1]
    sum_m2 = np.sum(data**2, axis=-1, dtype=np.float32)

    sigma = np.zeros(phi.shape, dtype=phi.dtype)
    mask = np.zeros(phi.shape + data.shape[:-1])

    lambda_minus = _inv_nchi_cdf(N, K, alpha/2)
    lambda_plus = _inv_nchi_cdf(N, K, 1 - alpha/2)

    pos = 0
    max_length_omega = 0

    for num, sig in enumerate(phi):

        sig_prev = 0
        omega_size = 1
        idx = np.zeros(sum_m2.shape, dtype=np.bool)

        for n in range(itermax):

            if np.abs(sig - sig_prev) < eps:
                break

            s = sum_m2 / (2 * K * sig**2)
            idx = np.logical_and(lambda_minus <= s, s <= lambda_plus)
            omega = data[idx, :]

            # If no point meets the criterion, exit
            if omega.size == 0:
                omega_size = 0
                break

            sig_prev = sig

            # Numpy percentile must range in 0 to 100, hence q*100
            sig = np.percentile(omega, q * 100) / denom
            omega_size = omega.size / K

        # Remember the biggest omega array as giving the optimal
        # sigma amongst all initial estimates from phi
        if omega_size > max_length_omega:
            pos, max_length_omega = num, omega_size

        sigma[num] = sig
        mask[num] = idx

    if return_mask:
        return sigma[pos], mask[pos]

    return sigma[pos]


def estimate_sigma(arr, disable_background_masking=False):
    """Standard deviation estimation from local patches

    Parameters
    ----------
    arr : 3D or 4D ndarray
        The array to be estimated

    disable_background_masking : bool, default False
        If True, uses all voxels for the estimation, otherwise, only non-zeros
        voxels are used. Useful if the background is masked by the scanner.

    Returns
    -------
    sigma : ndarray
        standard deviation of the noise, one estimation per volume.
    """
    k = np.zeros((3, 3, 3), dtype=np.int8)

    k[0, 1, 1] = 1
    k[2, 1, 1] = 1
    k[1, 0, 1] = 1
    k[1, 2, 1] = 1
    k[1, 1, 0] = 1
    k[1, 1, 2] = 1

    if arr.ndim == 3:
        sigma = np.zeros(1, dtype=np.float32)
        arr = arr[..., None]
    elif arr.ndim == 4:
        sigma = np.zeros(arr.shape[-1], dtype=np.float32)
    else:
        raise ValueError("Array shape is not supported!", arr.shape)

    if disable_background_masking:
        mask = arr[..., 0].astype(np.bool)
    else:
        mask = np.ones_like(arr[..., 0], dtype=np.bool)

    conv_out = np.zeros(arr[..., 0].shape, dtype=np.float64)

    for i in range(sigma.size):
        convolve(arr[..., i], k, output=conv_out)
        mean_block = np.sqrt(6/7) * (arr[..., i] - 1/6 * conv_out)
        sigma[i] = np.sqrt(np.mean(mean_block[mask]**2))

    return sigma
