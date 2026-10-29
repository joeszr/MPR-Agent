"""DFT-s-OFDM MPR 计算主程序 —— DFT_ofdm_mainV2.m 的 Python 版。

功能：遍历不同 RB 配置，计算满足 EVM/ACLR/SEM/IBE 指标的最大输出功率及 MPR。
子程序：apply_pa_model, check_EVM_DFT, check_ACLR, check_SEM_FR1, check_SEM_FR2,
        check_IBE, check_region_avg_left, check_region_avg_right

运行（在项目根目录下）：
    python DFT_ofdm_mainV2.py

目录结构：功放模型在 PAmodel/，指标检测在 Checks/，绘图脚本在 plots/。本脚本用包
导入引用它们，所以在项目根目录下运行即可（脚本所在目录会自动进入 sys.path）。

与 CP-OFDM 版的区别（与 .m 一致）：
  * 子载波映射前多一次 DFT 预编码，EVM 判决里对应多做一步 IDFT；
  * 12*lcrb 不是 5-平滑数（最大质因子 > 5）的配置直接跳过，结果保持初值 0；
  * SEM 判决放在 ACLR / EVM 之前，而且 IBE 判决是打开的；
  * PSD 用 pwelch 而不是单次 FFT；
  * 功率搜索从 -25 dB 起步；
  * QPSK 的 EVM 限值取 3.5%（规范是 17.5%，原 .m 就是这样收紧的，保持不变）。

默认全量扫描（37401 个 RB 配置 × 30 次蒙特卡洛），单进程约 12 小时；
调试时把 CONFIG_START / CONFIG_STOP 改小，或把 MONTE_CARLO 改成 1。
"""

from __future__ import annotations

import time

import numpy as np

from Checks.check_ACLR import check_ACLR
from Checks.check_EVM_DFT import check_EVM_DFT
from Checks.check_IBE import check_IBE
from Checks.check_SEM_FR1 import check_SEM_FR1
from Checks.check_SEM_FR2 import check_SEM_FR2
from PAmodel.apply_pa_model import apply_pa_model
from matlab_builtins import factor, fftshift, hann, ifftshift, pwelch, qammod

# ====================== 参数配置 ======================
freq_band = 'FR1'
PA_MODEL_TYPE = 'MP1'         # 功放模型：'MP1', 'HZW_HB', 'MP', 'MEMORYLESS', 'MEMORY'
k_max = 10
ACLR_spec = 31                # ACLR (PC3:30, PC2:31 FR2:16)

NRB = 273                     # 资源块数，100M:273, 20M:106, 40M:216
CBW = 100                     # 信道带宽 (MHz)
Fs = 614.4 * 1000             # 采样率 (kHz)
ifft_length = 20480           # IFFT 长度

REF_SCS = 30                  # 参考子载波间隔 (kHz)
scs = 30                      # 子载波间隔 (kHz)
ds = 1                        # 窗分段数

mod_order = 4                 # 调制阶数：4=QPSK, 16, 64, 256, 1024

# 扫描范围与蒙特卡洛次数（.m 里写死为 1:37401 / 30，这里提出来便于调试）
CONFIG_START = 1              # 第一个配置（1 基）
CONFIG_STOP = 37401           # 最后一个配置（含）
MONTE_CARLO = 30              # 每个配置的随机序列次数
RANDOM_SEED = None            # None：每次不同（同 MATLAB）；给整数可复现

# ====================== FFT 参数计算 ======================
FFT_factor = Fs / ifft_length          # FFT 频率分辨率 (kHz)
bins_per_1MHz = 1000 / FFT_factor      # 每 1MHz 对应的频点数
scs_step = scs / FFT_factor            # 子载波间隔对应的频点步长

# ====================== 调制参数 ======================
if mod_order == 4:
    EVMLevel = 3.5                     # EVM 限值 (%)（原 .m 收紧，规范为 17.5）
    bit_per_symbol = 2                 # 每符号比特数
elif mod_order == 16:
    EVMLevel = 12.5
    bit_per_symbol = 4
elif mod_order == 64:
    EVMLevel = 8
    bit_per_symbol = 6
elif mod_order == 256:
    EVMLevel = 3.5
    bit_per_symbol = 8
elif mod_order == 1024:
    EVMLevel = 2.2
    bit_per_symbol = 10
else:
    raise ValueError(f'Unsupported mod_order: {mod_order}')

SNR = 40
symbol_count = 1
CP_length = int(np.floor(ifft_length * 0.75))


