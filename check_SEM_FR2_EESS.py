"""check_SEM_FR2_EESS —— FR2 EESS 频谱发射模板(SEM)检测（check_SEM_FR2_EESS.m 的 Python 版）。

FR2 的 EESS 变体，限值常量 -13/-13/-5/-13，区域宽度用 ceil 而不是 floor。
"""

from __future__ import annotations

import numpy as np

from matlab_builtins import round_

from check_region_avg_left import check_region_avg_left
from check_region_avg_right import check_region_avg_right


def check_SEM_FR2_EESS(psd1, CBW, FFT_factor, bins_per_1MHz):
    """``check_SEM_FR2_EESS.m`` – FR2 EESS variant of the emission mask."""
    psd1 = np.asarray(psd1).ravel()

    SEM_limit_frequency1 = -13
    SEM_limit_frequency2 = -13
    SEM_limit_frequency3 = -5
    SEM_limit_frequency4 = -13
    SEM_limit_additional = 0

    len_psd = psd1.size
    violation = 0

    start_idx = int(np.floor(len_psd / 2 - (CBW * (0.5)) * bins_per_1MHz))
    region_bins = int(np.ceil((CBW * 0.1) * bins_per_1MHz))
    meas_bw_bins = max(1, int(round_(1.0 * bins_per_1MHz)))
    step_bins = max(1, int(round_(meas_bw_bins / 5)))
    limit_dBm = SEM_limit_frequency1
    if check_region_avg_left(psd1, start_idx, region_bins, meas_bw_bins, step_bins,
                             limit_dBm, FFT_factor):
        violation = 1

    if violation:
        start_idx = int(np.floor(len_psd / 2 - (CBW * (0.5 + 0.1)) * bins_per_1MHz))
        region_bins = int(np.ceil((CBW * (2 - 0.1)) * bins_per_1MHz))
        meas_bw_bins = max(1, int(round_(1.0 * bins_per_1MHz)))
        step_bins = max(1, int(round_(meas_bw_bins / 5)))
        limit_dBm = SEM_limit_frequency2
        if check_region_avg_left(psd1, start_idx, region_bins, meas_bw_bins,
                                 step_bins, limit_dBm, FFT_factor):
            violation = 1

    if violation:
        start_idx = int(np.floor(len_psd / 2 + (CBW * (0.5)) * bins_per_1MHz))
        region_bins = int(np.ceil(CBW * (0.1 - 0.0) * bins_per_1MHz))
        meas_bw_bins = max(1, int(round_(1.0 * bins_per_1MHz)))
        step_bins = max(1, int(round_(meas_bw_bins / 5)))
        limit_dBm = SEM_limit_frequency3
        if check_region_avg_right(psd1, start_idx, region_bins, meas_bw_bins,
                                  step_bins, limit_dBm, FFT_factor):
            violation = 1

    if violation:
        start_idx = int(np.floor(len_psd / 2 + (CBW * (0.5 + 0.1)) * bins_per_1MHz))
        region_bins = int(np.ceil(CBW * (2 - 0.1) * bins_per_1MHz))
        meas_bw_bins = max(1, int(round_(1.0 * bins_per_1MHz)))
        step_bins = max(1, int(round_(meas_bw_bins / 5)))
        limit_dBm = SEM_limit_frequency4
        if check_region_avg_right(psd1, start_idx, region_bins, meas_bw_bins,
                                  step_bins, limit_dBm, FFT_factor):
            violation = 1

    if violation:
        start_idx = int(np.floor(len_psd / 2 - (CBW * 0.5) * bins_per_1MHz)) + 1
        region_bins = int(np.ceil(200 * bins_per_1MHz))
        meas_bw_bins = max(1, int(round_(200.0 * bins_per_1MHz)))
        step_bins = max(1, int(round_(meas_bw_bins / 5)))
        limit_dBm = SEM_limit_additional
        if check_region_avg_left(psd1, start_idx, region_bins, meas_bw_bins,
                                 step_bins, limit_dBm, FFT_factor):
            violation = 1

    return 1 if violation else 0


# ----------------------------------------------------------------------------
# IBE
# ----------------------------------------------------------------------------
