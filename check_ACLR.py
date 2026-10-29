"""check_ACLR —— 邻道泄漏比(ACLR)检测（check_ACLR.m 的 Python 版）。

测量带宽 MBW = REF_SCS*(12*NRB+1)/1000，主信道与左右邻道各积分一个 MBW，
两端都要达到 ``ACLR_spec`` 才算通过。
"""

from __future__ import annotations

import numpy as np

from matlab_builtins import log10


def check_ACLR(orgin_aver_power, CBW, REF_SCS, NRB, ACLR_spec, FFT_factor,
               bins_per_1MHz):
    """``check_ACLR.m`` – adjacent channel leakage ratio, returns 1 (pass) / 0."""
    psd = np.asarray(orgin_aver_power).ravel()
    len_psd = psd.size

    MBW = REF_SCS * (12 * NRB + 1) / 1000        # NR ACLR measurement bandwidth

    # main channel power
    k1 = int(np.floor(len_psd / 2 - (MBW / 2 * bins_per_1MHz)))
    i1 = int(np.floor(MBW * bins_per_1MHz))
    mainpower = np.sum(psd[k1:k1 + i1]) * FFT_factor
    main = 10 * log10(mainpower)

    # lower adjacent channel
    k2 = int(np.floor(len_psd / 2 - ((MBW / 2 + CBW) * bins_per_1MHz)))
    i2 = int(np.floor(MBW * bins_per_1MHz))
    aclrpower1 = np.sum(psd[k2:k2 + i2]) * FFT_factor
    aclr1 = 10 * log10(aclrpower1)

    # upper adjacent channel
    k3 = int(np.floor(len_psd / 2 + ((-MBW / 2 + CBW) * bins_per_1MHz)))
    i3 = int(np.floor(MBW * bins_per_1MHz))
    aclrpower2 = np.sum(psd[k3:k3 + i3]) * FFT_factor
    aclr2 = 10 * log10(aclrpower2)

    aclrright = main - aclr2
    aclrleft = main - aclr1

    return 1 if (aclrright >= ACLR_spec and aclrleft >= ACLR_spec) else 0


# ----------------------------------------------------------------------------
# SEM primitives
# ----------------------------------------------------------------------------