# ====================== 生成 RB 配置表 ======================
def build_configs():
    """``configs``：每行 ``[lcrb, rbstart, rbend]``，共 NRB*(NRB+1)/2 行。"""
    rows = []
    for rbstart in range(NRB):
        for rbend in range(rbstart, NRB):
            rows.append((rbend - rbstart + 1, rbstart, rbend))
    return np.asarray(rows, dtype=int)


# ====================== 单个配置的计算 ======================
def simulate_config(lcrb, rbstart, rbend, rng):
    """返回 ``(outputpowerfinal6, sum(ACLR), sum(SEM), sum(IBE), sum(EVM))``。

    被 5-平滑规则跳过的配置返回 ``None``（对应 .m 里的 ``continue``）。
    """
    carrier_count = 12 * lcrb          # 子载波数

    # DFT 长度限制：跳过最大质因子 > 5 的配置（TS 38.211 transform precoding）
    if factor(carrier_count).max() > 5:
        return None

    # 载波位置计算
    aa11 = ifft_length / 2 - (12 * NRB * scs_step) / 2 + 1 + 12 * rbstart * scs_step
    cc11 = (ifft_length / 2 - (12 * NRB * scs_step) / 2 + 1
            + 12 * rbend * scs_step + 12 * scs_step - 1)
    aa11 = int(aa11)
    cc11 = int(cc11)
    carrier_position = np.arange(aa11, cc11 + 1)       # 1 基下标

    power_array = np.zeros(MONTE_CARLO)
    ACLR_array = np.zeros(MONTE_CARLO)
    SEM_array = np.zeros(MONTE_CARLO)
    IBE_array = np.zeros(MONTE_CARLO)
    EVM_array = np.zeros(MONTE_CARLO)

    # .m 里没有初始化；未找到有效工作点时记 NaN
    outputpower_last = np.nan

    Msc = carrier_count

    for j in range(MONTE_CARLO):
        # ---- 产生随机序列与 DFT 预编码 ----
        data_check = True
        while data_check:
            bit_length = carrier_count * symbol_count * bit_per_symbol
            bit_sequence = np.round(rng.random_sample(bit_length)).reshape(-1, 1)

            # 子载波调制
            bit_moded = qammod(bit_sequence, mod_order, input_type='bit')
            bit_modedn = bit_moded

            # DFT 预编码
            total_symbols = bit_moded.size
            if total_symbols % Msc != 0:
                raise ValueError('Total modulated symbols not divisible by Msc '
                                 '(carrier_count).')

            bit_moded_matrix = bit_moded.reshape(Msc, symbol_count, order='F')
            bit_moded_dft = np.fft.fft(bit_moded_matrix, axis=0) / np.sqrt(Msc)

            # 检查 DFT 后是否有零值（会导致除零错误）
            data_check = bool(np.min(np.abs(bit_moded_dft)) == 0)

        # 恢复为列向量
        bit_moded = bit_moded_dft.reshape(-1, 1, order='F')

        # ---- 串并转换与载波映射 ----
        bit_moded1 = np.zeros((carrier_count, int(scs_step)), dtype=complex)
        bit_moded1[:, 0:1] = bit_moded
        bit_moded2 = bit_moded1.T
        bit_moded2 = bit_moded2.reshape(carrier_count * int(scs_step), symbol_count,
                                        order='F')

        ifft_position = np.zeros((ifft_length, symbol_count), dtype=complex)
        ifft_position[carrier_position - 1, :] = bit_moded2[:, 0:1]

        # ---- IFFT 与添加 CP ----
        ifft_position = ifftshift(ifft_position, 0)
        signal_time = np.fft.ifft(ifft_position, n=ifft_length, axis=0)
        signal_time_C = np.vstack([signal_time[ifft_length - CP_length:, :],
                                   signal_time])
        signal_window = signal_time_C

        # ---- 信号归一化 ----
        signal_window = signal_window / np.max(np.abs(signal_window))

        # ---- 多粒度功率回退搜索 ----
        k = -25                        # 初始回退值，MP1=-25, HZW=-15
        steps = (5, 1, 0.2)            # 粗/中/细三档步长

        for step in steps:
            # 重置检测结果
            SEMresult = 1
            ACLRresult = 1
            EVMresult = 1
            IBEresult = 1

            while SEMresult == 1 and ACLRresult == 1 and EVMresult == 1 and IBEresult == 1:
                k = k + step

                # 应用 PA 模型
                output = apply_pa_model(signal_window, k, PA_MODEL_TYPE)

                # 计算 PSD
                window3 = hann(ifft_length / ds)
                noverlap = ifft_length - CP_length
                psd1, _f = pwelch(output, window3, noverlap, ifft_length, Fs)
                psd1 = fftshift(psd1, 0)

                # 计算信道带宽内功率
                CBW_start = int(np.floor(psd1.size / 2 - (CBW / 2 * bins_per_1MHz))) + 1
                CBW_end = int(np.floor(psd1.size / 2 + (CBW / 2 * bins_per_1MHz)))
                outputpower = np.sum(psd1[CBW_start - 1:CBW_end]) * FFT_factor

                # SEM 检测
                if str(freq_band).lower() == 'fr1':
                    SEMresult = check_SEM_FR1(psd1, CBW, FFT_factor, bins_per_1MHz)
                    if SEMresult != 1:
                        break
                elif str(freq_band).lower() == 'fr2':
                    SEMresult = check_SEM_FR2(psd1, CBW, FFT_factor, bins_per_1MHz)
                    if SEMresult != 1:
                        break

                # ACLR 检测
                ACLRresult = check_ACLR(psd1, CBW, REF_SCS, NRB, ACLR_spec,
                                        FFT_factor, bins_per_1MHz)
                if ACLRresult != 1:
                    break

                # EVM 检测（DFT 专用）
                EVMresult = check_EVM_DFT(output, CP_length, ifft_length,
                                          carrier_position, scs, scs_step,
                                          carrier_count, lcrb, bit_moded, bit_modedn,
                                          SNR, EVMLevel, Msc)
                if EVMresult != 1:
                    break

                # IBE 检测
                IBEresult = check_IBE(rbstart, rbend, NRB, lcrb, scs, scs_step,
                                      EVMLevel, outputpower, carrier_position,
                                      aa11, cc11, psd1)
                if IBEresult != 1:
                    break
                outputpower_last = outputpower

            # 回退到最后一个有效值
            k = k - step

        power_array[j] = outputpower_last
        ACLR_array[j] = ACLRresult
        SEM_array[j] = SEMresult
        IBE_array[j] = IBEresult
        EVM_array[j] = EVMresult

    # ---- 汇总当前配置结果 ----
    outputpowerfinal = np.sum(power_array)
    with np.errstate(divide='ignore', invalid='ignore'):
        outputpowerfinal6 = 10 * np.log10(outputpowerfinal / MONTE_CARLO)

    return (float(outputpowerfinal6), float(np.sum(ACLR_array)),
            float(np.sum(SEM_array)), float(np.sum(IBE_array)),
            float(np.sum(EVM_array)))


