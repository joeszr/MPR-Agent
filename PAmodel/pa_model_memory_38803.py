"""pa_model_memory_38803 —— 广义记忆多项式（GMP）模型，2 GHz GaAs（pa_model_memory_38803.m 的 Python 版）。

    y[n] = sum_l polyval(a_l, |x[n-l]|^2) * x[n-l]
         + sum_(l,m) polyval(b_lm, |x[n-m]|^2) * x[n-l]

对角项时延 La = [-2..2]，交叉项 (Lb, Mb) = ([-1 1], [0 0])。

注意：原 .m 文件的最后一个 local function ``shift_signal`` 缺少结尾的 ``end``，
MATLAB 无法解析该文件（不是本移植引入的问题）。这里按函数体意图补全——
缺失的那个 ``end`` 就是闭合 shift_signal 的。
"""

from __future__ import annotations

import numpy as np

from matlab_builtins import polyval

# ------------------------- 对角项系数 -------------------------
A_L_NEG2 = np.array([0.0913878 + 0.029207j, -0.205695 - 0.0047561j,
                     0.436792 + 0.098933j, -0.0447736 + 0.802472j,
                     -1.91069 - 3.64271j, 3.53201 + 6.10853j,
                     -2.64467 - 4.81807j, 0.741402 + 1.46945j])
A_L_NEG1 = np.array([-0.109009 - 0.0382752j, 1.34619 - 0.303139j,
                     -7.57533 + 2.07457j, 30.8214 - 7.83883j,
                     -71.9119 + 13.7515j, 94.7172 - 10.8742j,
                     -65.1891 + 3.05573j, 18.1882 + 0.14561j])
A_L_0 = np.array([-0.369392 - 0.616894j, 0.582141 - 1.54129j,
                  -4.2332 + 13.9746j, 15.4346 - 56.4738j,
                  -34.026 + 106.817j, 42.3779 - 83.2642j,
                  -26.6004 + 5.86237j, 6.4982 + 15.2082j])
A_L_POS1 = np.array([-0.0730384 - 0.0608598j, 0.316437 - 0.130488j,
                     -2.64289 + 1.95766j, 13.9617 - 8.92706j,
                     -35.9884 + 25.271j, 49.5323 - 38.9777j,
                     -34.8388 + 30.1032j, 9.83576 - 9.12289j])
A_L_POS2 = np.array([0.0145707 + 0.00223568j, 0.0166021 + 0.0884597j,
                     -0.170987 - 0.889998j, 0.398012 + 4.25717j,
                     -0.922915 - 11.5296j, 1.51648 + 16.8822j,
                     -1.31708 - 12.4992j, 0.443603 + 3.66282j])

# ------------------------- 交叉项系数（m = 0） -------------------------
B_L_NEG1_M0 = np.array([-0.108885 - 0.0392921j, -0.65351 - 0.122316j,
                        2.7747 + 3.26333j, -6.41902 - 23.391j,
                        9.68476 + 79.745j, -10.5191 - 141.613j,
                        6.89414 + 125.231j, -1.92908 - 43.441j])
B_L_POS1_M0 = np.array([-0.0732748 - 0.0617029j, 1.04861 + 0.216692j,
                        -7.53774 - 2.85579j, 29.348 + 11.8762j,
                        -68.0727 - 19.8783j, 92.0079 + 4.93057j,
                        -66.4247 + 17.5978j, 19.6384 - 12.2782j])

LA = [-2, -1, 0, 1, 2]
# flipud([...])：最高次在前，每一列对应一个时延
P_AM = np.flipud(np.column_stack([A_L_NEG2, A_L_NEG1, A_L_0, A_L_POS1, A_L_POS2]))

LB = [-1, 1]
MB = [0, 0]
P_BM = np.flipud(np.column_stack([B_L_NEG1_M0, B_L_POS1_M0]))


def shift_signal(x, d):
    """``xs = shift_signal(x, d)``：x(n-d)，越界补零。

    d > 0 表示延迟，d < 0 表示超前，d = 0 原样返回。
    """
    x = np.asarray(x)
    xs = np.zeros(x.shape, dtype=complex)
    n = x.size
    xf = x.ravel()
    of = xs.ravel()
    if d == 0:
        return x.astype(complex)
    if d > 0:
        if d < n:
            of[d:] = xf[:n - d]
    else:
        a = -d
        if a < n:
            of[:n - a] = xf[a:]
    return of.reshape(x.shape)


def pa_model_memory_38803(x):
    """``y = pa_model_memory_38803(x)``。"""
    x = np.asarray(x).astype(complex)
    y = np.zeros(x.shape, dtype=complex)

    # ---------------- 对角项 ----------------
    for idx, l in enumerate(LA):
        x_shift = shift_signal(x, l)
        abs_sq = np.abs(x_shift) ** 2
        term = polyval(P_AM[:, idx], abs_sq)
        y = y + term * x_shift

    # ---------------- 交叉项 ----------------
    for idx, (l, m) in enumerate(zip(LB, MB)):
        x_shift_l = shift_signal(x, l)
        x_shift_m = shift_signal(x, m)
        abs_sq = np.abs(x_shift_m) ** 2
        term = polyval(P_BM[:, idx], abs_sq)
        y = y + term * x_shift_l

    return y
