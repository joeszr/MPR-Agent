"""pa_GaAs_2GHz —— 无记忆 2 GHz GaAs 多项式模型（pa_GaAs_2GHz.m 的 Python 版）。

    y = x * sum_{k=0}^{7} a_k * |x|^(2k)

输入是归一化复基带信号，|x| <= 1。
"""

from __future__ import annotations

import numpy as np

# 系数 a_k，k = 0..7
A = np.array([-0.618347 - 0.785905j, 2.0831 - 1.69506j,
              -14.7229 + 16.8335j, 61.6423 - 76.9171j,
              -145.139 + 184.765j, 190.61 - 239.371j,
              -130.184 + 158.957j, 36.0047 - 42.5192j])


def pa_GaAs_2GHz(x):
    """``y = pa_GaAs_2GHz(x)``。"""
    a = np.asarray(x).reshape(-1, 1)
    z = np.abs(a) ** 2

    # 原 .m 的 Horner 循环等价于 polyval(flipud(A), z)
    p = np.polyval(A[::-1], z)
    return a * p