# ====================== 主程序 ======================
def main():
    configs = build_configs()
    num_configs = configs.shape[0]
    if not (1 <= CONFIG_START <= CONFIG_STOP <= num_configs):
        raise ValueError(f'扫描范围 {CONFIG_START}..{CONFIG_STOP} 超出 1..{num_configs}')

    MPR_results = np.zeros(num_configs)
    ACLR_results = np.zeros(num_configs)
    SEM_results = np.zeros(num_configs)
    IBE_results = np.zeros(num_configs)
    EVM_results = np.zeros(num_configs)

    rng = np.random.RandomState(RANDOM_SEED)
    if RANDOM_SEED is not None:
        print(f'random seed = {RANDOM_SEED}')

    tic = time.perf_counter()

    # ====================== 主循环：遍历配置 ======================
    for i in range(CONFIG_START - 1, CONFIG_STOP):
        lcrb = int(configs[i, 0])
        rbstart = int(configs[i, 1])
        rbend = int(configs[i, 2])

        result = simulate_config(lcrb, rbstart, rbend, rng)
        if result is not None:                     # None = 被 5-平滑规则跳过
            (MPR_results[i], ACLR_results[i], SEM_results[i],
             IBE_results[i], EVM_results[i]) = result

        print(f'Config {i + 1}/{num_configs}: lcrb={lcrb}, rbstart={rbstart}, '
              f'rbend={rbend}, MPR={MPR_results[i]:.2f} dBW')

    # ====================== 保存结果 ======================
    stamp = time.strftime('%m%d-%H%M')
    fileName = stamp
    np.savez(fileName + '.npz', MPR_results=MPR_results, ACLR_results=ACLR_results,
             SEM_results=SEM_results, IBE_results=IBE_results,
             EVM_results=EVM_results)
    print(f'结果已保存至: {fileName}.npz')
    try:                                    # 装了 scipy 时额外写 MATLAB 的 .mat
        from scipy.io import savemat
        savemat(fileName + '.mat',
                dict(MPR_results=MPR_results, ACLR_results=ACLR_results,
                     SEM_results=SEM_results, IBE_results=IBE_results,
                     EVM_results=EVM_results))
        print(f'结果已保存至: {fileName}.mat')
    except ImportError:
        pass

    elapsed_time = time.perf_counter() - tic
    print(f'总耗时: {elapsed_time:.1f} 秒')


if __name__ == '__main__':
    main()
