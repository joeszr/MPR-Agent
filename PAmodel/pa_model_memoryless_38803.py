"""pa_model_memoryless_38803 —— 28 GHz GaN 无记忆多项式模型（pa_model_memoryless_38803.m 的 Python 版）。

原 .m 文件里的函数名也叫 ``pa_model_memoryless``（与 pa_model_memoryless.m 撞名，
MATLAB 靠文件名区分）。这里保持文件名为 38803 版本，函数名沿用原 .m 的
``pa_model_memoryless``，与 MATLAB 的调用方式一致。
"""

from __future__ import annotations

import numpy as np

from matlab_builtins import polyval

# 系数按幂次从高到低（polyval 顺序）
P_AM = np.array([
    1.54271 - 2.94034j,
    -4.41452 + 8.63164j,
    4.81548 - 9.54837j,
    -2.58056 + 4.81215j,
    0.89015 - 0.72633j,
    -0.334697 - 0.942326j,
])


def pa_model_memoryless(x):
    """``y = pa_model_memoryless(x)``，多项式作用于 |x|^2。"""
    x = np.asarray(x)
    abs_x = np.abs(x) ** 2
    term = polyval(P_AM, abs_x)
    return term * x
