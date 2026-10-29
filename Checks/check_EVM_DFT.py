"""check_EVM_DFT —— DFT-s-OFDM 误差矢量幅度(EVM)检测（check_EVM_DFT.m 的 Python 版）。

前面几步与 CP-OFDM 版几乎一样，两处不同：

    * LS 估计用 ``bit_moded``（DFT 预编码之后的频域符号）作参考；
    * 均衡之后多一步 IDFT 解预编码，EVM 在解预编码后的星座上测量（符合 3GPP）。
"""

from __future__ import annotations

import numpy as np

from matlab_builtins import comm_evm, fftshift, interp1, reshape_F


def _col(x):
    """确保是 (N,1) 列向量。"""
    a = np.asarray(x)
    return a.reshape(-1, 1) if a.ndim == 1 else a


def check_EVM_DFT(output, CP_length, ifft_length, carrier_position, scs, scs_step,
                  carrier_count, lcrb, bit_moded, bit_modedn, SNR, EVMLevel, Msc):
    """``check_EVM_DFT.m`` – DFT-s-OFDM RMS EVM check (adds the IDFT step).

    ``bit_moded`` is the post-DFT reference used for the LS estimate, while the
    EVM itself is measured against the original QAM symbols, as 3GPP requires.
    """
    output = _col(output)
    bit_moded = _col(bit_moded)
    bit_modedn = _col(bit_modedn)

    var_output = np.var(output.ravel(), ddof=1)
    _snr_linear = 10 ** (SNR / 10)
    _noise_power = var_output / _snr_linear

    Rx_data_sig = output[CP_length:, :]
    sigout = np.fft.fft(Rx_data_sig, axis=0) / ifft_length
    sigout = fftshift(sigout, 0)

    sigout1 = sigout[np.asarray(carrier_position) - 1, :]
    sigout11 = reshape_F(sigout1, (scs_step, carrier_count))
    sigout2 = sigout11[0, :]
    sigout3 = sigout2 / np.max(np.abs(sigout2))
    sigout3 = sigout3.reshape(carrier_count, 1)              # .'
    sigout6 = sigout3
    sigout8 = sigout6 / np.max(np.abs(sigout6))

    bit_modedn1 = reshape_F(bit_moded, (6, 2 * lcrb))
    sigout88 = reshape_F(sigout8, (6, 2 * lcrb))

    bit_moded_SR = bit_modedn1[0, :]
    sigout_SR = sigout88[0, :]
    H_LS = bit_moded_SR / sigout_SR

    x = np.arange(0, carrier_count - 5, 6)
    x1 = np.arange(carrier_count)
    H_LSn1 = interp1(x, H_LS, x1)

    bit_moded_SR1 = bit_modedn1[5, :]
    sigout_SR1 = sigout88[5, :]
    H_LS1 = bit_moded_SR1 / sigout_SR1

    x2 = np.arange(5, carrier_count, 6)
    x22 = np.arange(carrier_count)
    H_LSn2 = interp1(x2, H_LS1, x22)

    H_LSn3 = (H_LSn1 + H_LSn2) / 2
    H_LSn = H_LSn3.copy()
    H_LSn[0:5] = H_LSn1[0:5]
    H_LSn[carrier_count - 1] = H_LSn2[carrier_count - 1]
    H_LSn[carrier_count - 2] = H_LSn2[carrier_count - 2]
    H_LSn[carrier_count - 3] = H_LSn2[carrier_count - 3]
    H_LSn[carrier_count - 4] = H_LSn2[carrier_count - 4]
    H_LSn[carrier_count - 5] = H_LSn2[carrier_count - 5]

    H_LSnn = np.mean(H_LSn)
    sigout10 = H_LSnn * sigout8

    # --- DFT-s-OFDM: undo the transform precoding ---
    sigout10_matrix = reshape_F(sigout10, (Msc, 1))
    sigout10_idft = np.fft.ifft(sigout10_matrix, axis=0) * np.sqrt(Msc)

    rmsEVM = comm_evm(bit_modedn, sigout10_idft)
    return 1 if rmsEVM < EVMLevel else 0
