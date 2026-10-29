"""pa_model_memoryless —— 无记忆多项式功放模型，K=9（pa_model_memoryless.m 的 Python 版）。

系数 a_k（k=1..9）对应 1,3,...,17 阶。
"""

from __future__ import annotations

import numpy as np

A = np.array([
    4.62430516e+01 - 5.02480716e+01j,
    2.59475909e+03 + 1.44281985e+02j,
    -3.93505780e+05 - 6.62910642e+04j,
    3.14355276e+07 + 9.08242329e+06j,
    -1.41867540e+09 - 6.32875998e+08j,
    3.52165692e+10 + 2.43823495e+10j,
    -4.47053276e+11 - 4.60421463e+11j,
    2.23971323e+12 + 3.27669048e+12j,
    3.90316701e+11 + 5.68696418e+11j,
])


def pa_model_memoryless(x):
    """``y = pa_model_memoryless(x)``。"""
    x = np.asarray(x)
    abs_x_sq = np.abs(x) ** 2          # |x|^2

    term = x.astype(complex)           # 第 1 项：x * |x|^0
    y = A[0] * term
    for k in range(1, A.size):
        term = term * abs_x_sq         # 每乘一次 |x|^2 升两阶
        y = y + A[k] * term
    return y
