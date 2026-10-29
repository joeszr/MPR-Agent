"""HZW_HB_pm —— HZW 高频段功放的 AM/PM 多项式拟合（HZW_HB_pm.m 的 Python 版）。

输入未归一化的复基带信号幅度（线性），输出相位偏移（弧度，不是度）。
"""

from __future__ import annotations

import numpy as np

from matlab_builtins import polyval

# 系数：从高次项到低次项 (x^8 ... x^0)
P_PM = np.array([-3.892470097856681,
                 3.255755110677330,
                 17.584338005626430,
                 -36.556848195328900,
                 28.150837417511450,
                 -10.089193164937422,
                 1.596851134816818,
                 -0.068348097866659,
                 1.999751611906609])

# PA 拟合时保存的归一化参数
R_SCALE = 3.162277660168380


def HZW_HB_pm(x_linear):
    """``y = HZW_HB_pm(x_linear)``，结果是相位偏移（rad）。"""
    x_norm = np.asarray(x_linear) / R_SCALE       # 输入归一化
    return polyval(P_PM, x_norm)
