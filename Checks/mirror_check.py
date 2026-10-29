"""mirror_check —— 左右镜像对称性自检（mirror_check.m 的 Python 版）。

对每个分配 (rbstart, L) 同时跑镜像分配 (NRB - rbstart - L, L)，两边用同一组 QAM
符号。如果整条测量链路对称，两者的收敛点 k_final 与各项指标必须（统计上）相同。

跑两种功放变体：
    "full"    = pa_model_mp_K7 原样（MP1 分支用的就是它）
    "memless" = 同一组系数但把 m >= 1 的记忆抽头置零（无记忆对照）

如果 "memless" 的镜像对完全一致、"full" 的镜像对有差异，说明 MPR 图的左右不对称
来自功放记忆效应（物理原因），不是测量链路的 bug。

这是可直接运行的诊断脚本（不是被主程序调用的检测函数），默认跑到全部镜像对结束。

用法（在项目根目录下）：
    python Checks/mirror_check.py

也可以当作模块跑：
    python -m Checks.mirror_check
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

# 允许从 Checks/ 目录直接运行：把项目根目录加入 sys.path
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import numpy as np

from matlab_builtins import comm_evm, fftshift, hann, ifftshift, pwelch, qammod

# ---------------------------------------------------------------------------
# 参数（与要验证的那次仿真保持一致）
# ---------------------------------------------------------------------------
NRB = 273              # 100M:273, 20M(15kHz):106
CBW = 100              # MHz
Fs = 614.4 * 1000
ifft_length = 20480    # 必须保证 scs_step = scs/(Fs/ifft_length) 为整数
REF_SCS = 30           # kHz（ACLR 测量带宽）；15kHz SCS 时用 15
scs = 30               # kHz
mod_order = 256        # 4 / 16 / 64 / 256
EVMLevel = 1.9         # 必须与那次仿真一致
aclrrelaxation = -1    # PC3: 0, PC2: -1
kref = -8              # 对比各指标时共用的驱动电平

# 要测的镜像对：[rbstart L]，镜像自动计算
pairs = [(0, 100), (30, 50), (10, 20), (86, 100)]

FFT_factor = Fs / ifft_length
bins_per_1MHz = 1000 / FFT_factor
scs_step = scs / FFT_factor
assert scs_step == int(scs_step), 'scs_step 不是整数——检查 Fs / ifft_length / scs'
CP_length = int(np.floor(ifft_length * 0.75))
bps = {4: 2, 16: 4, 64: 6, 256: 8}[mod_order]


# ========================= local functions =========================
def get_mpk7_coeffs():
    """``get_mpk7_coeffs``：与 MATLAB 相同的 4x7 系数矩阵。"""
    c = np.array([
        1.78125421e+01 + 3.96234802e+00j, 7.75483096e+00 - 1.06941812e+01j,
        -7.72899765e+00 + 9.04484189e+00j, 2.48795348e+00 - 2.76518830e+00j,
        9.75722189e+01 + 9.49718204e+01j, -6.46736904e+01 + 1.55427298e+01j,
        2.65557457e+00 - 1.41372308e+01j, 8.14834939e+00 + 3.68035394e+00j,
        -4.36921775e+03 - 2.90487370e+03j, 3.25651083e+03 - 5.88392401e+02j,
        -5.23038528e+02 + 4.58746411e+02j, -1.51258701e+02 - 1.40300633e+02j,
        6.67412504e+04 + 3.62371316e+04j, -4.19280551e+04 + 6.06657427e+03j,
        3.95605656e+03 - 5.72662196e+03j, 4.02914882e+03 + 1.39078164e+03j,
        -5.42918789e+05 - 2.29695739e+05j, 2.56101445e+05 - 3.11728454e+04j,
        9.08023985e+02 + 3.43943069e+04j, -4.26449208e+04 - 3.95132361e+03j,
        2.19218318e+06 + 7.35795077e+05j, -7.70951908e+05 + 8.54072559e+04j,
        -8.90153246e+04 - 1.02613131e+05j, 1.90424815e+05 - 6.66193945e+03j,
        -3.40445900e+06 - 9.45835587e+05j, 9.20919772e+05 - 1.00871883e+05j,
        2.14152570e+05 + 1.22085816e+05j, -3.07290090e+05 + 3.43617693e+04j])
    return c.reshape((4, 7), order='F')


def pa_local(x, model):
    """``pa_local``：mp_K7，可选地把记忆抽头去掉。"""
    coeffs = get_mpk7_coeffs()
    if model == 'memless':
        coeffs[1:4, :] = 0

    x = np.array(x, dtype=complex, copy=True)
    Vclip = 0.39764
    mag = np.abs(x)
    over = mag > Vclip
    if np.any(over):
        x[over] = Vclip * x[over] / mag[over]

    x = x.reshape(-1, 1)
    N = x.size
    M, K = 3, 7
    y = np.zeros((N, 1), dtype=complex)
    xp = np.vstack([np.zeros((M, 1), dtype=complex), x])
    pp = np.abs(xp) ** 2

    for m in range(M + 1):
        xd = xp[M - m:M - m + N]
        pd = pp[M - m:M - m + N]
        term = coeffs[m, 0] * xd
        poly = xd
        for k in range(1, K):
            poly = poly * pd
            term = term + coeffs[m, k] * poly
        y = y + term
    return y


def run_search(rbstart, L, bits, model):
    """``run_search``：功率搜索 + 表格里那几列指标。"""
    rbend = rbstart + L - 1
    aa11 = int(ifft_length / 2 - (12 * NRB * scs_step) / 2 + 1 + 12 * rbstart * scs_step)
    cc11 = int(ifft_length / 2 - (12 * NRB * scs_step) / 2 + 1
               + 12 * rbend * scs_step + 12 * scs_step - 1)
    carrier_position = np.arange(aa11, cc11 + 1)

    bit_modedn = qammod(bits, mod_order, input_type='bit')
    bm1 = np.zeros((12 * L, int(scs_step)), dtype=complex)
    bm1[:, 0:1] = bit_modedn
    bm2 = bm1.T.reshape(int(12 * L * scs_step), 1, order='F')

    ifft_position = np.zeros((ifft_length, 1), dtype=complex)
    ifft_position[carrier_position - 1, 0] = bm2[:, 0]
    ifft_position = ifftshift(ifft_position, 0)
    signal_time = np.fft.ifft(ifft_position, n=ifft_length, axis=0)
    signal_time_C = np.vstack([signal_time[ifft_length - CP_length:, :], signal_time])
    signal_window = signal_time_C / np.max(np.abs(signal_time_C))

    def eval_at(k):
        output = pa_local(signal_window * 10 ** (k / 20), model) * np.sqrt(20)
        psd1, _ = pwelch(output, hann(ifft_length), ifft_length - CP_length,
                         ifft_length, Fs)
        psd1 = fftshift(psd1, 0)
        lenp = psd1.size
        CBW_start = int(np.floor(lenp / 2 - (CBW / 2 * bins_per_1MHz)))
        CBW_end = int(np.floor(lenp / 2 + (CBW / 2 * bins_per_1MHz))) - 1
        outp = float(np.sum(psd1[CBW_start - 1:CBW_end]) * FFT_factor)

        # EVM：与 check_EVM 相同（H_LS 均值做平坦均衡）
        rx = output[CP_length:, :]
        X = fftshift(np.fft.fft(rx, axis=0) / ifft_length, 0)
        sig1 = X[carrier_position - 1, :]
        sig11 = sig1.reshape((int(scs_step), 12 * L), order='F')
        sig8 = sig11[0, :].reshape(-1, 1) / np.max(np.abs(sig11[0, :]))
        b1 = bit_modedn.reshape((6, 2 * L), order='F')
        s88 = sig8.reshape((6, 2 * L), order='F')
        H_LS = b1[0, :] / s88[0, :]
        eq = np.mean(H_LS) * sig8
        m_evm = comm_evm(bit_modedn, eq)

        # ACLR：与 check_ACLR 相同
        MBW = REF_SCS * (12 * NRB + 1) / 1000
        k1 = int(np.floor(lenp / 2 - (MBW / 2 * bins_per_1MHz)))
        i1 = int(np.floor(MBW * bins_per_1MHz))
        mainp = np.sum(psd1[k1:k1 + i1]) * FFT_factor
        k2 = int(np.floor(lenp / 2 - ((MBW / 2 + CBW) * bins_per_1MHz)))
        k3 = int(np.floor(lenp / 2 + ((-MBW / 2 + CBW) * bins_per_1MHz)))
        with np.errstate(divide='ignore', invalid='ignore'):
            aclr_l = (10 * np.log10(mainp)
                      - 10 * np.log10(np.sum(psd1[k2:k2 + i1]) * FFT_factor))
            aclr_r = (10 * np.log10(mainp)
                      - 10 * np.log10(np.sum(psd1[k3:k3 + i1]) * FFT_factor))

        # IBE：与 check_IBE 相同（输出裕量，<= 0 为通过）
        if rbstart > 0 and rbend < NRB - 1:
            ibe_limit = max(-25 - 10 * np.log10(NRB / L),
                            20 * np.log10(EVMLevel / 100) - 3,
                            -57 + 10 * np.log10(scs / 15) - 10 * np.log10(outp / L))
            aver = 10 * np.log10(np.mean(psd1[carrier_position - 1]) * 12 * scs_step) + 1
            lft = 10 * np.log10(np.mean(psd1[aa11 - int(12 * scs_step) - 2:aa11 - 2])
                                * 12 * scs_step)
            rgt = 10 * np.log10(np.mean(psd1[cc11 + 1:cc11 + int(12 * scs_step) + 1])
                                * 12 * scs_step)
            ibe_lm = (lft - aver) - ibe_limit
            ibe_rm = (rgt - aver) - ibe_limit
            ibe_pass = ibe_lm <= 0 and ibe_rm <= 0
        else:
            ibe_lm = ibe_rm = np.nan
            ibe_pass = True

        ok = [m_evm < EVMLevel,
              aclr_l >= 30 - aclrrelaxation and aclr_r >= 30 - aclrrelaxation,
              ibe_pass]
        met = SimpleNamespace(evm=m_evm, aclrL=aclr_l, aclrR=aclr_r,
                              ibeLm=ibe_lm, ibeRm=ibe_rm)
        return ok, met

    k = -25.0
    for st in (5, 1, 0.2):
        passing = True
        while passing:
            k = k + st
            ok, _ = eval_at(k)
            passing = all(ok)
        k = k - st

    k_final = k
    ok, _ = eval_at(k_final + 0.2)
    names = ['EVM', 'ACLR', 'IBE']
    failname = '?'
    for i, good in enumerate(ok):
        if not good:
            failname = names[i]
            break

    _, met = eval_at(kref)
    return k_final, failname, met


def main():
    print(f'EVM limit {EVMLevel:.2f}%, ACLR limit {30 - aclrrelaxation:.0f} dB, '
          f'NRB={NRB}, CBW={CBW} MHz')
    print(f"{'model':<8} {'cfg(s,L)':<14} | {'k_final':<8} {'fail':<5} | "
          f"@k={kref:+.0f}: {'EVM%':>8} {'ACLR_L':>7} {'ACLR_R':>7} "
          f"{'IBE_Lm':>7} {'IBE_Rm':>7}")

    for model in ('full', 'memless'):
        for p, (s, L) in enumerate(pairs, start=1):
            mirr = NRB - s - L
            cfgs = [(s, L), (mirr, L)]
            if mirr == s:
                cfgs = cfgs[:1]
            rng = np.random.RandomState(1000 + p)      # 镜像对用同一组符号
            bits = np.round(rng.random_sample(12 * L * bps)).reshape(-1, 1)

            for (cs, cl) in cfgs:
                kf, failname, met = run_search(cs, cl, bits, model)
                print(f'{model:<8} ({cs:3d},{cl:3d})->{cs + cl - 1:3d} | '
                      f'{kf:8.1f} {failname:<5} | '
                      f'{met.evm:10.2f} {met.aclrL:7.2f} {met.aclrR:7.2f} '
                      f'{met.ibeLm:7.2f} {met.ibeRm:7.2f}')


if __name__ == '__main__':
    main()
