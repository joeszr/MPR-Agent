"""plotPA_HUAWEI —— 2 GHz GaAs 模型的 AM/AM、AM-PM 曲线（plotPA_HUAWEI.m 的 Python 版）。

扫描输入功率，用复指数信号驱动模型，画输出功率与相移。换模型时改下面这一行即可
（原 .m 的注释也是这么说的）。

用法：
    python plotPA_HUAWEI.py           # 出图（没装 matplotlib 则只写 CSV）
"""

from __future__ import annotations

import sys

import numpy as np

from pa_GaAs_2GHz import pa_GaAs_2GHz


def compute():
    input_power_dBm = np.arange(-30.0, 20.0 + 1e-9, 0.05)   # 输入功率范围 (dBm)
    R = 50.0                                                # 系统阻抗 (欧)

    output_power_dBm = np.zeros_like(input_power_dBm)
    phase_shift_deg = np.zeros_like(input_power_dBm)

    f = 0.1            # 归一化频率（任意值）
    n_samples = 10240

    for i, p_dbm in enumerate(input_power_dBm):
        input_power_W = 10 ** ((p_dbm - 30) / 10)           # W
        amplitude_linear = np.sqrt(input_power_W * R)       # RMS 幅度
        x = amplitude_linear * np.exp(
            1j * 2 * np.pi * f * np.arange(n_samples) / n_samples).reshape(-1, 1)

        y = pa_GaAs_2GHz(x)                                # ← 换模型改这里

        output_power_W = np.mean(np.abs(y) ** 2) / R
        output_power_dBm[i] = 10 * np.log10(output_power_W) + 30
        phase_in = np.angle(x[0, 0])
        phase_out = np.angle(y[0, 0])
        phase_shift_deg[i] = np.rad2deg(phase_out - phase_in)

    return input_power_dBm, output_power_dBm, phase_shift_deg


def main():
    p_in, p_out, phase = compute()

    try:
        import matplotlib.pyplot as plt
    except Exception:
        plt = None

    if plt is None:
        with open('pa_huawei.csv', 'w', encoding='utf-8', newline='') as fh:
            fh.write('input_power_dBm,output_power_dBm,phase_shift_deg\n')
            for a, b, c in zip(p_in, p_out, phase):
                fh.write(f'{a:.4f},{b:.6f},{c:.6f}\n')
        print('提示: 没有安装 matplotlib，图没有画出来；数据已写入 pa_huawei.csv。')
        i = int(np.argmin(np.abs(p_in + 10)))
        print(f'       -10 dBm 输入时增益 {p_out[i] - p_in[i]:.2f} dB')
        return 0

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
    ax1.plot(p_in, p_out, 'b-', linewidth=1.5, label='model')
    ax1.plot(p_in, p_in, 'k-', linewidth=1.0, label='ideal')
    ax1.grid(True)
    ax1.set_xlabel('PA Input Power (dBm)')
    ax1.set_ylabel('PA Output Power (dBm)')
    ax1.set_title('AM-AM Characteristic')

    ax2.plot(p_in, phase, 'r-', linewidth=1.5)
    ax2.grid(True)
    ax2.set_xlabel('PA Input Power (dBm)')
    ax2.set_ylabel('Phase Shift (Degrees)')
    ax2.set_title('AM-PM Characteristic')

    fig.suptitle('PC2 PA Model (K=9, M=0) - AM/AM & AM/PM')
    fig.savefig('pa_huawei.png', dpi=150, bbox_inches='tight')
    print('figure saved to: pa_huawei.png')
    plt.close(fig)
    return 0


if __name__ == '__main__':
    sys.exit(main())
