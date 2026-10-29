"""check_region_avg_left —— SEM 左侧频段区间平均功率检测（check_region_avg_left.m 的 Python 版）。

从靠近信道中心的一侧开始，每次取 ``avg_bins`` 个频点求和，转成 dBm 与限值比较，
超了立即返回 0。返回 1 表示通过。``start_idx`` 是 1 基下标。

原 .m 是 while 循环，遇到第一个超标窗就返回；这里用累加和一次算出所有窗口，
取最大者比较——判定结果完全相同，全量扫描时快很多。
"""

from __future__ import annotations

import numpy as np

from matlab_builtins import log10


def check_region_avg_left(psd1, start_idx, region_bins, avg_bins, step_bins,
                          limit_dBm, FFT_factor):
    """``check_region_avg_left.m`` – sliding-window power check, sliding left.

    Returns 1 when every window stays below ``limit_dBm`` (pass), 0 on violation.
    ``start_idx`` is 1-based.

    The original is a ``while`` loop that sums ``avg_bins`` bins and stops at the
    first window above the limit.  Comparing the largest window sum instead gives
    exactly the same verdict, so the loop is evaluated with a cumulative sum here;
    on a full sweep that is the difference between minutes and hours.
    """
    psd1 = np.asarray(psd1).ravel()
    end_idx = start_idx - region_bins + 1

    if start_idx - avg_bins + 1 < end_idx:
        return 1                                    # empty region: nothing to check

    n = (start_idx - avg_bins + 1 - end_idx) // step_bins + 1
    cur = start_idx - step_bins * np.arange(n)
    csum = np.concatenate(([0.0], np.cumsum(psd1)))
    sums = csum[cur] - csum[cur - avg_bins]          # psd1(cur-avg+1:cur)

    worst = np.max(sums) * FFT_factor
    return 1 if 10 * log10(worst) <= limit_dBm else 0
