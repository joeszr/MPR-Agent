"""pa_model_mp_K7 —— PC2 记忆多项式功放模型，M=3、K=7（pa_model_mp_K7.m 的 Python 版）。

    y[n] = sum_{m=0}^{M} sum_{k=1}^{K} a(m,k) * x[n-m] * |x[n-m]|^(2(k-1))

非线性阶次 1,3,5,7,9,11,13（K=7），记忆深度 M=3，共 28 个复系数，出自 PC2 文档。

NOTE 1: 前端 4 dB 插损已包含在模型里。
NOTE 2: 模型拟合采样率为 614.4 MHz。
NOTE 3: 模型输入在 5 dBm 处截幅（50 欧上 0.39764 V 峰值），
        最小有效输入 -30 dBm（0.0070711 V）。
"""

from __future__ import annotations

import numpy as np

# 系数：按 [a0,1; a1,1; a2,1; a3,1; a0,3; ...; a3,13] 排列（先时延后阶次）
COEFFS = np.array([
    # k=1 (1 阶)
    1.78125421e+01 + 3.96234802e+00j,
    7.75483096e+00 - 1.06941812e+01j,
    -7.72899765e+00 + 9.04484189e+00j,
    2.48795348e+00 - 2.76518830e+00j,
    # k=2 (3 阶)
    9.75722189e+01 + 9.49718204e+01j,
    -6.46736904e+01 + 1.55427298e+01j,
    2.65557457e+00 - 1.41372308e+01j,
    8.14834939e+00 + 3.68035394e+00j,
    # k=3 (5 阶)
    -4.36921775e+03 - 2.90487370e+03j,
    3.25651083e+03 - 5.88392401e+02j,
    -5.23038528e+02 + 4.58746411e+02j,
    -1.51258701e+02 - 1.40300633e+02j,
    # k=4 (7 阶)
    6.67412504e+04 + 3.62371316e+04j,
    -4.19280551e+04 + 6.06657427e+03j,
    3.95605656e+03 - 5.72662196e+03j,
    4.02914882e+03 + 1.39078164e+03j,
    # k=5 (9 阶)
    -5.42918789e+05 - 2.29695739e+05j,
    2.56101445e+05 - 3.11728454e+04j,
    9.08023985e+02 + 3.43943069e+04j,
    -4.26449208e+04 - 3.95132361e+03j,
    # k=6 (11 阶)
    2.19218318e+06 + 7.35795077e+05j,
    -7.70951908e+05 + 8.54072559e+04j,
    -8.90153246e+04 - 1.02613131e+05j,
    1.90424815e+05 - 6.66193945e+03j,
    # k=7 (13 阶)
    -3.40445900e+06 - 9.45835587e+05j,
    9.20919772e+05 - 1.00871883e+05j,
    2.14152570e+05 + 1.22085816e+05j,
    -3.07290090e+05 + 3.43617693e+04j,
])

K = 7          # 非线性项数（1,3,...,13 阶）
M = 3          # 记忆深度（时延 0..3）
VCLIP = 0.39764  # NOTE 3：5 dBm 峰值电压（50 欧）


def _as_column(x):
    """``x(:)``，并告知输入是否为 1xN 行向量。"""
    a = np.asarray(x)
    was_row = a.ndim == 2 and a.shape[0] == 1
    return a.reshape(-1, 1), was_row


def pa_model_mp_K7(x):
    """``y = pa_model_mp_K7(x)``。"""
    x = np.array(x, dtype=complex, copy=True)

    # NOTE 3：输入截幅，保持相位不变
    mag = np.abs(x)
    over = mag > VCLIP
    if np.any(over):
        x[over] = VCLIP * x[over] / mag[over]

    x_col, was_row = _as_column(x)
    N = x_col.size

    y = np.zeros((N, 1), dtype=complex)

    # 前面补 M 个零，保证因果
    x_padded = np.vstack([np.zeros((M, 1), dtype=complex), x_col])
    abs_x_sq_padded = np.abs(x_padded) ** 2

    # MATLAB 的 reshape(coeffs, M+1, K) 是列主序
    A = COEFFS.reshape((M + 1, K), order="F")

    for m in range(M + 1):
        idx = slice(M - m, M - m + N)
        x_d = x_padded[idx]
        p_d = abs_x_sq_padded[idx]

        # 递推求各阶非线性项：每次乘 |x|^2，避免直接算高阶幂
        term = A[m, 0] * x_d
        poly_term = x_d
        for k in range(1, K):
            poly_term = poly_term * p_d
            term = term + A[m, k] * poly_term
        y = y + term

    return y.T if was_row else y
