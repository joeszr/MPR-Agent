"""check_SEM_FR1 —— FR1 频谱发射模板(SEM)检测（check_SEM_FR1.m 的 Python 版）。

按 CBW 分成 3 / 5 / 7~45 / 50~100 MHz 四个分支，每段交给
check_region_avg_left / check_region_avg_right 做滑窗判决。

原 .m 的 ``check_SEM_FR1.m`` 文件末尾还带了 ``check_SEM_FR2`` 和
``check_SEM_FR2_EESS`` 两个 local function；MATLAB 从外部调用时用的是独立文件，
这里同样只保留独立文件（check_SEM_FR2.py / check_SEM_FR2_EESS.py）。

分段判决的短路逻辑原样保留（工程说明文档 6.5.2 节指出的问题）：``violation``
只会被置 1、从不置 0，所以除第一段外，其余各段的超标都会被静默忽略。改掉它会改变
结果，因此保持与 .m 一致。
"""

from __future__ import annotations

import numpy as np

from matlab_builtins import round_

from check_region_avg_left import check_region_avg_left
from check_region_avg_right import check_region_avg_right


def check_SEM_FR1(psd1, CBW, FFT_factor, bins_per_1MHz):
    """``check_SEM_FR1.m`` – FR1 spectrum emission mask.

    Reproduces the original block structure verbatim, including the short-circuit
    quirk described in section 6.5.2 of the project documentation: every block
    after the first one is only *entered* while ``violation`` is already 1, and
    ``violation`` is never cleared, so only the first segment of each template can
    turn the verdict into a failure.  That is the behaviour of the MATLAB code and
    is kept so results stay comparable.
    """
    psd1 = np.asarray(psd1).ravel()
    len_psd = psd1.size
    violation = 0
    semrelaxation = 0

    if CBW == 3:
        # left 0..1 MHz, limit -13, MBW = 1% CBW
        start_idx = int(np.floor(len_psd / 2 - CBW * 0.5 * bins_per_1MHz))
        region_bins = int(np.floor(1 * bins_per_1MHz))
        meas_bw_bins = max(1, int(round_((0.01 * CBW) * bins_per_1MHz)))
        step_bins = max(1, int(round_(meas_bw_bins / 5)))
        limit_dBm = semrelaxation - 13
        if check_region_avg_left(psd1, start_idx, region_bins, meas_bw_bins,
                                 step_bins, limit_dBm, FFT_factor):
            violation = 1

        if violation:
            start_idx = int(np.floor(len_psd / 2 - (CBW * 0.5 + 1) * bins_per_1MHz))
            region_bins = int(np.floor(4 * bins_per_1MHz))
            meas_bw_bins = max(1, int(round_(1.0 * bins_per_1MHz)))
            step_bins = max(1, int(round_(meas_bw_bins / 5)))
            limit_dBm = semrelaxation - 10
            if check_region_avg_left(psd1, start_idx, region_bins, meas_bw_bins,
                                     step_bins, limit_dBm, FFT_factor):
                violation = 1

        if violation:
            start_idx = int(np.floor(len_psd / 2 - (CBW * 0.5 + 5) * bins_per_1MHz))
            region_bins = int(np.floor(1 * bins_per_1MHz))
            meas_bw_bins = max(1, int(round_(1.0 * bins_per_1MHz)))
            step_bins = max(1, int(round_(meas_bw_bins / 5)))
            limit_dBm = semrelaxation - 25
            if check_region_avg_left(psd1, start_idx, region_bins, meas_bw_bins,
                                     step_bins, limit_dBm, FFT_factor):
                violation = 1

        if violation:
            start_idx = int(np.floor(len_psd / 2 + (CBW * 0.5) * bins_per_1MHz))
            region_bins = int(np.floor(1 * bins_per_1MHz))
            meas_bw_bins = max(1, int(round_((0.01 * CBW) * bins_per_1MHz)))
            step_bins = max(1, int(round_(meas_bw_bins / 5)))
            limit_dBm = semrelaxation - 13
            if check_region_avg_right(psd1, start_idx, region_bins, meas_bw_bins,
                                      step_bins, limit_dBm, FFT_factor):
                violation = 1

        if violation:
            start_idx = int(np.floor(len_psd / 2 + (CBW * 0.5 + 1) * bins_per_1MHz))
            region_bins = int(np.floor(4 * bins_per_1MHz))
            meas_bw_bins = max(1, int(round_(1.0 * bins_per_1MHz)))
            step_bins = max(1, int(round_(meas_bw_bins / 5)))
            limit_dBm = semrelaxation - 10
            if check_region_avg_right(psd1, start_idx, region_bins, meas_bw_bins,
                                      step_bins, limit_dBm, FFT_factor):
                violation = 1

        if violation:
            start_idx = int(np.floor(len_psd / 2 + (CBW * 0.5 + 5) * bins_per_1MHz))
            region_bins = int(np.floor(1 * bins_per_1MHz))
            meas_bw_bins = max(1, int(round_(1.0 * bins_per_1MHz)))
            step_bins = max(1, int(round_(meas_bw_bins / 5)))
            limit_dBm = semrelaxation - 25
            if check_region_avg_right(psd1, start_idx, region_bins, meas_bw_bins,
                                      step_bins, limit_dBm, FFT_factor):
                violation = 1

    elif CBW == 5:
        start_idx = int(np.floor(len_psd / 2 - (CBW * 0.5) * bins_per_1MHz))
        region_bins = int(np.floor(1 * bins_per_1MHz))
        meas_bw_bins = max(1, int(round_((0.01 * CBW) * bins_per_1MHz)))
        step_bins = max(1, int(round_(meas_bw_bins / 5)))
        limit_dBm = semrelaxation - 13
        if check_region_avg_left(psd1, start_idx, region_bins, meas_bw_bins,
                                 step_bins, limit_dBm, FFT_factor):
            violation = 1

        if violation:
            start_idx = int(np.floor(len_psd / 2 - (CBW * 0.5 + 1) * bins_per_1MHz))
            region_bins = int(np.floor(4 * bins_per_1MHz))
            meas_bw_bins = max(1, int(round_(1.0 * bins_per_1MHz)))
            step_bins = max(1, int(round_(meas_bw_bins / 5)))
            limit_dBm = semrelaxation - 10
            if check_region_avg_left(psd1, start_idx, region_bins, meas_bw_bins,
                                     step_bins, limit_dBm, FFT_factor):
                violation = 1

        if violation:
            start_idx = int(np.floor(len_psd / 2 - (CBW * 0.5 + 5) * bins_per_1MHz))
            region_bins = int(np.floor(1 * bins_per_1MHz))
            meas_bw_bins = max(1, int(round_(1.0 * bins_per_1MHz)))
            step_bins = max(1, int(round_(meas_bw_bins / 5)))
            limit_dBm = semrelaxation - 13
            if check_region_avg_left(psd1, start_idx, region_bins, meas_bw_bins,
                                     step_bins, limit_dBm, FFT_factor):
                violation = 1

        if violation:
            start_idx = int(np.floor(len_psd / 2 - (CBW * 0.5 + 6) * bins_per_1MHz))
            region_bins = int(np.floor((10 - 6) * bins_per_1MHz))
            meas_bw_bins = max(1, int(round_(1.0 * bins_per_1MHz)))
            step_bins = max(1, int(round_(meas_bw_bins / 5)))
            limit_dBm = semrelaxation - 25
            if check_region_avg_left(psd1, start_idx, region_bins, meas_bw_bins,
                                     step_bins, limit_dBm, FFT_factor):
                violation = 1

        if violation:
            start_idx = int(np.floor(len_psd / 2 + (CBW * 0.5) * bins_per_1MHz))
            region_bins = int(np.floor(1 * bins_per_1MHz))
            meas_bw_bins = max(1, int(round_((0.01 * CBW) * bins_per_1MHz)))
            step_bins = max(1, int(round_(meas_bw_bins / 5)))
            limit_dBm = semrelaxation - 13
            if check_region_avg_right(psd1, start_idx, region_bins, meas_bw_bins,
                                      step_bins, limit_dBm, FFT_factor):
                violation = 1

        if violation:
            start_idx = int(np.floor(len_psd / 2 + (CBW * 0.5 + 1) * bins_per_1MHz))
            region_bins = int(np.floor(4 * bins_per_1MHz))
            meas_bw_bins = max(1, int(round_(1.0 * bins_per_1MHz)))
            step_bins = max(1, int(round_(meas_bw_bins / 5)))
            limit_dBm = semrelaxation - 10
            if check_region_avg_right(psd1, start_idx, region_bins, meas_bw_bins,
                                      step_bins, limit_dBm, FFT_factor):
                violation = 1

        if violation:
            start_idx = int(np.floor(len_psd / 2 + (CBW * 0.5 + 5) * bins_per_1MHz))
            region_bins = int(np.floor(1 * bins_per_1MHz))
            meas_bw_bins = max(1, int(round_(1.0 * bins_per_1MHz)))
            step_bins = max(1, int(round_(meas_bw_bins / 5)))
            limit_dBm = semrelaxation - 13
            if check_region_avg_right(psd1, start_idx, region_bins, meas_bw_bins,
                                      step_bins, limit_dBm, FFT_factor):
                violation = 1

        if violation:
            start_idx = int(np.floor(len_psd / 2 + (CBW * 0.5 + 6) * bins_per_1MHz))
            region_bins = int(np.floor((10 - 6) * bins_per_1MHz))
            meas_bw_bins = max(1, int(round_(1.0 * bins_per_1MHz)))
            step_bins = max(1, int(round_(meas_bw_bins / 5)))
            limit_dBm = semrelaxation - 25
            if check_region_avg_right(psd1, start_idx, region_bins, meas_bw_bins,
                                      step_bins, limit_dBm, FFT_factor):
                violation = 1

    elif 7 <= CBW <= 45:
        # left, 0..1 MHz, limit -13
        start_idx = int(np.floor(len_psd / 2 - CBW * 0.5 * bins_per_1MHz))
        region_bins = int(np.floor(1 * bins_per_1MHz))
        meas_bw_bins = max(1, int(round_((0.01 * CBW) * bins_per_1MHz)))
        step_bins = max(1, int(round_(meas_bw_bins / 5)))
        limit_dBm = - 13                       # note: semrelaxation is not applied
        if check_region_avg_left(psd1, start_idx, region_bins, meas_bw_bins,
                                 step_bins, limit_dBm, FFT_factor):
            violation = 1

        if violation:
            start_idx = int(np.floor(len_psd / 2 - (CBW * 0.5 + 1) * bins_per_1MHz))
            region_bins = int(np.floor(4 * bins_per_1MHz))
            meas_bw_bins = max(1, int(round_(1.0 * bins_per_1MHz)))
            step_bins = max(1, int(round_(meas_bw_bins / 5)))
            limit_dBm = semrelaxation - 10
            if check_region_avg_left(psd1, start_idx, region_bins, meas_bw_bins,
                                     step_bins, limit_dBm, FFT_factor):
                violation = 1

        if violation:
            start_idx = int(np.floor(len_psd / 2 - (CBW * 0.5 + 5) * bins_per_1MHz))
            region_bins = int(np.floor((CBW - 5) * bins_per_1MHz))
            meas_bw_bins = max(1, int(round_(1.0 * bins_per_1MHz)))
            step_bins = max(1, int(round_(meas_bw_bins / 5)))
            limit_dBm = semrelaxation - 13
            if check_region_avg_left(psd1, start_idx, region_bins, meas_bw_bins,
                                     step_bins, limit_dBm, FFT_factor):
                violation = 1

        if violation:
            start_idx = int(np.floor(len_psd / 2 - (CBW * 1.5 * bins_per_1MHz)))
            region_bins = int(np.floor(5 * bins_per_1MHz))
            meas_bw_bins = max(1, int(round_(1.0 * bins_per_1MHz)))
            step_bins = max(1, int(round_(meas_bw_bins / 5)))
            limit_dBm = semrelaxation - 25
            if check_region_avg_left(psd1, start_idx, region_bins, meas_bw_bins,
                                     step_bins, limit_dBm, FFT_factor):
                violation = 1

        if violation:
            start_idx = int(np.floor(len_psd / 2 + (CBW * 0.5) * bins_per_1MHz))
            region_bins = int(np.floor(1 * bins_per_1MHz))
            meas_bw_bins = max(1, int(round_((0.01 * CBW) * bins_per_1MHz)))
            step_bins = max(1, int(round_(meas_bw_bins / 5)))
            limit_dBm = semrelaxation - 13
            if check_region_avg_right(psd1, start_idx, region_bins, meas_bw_bins,
                                      step_bins, limit_dBm, FFT_factor):
                violation = 1

        if violation:
            start_idx = int(np.floor(len_psd / 2 + (CBW * 0.5 + 1) * bins_per_1MHz))
            region_bins = int(np.floor(4 * bins_per_1MHz))
            meas_bw_bins = max(1, int(round_(1.0 * bins_per_1MHz)))
            step_bins = max(1, int(round_(meas_bw_bins / 5)))
            limit_dBm = semrelaxation - 10
            if check_region_avg_right(psd1, start_idx, region_bins, meas_bw_bins,
                                      step_bins, limit_dBm, FFT_factor):
                violation = 1

        if violation:
            start_idx = int(np.floor(len_psd / 2 + (CBW * 0.5 + 5) * bins_per_1MHz))
            region_bins = int(np.floor((CBW - 5) * bins_per_1MHz))
            meas_bw_bins = max(1, int(round_(1.0 * bins_per_1MHz)))
            step_bins = max(1, int(round_(meas_bw_bins / 5)))
            limit_dBm = semrelaxation - 13
            if check_region_avg_right(psd1, start_idx, region_bins, meas_bw_bins,
                                      step_bins, limit_dBm, FFT_factor):
                violation = 1

        if violation:
            start_idx = int(np.floor(len_psd / 2 + CBW * 1.5 * bins_per_1MHz))
            region_bins = int(np.floor(5 * bins_per_1MHz))
            meas_bw_bins = max(1, int(round_(1.0 * bins_per_1MHz)))
            step_bins = max(1, int(round_(meas_bw_bins / 5)))
            limit_dBm = semrelaxation - 25
            if check_region_avg_right(psd1, start_idx, region_bins, meas_bw_bins,
                                      step_bins, limit_dBm, FFT_factor):
                violation = 1

    elif 50 <= CBW <= 100:
        # left, 0..1 MHz, limit -24, MBW = 30 kHz
        start_idx = int(np.floor(len_psd / 2 - CBW * 0.5 * bins_per_1MHz))
        region_bins = int(np.floor(1 * bins_per_1MHz))
        meas_bw_bins = max(1, int(round_(0.03 * bins_per_1MHz)))
        step_bins = max(1, int(round_(meas_bw_bins / 5)))
        limit_dBm = semrelaxation - 24
        if check_region_avg_left(psd1, start_idx, region_bins, meas_bw_bins,
                                 step_bins, limit_dBm, FFT_factor):
            violation = 1

        if violation:
            start_idx = int(np.floor(len_psd / 2 - (CBW * 0.5 + 1) * bins_per_1MHz))
            region_bins = int(np.floor(4 * bins_per_1MHz))
            meas_bw_bins = max(1, int(round_(1.0 * bins_per_1MHz)))
            step_bins = max(1, int(round_(meas_bw_bins / 5)))
            limit_dBm = semrelaxation - 10
            if check_region_avg_left(psd1, start_idx, region_bins, meas_bw_bins,
                                     step_bins, limit_dBm, FFT_factor):
                violation = 1

        if violation:
            start_idx = int(np.floor(len_psd / 2 - (CBW * 0.5 + 5) * bins_per_1MHz))
            region_bins = int(np.floor((CBW - 5) * bins_per_1MHz))
            meas_bw_bins = max(1, int(round_(1.0 * bins_per_1MHz)))
            step_bins = max(1, int(round_(meas_bw_bins / 5)))
            limit_dBm = semrelaxation - 13
            if check_region_avg_left(psd1, start_idx, region_bins, meas_bw_bins,
                                     step_bins, limit_dBm, FFT_factor):
                violation = 1

        if violation:
            start_idx = int(np.floor(len_psd / 2 - (CBW * 1.5) * bins_per_1MHz))
            region_bins = int(np.floor(5 * bins_per_1MHz))
            meas_bw_bins = max(1, int(round_(1.0 * bins_per_1MHz)))
            step_bins = max(1, int(round_(meas_bw_bins / 5)))
            limit_dBm = semrelaxation - 25
            if check_region_avg_left(psd1, start_idx, region_bins, meas_bw_bins,
                                     step_bins, limit_dBm, FFT_factor):
                violation = 1

        if violation:
            start_idx = int(np.floor(len_psd / 2 + (CBW * 0.5) * bins_per_1MHz))
            region_bins = int(np.floor(1 * bins_per_1MHz))
            meas_bw_bins = max(1, int(round_(0.03 * bins_per_1MHz)))
            step_bins = max(1, int(round_(meas_bw_bins / 5)))
            limit_dBm = semrelaxation - 24
            if check_region_avg_right(psd1, start_idx, region_bins, meas_bw_bins,
                                      step_bins, limit_dBm, FFT_factor):
                violation = 1

        if violation:
            start_idx = int(np.floor(len_psd / 2 + (CBW * 0.5 + 1) * bins_per_1MHz))
            region_bins = int(np.floor(4 * bins_per_1MHz))
            meas_bw_bins = max(1, int(round_(1.0 * bins_per_1MHz)))
            step_bins = max(1, int(round_(meas_bw_bins / 5)))
            limit_dBm = semrelaxation - 10
            if check_region_avg_right(psd1, start_idx, region_bins, meas_bw_bins,
                                      step_bins, limit_dBm, FFT_factor):
                violation = 1

        if violation:
            start_idx = int(np.floor(len_psd / 2 + (CBW * 0.5 + 5) * bins_per_1MHz))
            region_bins = int(np.floor((CBW - 5) * bins_per_1MHz))
            meas_bw_bins = max(1, int(round_(1.0 * bins_per_1MHz)))
            step_bins = max(1, int(round_(meas_bw_bins / 5)))
            limit_dBm = semrelaxation - 13
            if check_region_avg_right(psd1, start_idx, region_bins, meas_bw_bins,
                                      step_bins, limit_dBm, FFT_factor):
                violation = 1

        if violation:
            start_idx = int(np.floor(len_psd / 2 + (CBW * 1.5) * bins_per_1MHz))
            region_bins = int(np.floor(5 * bins_per_1MHz))
            meas_bw_bins = max(1, int(round_(1.0 * bins_per_1MHz)))
            step_bins = max(1, int(round_(meas_bw_bins / 5)))
            limit_dBm = semrelaxation - 25
            if check_region_avg_right(psd1, start_idx, region_bins, meas_bw_bins,
                                      step_bins, limit_dBm, FFT_factor):
                violation = 1

    else:
        raise ValueError(f"Unsupported CBW = {CBW} MHz")

    return 1 if violation else 0
