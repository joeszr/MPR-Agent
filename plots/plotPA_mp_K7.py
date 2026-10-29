"""plotPA_mp_K7 —— PC2 K=7、M=3 模型的 AM/AM、AM-PM 曲线（plotPA_mp_K7.m 的 Python 版）。

系数与参数出自 PC2 文档：
  NOTE 1: 前端 4 dB 插损已包含在模型里；
  NOTE 2: 采样率 614.4 MHz；
  NOTE 3: 输入在 5 dBm（50 欧 0.39764 V 峰值）处截幅，最小有效输入 -30 dBm。

用法：
    python plots/plotPA_mp_K7.py       # 出图（没装 matplotlib 则只写 CSV）
"""

from __future__ import annotations

import sys
from pathlib import Path

# 允许从 plots/ 目录直接运行：把项目根目录加入 sys.path
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import numpy as np

from matlab_builtins import rad2deg

# ---- 1. 系数矩阵 A(m+1, k) = a_{m, 2k-1}，m = 0..3，k = 1..7 ----
A = np.zeros((4, 7), dtype=complex)

# 第 1 行：m = 0
A[0, 0] = 1.78125421e+01 + 3.96234802e+00j     # a0,1
A[0, 1] = 9.75722189e+01 + 9.49718204e+01j     # a0,3
A[0, 2] = -4.36921775e+03 - 2.90487370e+03j    # a0,5
A[0, 3] = 6.67412504e+04 + 3.62371316e+04j     # a0,7
A[0, 4] = -5.42918789e+05 - 2.29695739e+05j    # a0,9
A[0, 5] = 2.19218318e+06 + 7.35795077e+05j     # a0,11
A[0, 6] = -3.40445900e+06 - 9.45835587e+05j    # a0,13

# 第 2 行：m = 1
A[1, 0] = 7.75483096e+00 - 1.06941812e+01j
A[1, 1] = -6.46736904e+01 + 1.55427298e+01j
A[1, 2] = 3.25651083e+03 - 5.88392401e+02j
A[1, 3] = -4.19280551e+04 + 6.06657427e+03j
A[1, 4] = 2.56101445e+05 - 3.11728454e+04j
A[1, 5] = -7.70951908e+05 + 8.54072559e+04j
A[1, 6] = 9.20919772e+05 - 1.00871883e+05j

# 第 3 行：m = 2
A[2, 0] = -7.72899765e+00 + 9.04484189e+00j
A[2, 1] = 2.65557457e+00 - 1.41372308e+01j
A[2, 2] = -5.23038528e+02 + 4.58746411e+02j
A[2, 3] = 3.95605656e+03 - 5.72662196e+03j
A[2, 4] = 9.08023985e+02 + 3.43943069e+04j
A[2, 5] = -8.90153246e+04 - 1.02613131e+05j
A[2, 6] = 2.14152570e+05 + 1.22085816e+05j

# 第 4 行：m = 3
A[3, 0] = 2.48795348e+00 - 2.76518830e+00j
A[3, 1] = 8.14834939e+00 + 3.68035394e+00j
A[3, 2] = -1.51258701e+02 - 1.40300633e+02j
A[3, 3] = 4.02914882e+03 + 1.39078164e+03j
A[3, 4] = -4.26449208e+04 - 3.95132361e+03j
A[3, 5] = 1.90424815e+05 - 6.66193945e+03j
A[3, 6] = -3.07290090e+05 + 3.43617693e+04j

M = 3
K = 7

# NOTE 3：输入截幅
APPLY_CLIP = True
Vclip = 0.39764          # 5 dBm 峰值电压（50 欧）


def memory_polynomial_cw(x):
    """逐点记忆多项式：``y[n] = sum_m x[n-m] * polyval(A[m,:], |x[n-m]|^2)``。

    与 .m 里那层嵌套循环是同一个求和，只是按抽头向量化。
    """
    x_padded = np.concatenate([np.zeros(M, dtype=complex), x])
    y = np.zeros(x.size, dtype=complex)
    for m in range(M + 1):
        x_d = x_padded[M - m:M - m + x.size]
        y = y + x_d * np.polyval(A[m][::-1], np.abs(x_d) ** 2)
    return y


def compute():
    """返回 ``(P_in_dBm, P_out_dBm, Phase_deg)``。"""
    P_in_dBm = np.arange(-30.0, 10.0 + 1e-9, 0.1)
    P_out_dBm = np.zeros_like(P_in_dBm)
    Phase_deg = np.zeros_like(P_in_dBm)

    R = 50.0
    N_sig = 100
    f_norm = 0.1

    for i, p_dbm in enumerate(P_in_dBm):
        P_watt = 10 ** (p_dbm / 10) / 1000
        amp = np.sqrt(P_watt * R)        # 峰值幅度（文档约定）
        x = amp * np.exp(1j * 2 * np.pi * f_norm * np.arange(N_sig))

        if APPLY_CLIP:
            mag = np.abs(x)
            over = mag > Vclip
            if np.any(over):
                x[over] = Vclip * x[over] / mag[over]

        y = memory_polynomial_cw(x)

        y_steady = y[-1]
        x_steady = x[-1]
        P_out_watt = np.abs(y_steady) ** 2 / R
        P_out_dBm[i] = 10 * np.log10(P_out_watt * 1000)
        Phase_deg[i] = rad2deg(np.angle(y_steady) - np.angle(x_steady))

    return P_in_dBm, P_out_dBm, Phase_deg


def main():
    P_in, P_out, Phase = compute()

    try:
        import matplotlib.pyplot as plt
    except Exception:
        plt = None

    if plt is None:
        with open('pa_k7.csv', 'w', encoding='utf-8', newline='') as fh:
            fh.write('P_in_dBm,P_out_dBm,Phase_deg\n')
            for a, b, c in zip(P_in, P_out, Phase):
                fh.write(f'{a:.4f},{b:.6f},{c:.6f}\n')
        print('提示: 没有安装 matplotlib，图没有画出来；数据已写入 pa_k7.csv。')
        print(f'       5 dBm 输入时输出 {P_out[np.argmin(np.abs(P_in - 5.0))]:.2f} dBm')
        return 0

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
    ax1.plot(P_in, P_out, 'b-', linewidth=1.5)
    ax1.axvline(5, color='k', linestyle='--', label='5 dBm clip')
    ax1.grid(True)
    ax1.set_xlabel('PA Input Power (dBm)')
    ax1.set_ylabel('PA Output Power (dBm)')
    ax1.set_title('AM-AM Characteristic')
    ax1.set_xlim(-30, 10)

    ax2.plot(P_in, Phase, 'r-', linewidth=1.5)
    ax2.axvline(5, color='k', linestyle='--', label='5 dBm clip')
    ax2.grid(True)
    ax2.set_xlabel('PA Input Power (dBm)')
    ax2.set_ylabel('Phase Shift (Degrees)')
    ax2.set_title('AM-PM Characteristic')
    ax2.set_xlim(-30, 10)

    fig.suptitle('PC2 PA Model (K=7, M=3) - AM/AM & AM/PM')
    fig.savefig('pa_k7.png', dpi=150, bbox_inches='tight')
    print('figure saved to: pa_k7.png')
    plt.close(fig)
    return 0


if __name__ == '__main__':
    sys.exit(main())
