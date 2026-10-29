"""plotPA_memory —— TR 38.803 GMP 模型的 AM/AM、AM-PM 散点图（plotPA_memory.m 的 Python 版）。

按 TR 38.803 附录 A.1 的格式画 2.1 GHz GaAs 广义记忆多项式：
  x 轴：归一化输入功率 [dB]（0 dB 对应 |x| = 1）
  y 轴：增益 [dB]（AM-AM）与相位 [deg]（AM-PM）
  蓝色散点：GMP 模型输出（散开的点云来自记忆效应）
  红色曲线：同一个功放的无记忆模型（静态参考）

驱动信号：307.2 MHz 采样率、占用约 40 MHz 的 OFDM 波形，与规范一致。

用法：
    python plots/plotPA_memory.py      # 出图（没装 matplotlib 则只写 CSV）
"""

from __future__ import annotations

import sys
from pathlib import Path

# 允许从 plots/ 目录直接运行：把项目根目录加入 sys.path
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import numpy as np

from PAmodel.pa_model_memory_38803 import pa_model_memory_38803
from PAmodel.pa_model_memoryless_38803 import pa_model_memoryless


def build_ofdm_drive(seed=0):
    """驱动信号：307.2 MHz 采样、40 MHz 带宽、1/16 CP 的 OFDM。"""
    rng = np.random.RandomState(seed)

    fs = 307.2e6               # 采样率 (Hz)
    bw = 40e6                  # 信号带宽 (Hz)
    N_fft = 4096               # 每个 OFDM 符号的 FFT 点数
    df = fs / N_fft            # 子载波间隔
    N_used = 2 * int(np.floor(bw / 2 / df))   # 占用的子载波数
    N_sym = 80
    N_cp = int(round(N_fft / 16))

    x_td = np.zeros((N_fft + N_cp) * N_sym, dtype=complex)
    half = N_used // 2

    for s in range(N_sym):
        data = ((2 * rng.randint(0, 16, N_used) - 15)
                + 1j * (2 * rng.randint(0, 16, N_used) - 15)).astype(complex)
        data = data / np.sqrt(170)          # 256QAM 平均功率归一化
        X_fd = np.zeros(N_fft, dtype=complex)
        X_fd[1:1 + half] = data[:half]                  # 正频率
        X_fd[N_fft - half:] = data[half:]               # 负频率
        x_sym = np.fft.ifft(X_fd) * np.sqrt(N_fft)
        x_sym = np.concatenate([x_sym[-N_cp:], x_sym])  # 加 CP
        idx = s * (N_fft + N_cp) + np.arange(N_fft + N_cp)
        x_td[idx] = x_sym

    # 峰值压到 1 以下（模型定义域 0 <= |x| <= 1）
    return x_td / np.max(np.abs(x_td)) * 0.95


def compute():
    x_td = build_ofdm_drive()

    y_gmp = pa_model_memory_38803(x_td)             # 有记忆（GMP）
    y_mem = pa_model_memoryless(x_td)               # 无记忆基线

    in_dB = 20 * np.log10(np.abs(x_td))
    gmp_gain_dB = 20 * np.log10(np.abs(y_gmp)) - in_dB
    gmp_phase_dg = np.angle(y_gmp / x_td) * 180 / np.pi

    mem_gain_dB = 20 * np.log10(np.abs(y_mem)) - in_dB
    mem_phase_dg = np.angle(y_mem / x_td) * 180 / np.pi

    mask = (in_dB >= -30) & (in_dB <= 0)
    in_dB = in_dB[mask]
    gmp_gain_dB = gmp_gain_dB[mask]
    gmp_phase_dg = gmp_phase_dg[mask]
    mem_gain_dB = mem_gain_dB[mask]
    mem_phase_dg = mem_phase_dg[mask]

    order = np.argsort(in_dB)
    return {
        'input_dB': in_dB,
        'gmp_gain_dB': gmp_gain_dB,
        'gmp_phase_deg': gmp_phase_dg,
        'memless_gain_dB': mem_gain_dB,
        'memless_phase_deg': mem_phase_dg,
        'input_dB_sorted': in_dB[order],
        'memless_gain_dB_sorted': mem_gain_dB[order],
        'memless_phase_deg_sorted': mem_phase_dg[order],
    }


def main():
    d = compute()

    try:
        import matplotlib.pyplot as plt
    except Exception:
        plt = None

    if plt is None:
        with open('pa_memory.csv', 'w', encoding='utf-8', newline='') as fh:
            fh.write('input_dB,gmp_gain_dB,gmp_phase_deg,'
                     'memless_gain_dB,memless_phase_deg\n')
            for row in zip(d['input_dB'], d['gmp_gain_dB'], d['gmp_phase_deg'],
                           d['memless_gain_dB'], d['memless_phase_deg']):
                fh.write(','.join(f'{v:.6f}' for v in row) + '\n')
        print('提示: 没有安装 matplotlib，图没有画出来；数据已写入 pa_memory.csv。')
        g = d['gmp_gain_dB']
        print(f'       GMP 增益离散度 {g.max() - g.min():.2f} dB')
        return 0

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(7, 7))

    ax1.plot(d['input_dB'], d['gmp_gain_dB'], '.', color=(0, 0, 1), markersize=3)
    ax1.plot(d['input_dB_sorted'], d['memless_gain_dB_sorted'], 'r-', linewidth=1.5)
    ax1.grid(True)
    ax1.set_xlabel('Normalized input power [dB]')
    ax1.set_ylabel('Gain [dB]')
    ax1.set_title('AM-AM: 2.1GHz GaAs PA, (blue) GMP model (red) static model')
    ax1.set_xlim(-30, 0)
    ax1.set_ylim(-5, 5)

    ax2.plot(d['input_dB'], d['gmp_phase_deg'], '.', color=(0, 0, 1), markersize=3)
    ax2.plot(d['input_dB_sorted'], d['memless_phase_deg_sorted'], 'r-', linewidth=1.5)
    ax2.grid(True)
    ax2.set_xlabel('Normalized input power [dB]')
    ax2.set_ylabel('Phase [deg]')
    ax2.set_title('AM-PM: 2.1GHz GaAs PA, (blue) GMP model (red) static model')
    ax2.set_xlim(-30, 0)
    ax2.set_ylim(-150, -100)

    fig.tight_layout()
    fig.savefig('pa_memory.png', dpi=150, bbox_inches='tight')
    print('figure saved to: pa_memory.png')
    plt.close(fig)
    return 0


if __name__ == '__main__':
    sys.exit(main())
