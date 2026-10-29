"""check_region_avg_right —— SEM 右侧频段区间平均功率检测（check_region_avg_right.m 的 Python 版）。

与左侧版本完全对称，只是滑动方向相反。返回 1 表示通过。
"""

from __future__ import annotations

import numpy as np

from matlab_builtins import log10


def check_region_avg_right(psd1, start_idx, region_bins, avg_bins, step_bins,
                           limit_dBm, FFT_factor):
    """``check_region_avg_right.m`` – sliding-window power check, sliding right."""
    psd1 = np.asarray(psd1).ravel()
    end_idx = start_idx + region_bins - 1

    if start_idx + avg_bins - 1 > end_idx:
        return 1

    n = (end_idx - (start_idx + avg_bins - 1)) // step_bins + 1
    cur = start_idx + step_bins * np.arange(n)
    csum = np.concatenate(([0.0], np.cumsum(psd1)))
    sums = csum[cur + avg_bins - 1] - csum[cur - 1]  # psd1(cur:cur+avg-1)

    worst = np.max(sums) * FFT_factor
    return 1 if 10 * log10(worst) <= limit_dBm else 0


# ----------------------------------------------------------------------------
# SEM templates
# ----------------------------------------------------------------------------
