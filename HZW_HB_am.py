"""HZW_HB_am —— HZW 高频段功放的 AM/AM 多项式拟合（HZW_HB_am.m 的 Python 版）。

输入未归一化的复基带信号幅度（线性），输出幅度。
"""

from __future__ import annotations

import numpy as np

from matlab_builtins import polyval

# 系数：从高次项到低次项 (x^7 ... x^0)
P_AM = np.array([2.357466129209464e+03, -8.901337224131486e+03,
                 1.300533982360734e+04, -9.044800642711152e+03,
                 2.935432027031904e+03, -4.321630819328964e+02,
                 1.209577235215943e+02, -0.341191539644442])

# PA 拟合时保存的归一化参数
R_SCALE = 3.162277660168380


def HZW_HB_am(x_linear):
    """``y = HZW_HB_am(x_linear)``。"""
    x_norm = np.asarray(x_linear) / R_SCALE       # 输入归一化
    return polyval(P_AM, x_norm)
