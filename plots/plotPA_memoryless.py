"""plotPA_memoryless —— 28 GHz GaN 无记忆模型的增益与相位（plotPA_memoryless.m 的 Python 版）。

用单频复信号驱动 pa_model_memoryless_38803，画增益和相位随输入功率的变化。

用法：
    python plots/plotPA_memoryless.py  # 出图（没装 matplotlib 则只写 CSV）
"""

from __future__ import annotations

import sys
from pathlib import Path

# 允许从 plots/ 目录直接运行：把项目根目录加入 sys.path
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import numpy as np

from PAmodel.pa_model_memoryless_38803 import pa_model_memoryless


def compute():
    input_dbm = np.arange(-30.0, 0.0 + 1e-9, 0.1)
    input_amp = 10.0 ** (input_dbm / 20.0)          # dBm -> 幅度

    x = input_amp * np.exp(1j * 0 * np.pi / 180)    # 单频信号，初相 0 度
    y = pa_model_memoryless(x)

    output_amplitude = np.abs(y)
    output_phase = np.angle(y) * (180 / np.pi)      # 弧度转度

    output_dBm = 20 * np.log10(output_amplitude)
    output_gain = output_dBm - input_dbm
    return input_dbm, output_gain, output_phase


def main():
    x, gain, phase = compute()

    try:
        import matplotlib.pyplot as plt
    except Exception:
        plt = None

    if plt is None:
        with open('pa_memoryless.csv', 'w', encoding='utf-8', newline='') as fh:
            fh.write('input_dbm,output_gain_dB,output_phase_deg\n')
            for a, b, c in zip(x, gain, phase):
                fh.write(f'{a:.4f},{b:.6f},{c:.6f}\n')
        print('提示: 没有安装 matplotlib，图没有画出来；数据已写入 pa_memoryless.csv。')
        print(f'       -10 dBm 输入时增益 {gain[np.argmin(np.abs(x + 10))]:.3f} dB')
        return 0

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(7, 7))
    ax1.plot(x, gain)
    ax1.set_title('AM-AM Curve')
    ax1.set_xlabel('Input Power (dBm)')
    ax1.set_ylabel('Output gain (dB)')
    ax1.grid(True)

    ax2.plot(x, phase)
    ax2.set_title('AM-PM Curve')
    ax2.set_xlabel('Input Power (dBm)')
    ax2.set_ylabel('Output Phase (Degrees)')
    ax2.grid(True)

    fig.tight_layout()
    fig.savefig('pa_memoryless.png', dpi=150, bbox_inches='tight')
    print('figure saved to: pa_memoryless.png')
    plt.close(fig)
    return 0


if __name__ == '__main__':
    sys.exit(main())
