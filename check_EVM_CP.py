"""check_EVM_CP —— CP-OFDM 误差矢量幅度(EVM)检测（check_EVM_CP.m 的 Python 版）。

算法与原 .m 完全一致，包括两处需要在维护时留意的地方（见工程说明文档 6.2 节）：

    * 噪声功率算出来了但没有加进信号，``SNR`` 实际上不起作用；
    * 逐子载波的 LS 估计最终被 ``H_LSnn = ones(size(bit_modedn))*mean(H_LSnn)``
      压成一个复标量，上面那段插值只贡献它的均值。
"""

from __future__ import annotations

import numpy as np

from matlab_builtins import comm_evm, fftshift, interp1, reshape_F


def _col(x):
    """确保是 (N,1) 列向量。"""
    a = np.asarray(x)
    return a.reshape(-1, 1) if a.ndim == 1 else a


def check_EVM_CP(output, CP_length, ifft_length, carrier_position, scs, scs_step,
                 carrier_count, lcrb, bit_modedn, SNR, EVMLevel):
    """``check_EVM_CP.m`` – CP-OFDM RMS EVM check, returns 1 (pass) / 0 (fail).

    Notes carried over from the original on purpose:

    * the noise term is computed and then never added, so ``SNR`` has no effect;
    * the per-subcarrier LS estimate is collapsed to a single complex scalar by
      ``H_LSnn = ones(size(bit_modedn))*mean(H_LSnn)``, so the interpolation above
      it only contributes its mean.
    """
    output = _col(output)
    bit_modedn = _col(bit_modedn)

    var_output = np.var(output.ravel(), ddof=1)
    _snr_linear = 10 ** (SNR / 10)
    _noise_power = var_output / _snr_linear

    Rx_data_sig = output[CP_length:, :]                      # delete the CP
    sigout = np.fft.fft(Rx_data_sig, axis=0) / ifft_length
    sigout = fftshift(sigout, 0)

    # --- extract the occupied subcarriers ---
    sigout1 = sigout[np.asarray(carrier_position) - 1, :]
    sigout11 = reshape_F(sigout1, (scs_step, carrier_count))
    sigout2 = sigout11[0, :]
    sigout3 = sigout2 / np.max(np.abs(sigout2))
    sigout3 = sigout3.reshape(carrier_count, 1)              # .'
    sigout6 = sigout3
    sigout8 = sigout6 / np.max(np.abs(sigout6))

    bit_modedn1 = reshape_F(bit_modedn, (6, 2 * lcrb))
    sigout88 = reshape_F(sigout8, (6, 2 * lcrb))

    bit_moded_SR = bit_modedn1[0, :]
    sigout_SR = sigout88[0, :]
    H_LS = bit_moded_SR / sigout_SR

    x = np.arange(0, carrier_count - 5, 6)                   # 1:6:carrier_count-5
    x1 = np.arange(carrier_count)                            # 1:carrier_count
    H_LSn1 = interp1(x, H_LS, x1)

    bit_moded_SR1 = bit_modedn1[5, :]
    sigout_SR1 = sigout88[5, :]
    H_LS1 = bit_moded_SR1 / sigout_SR1

    x2 = np.arange(5, carrier_count, 6)                      # 6:6:carrier_count
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
    H_LSnn = H_LSn

    H_LSnn = np.ones(bit_modedn.shape, dtype=complex) * np.mean(H_LSnn)

    sigout10 = H_LSnn * sigout8                              # equalisation

    rmsEVM = comm_evm(bit_modedn, sigout10)
    return 1 if rmsEVM < EVMLevel else 0
