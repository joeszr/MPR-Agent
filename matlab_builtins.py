"""MATLAB 内建函数 / 工具箱函数的等价实现。

原 MPR 工程里没有对应的 .m 文件——这里放的是 MATLAB 自带、而 Python 没有现成等价物的
函数，供其余各 .py 调用：

    qammod      Communications Toolbox，方形 QAM，默认格雷映射、不归一化
    pwelch      Signal Processing Toolbox，Welch 功率谱，'psd' 标度
    interp1     线性插值，区间外返回 NaN
    factor      质因数分解
    polyval     多项式求值（幂次从高到低）
    comm_evm    comm.EVM，按参考信号平均功率归一化的 RMS EVM
    hann        Signal Processing Toolbox，对称汉宁窗
    fftshift / ifftshift   频谱中心顺序与自然顺序互转
    round       半数远离零取整（numpy.round 是"银行家舍入"，与之不同）

所有约定都按 MATLAB R2023b 实测对齐：列主序 reshape、1-based 下标、NaN 传播、
0.5 向上取整等，保证与 .m 版本逐点一致。
"""

from __future__ import annotations

import numpy as np

__all__ = [
    "qammod", "pwelch", "interp1", "factor", "polyval", "comm_evm",
    "hann", "hamming", "blackman", "boxcar",
    "fftshift", "ifftshift", "round_", "var", "rms", "deg2rad", "rad2deg",
    "log10", "reshape_F",
]


# ---------------------------------------------------------------- 频谱顺序
def fftshift(x, axis=0):
    """MATLAB ``fftshift(x, dim)``，dim 用 0 基的轴号。"""
    return np.fft.fftshift(x, axes=axis)


def ifftshift(x, axis=0):
    """MATLAB ``ifftshift(x, dim)``，dim 用 0 基的轴号。"""
    return np.fft.ifftshift(x, axes=axis)


# ---------------------------------------------------------------- 窗函数
def hann(n):
    """MATLAB ``hann(n)``，对称汉宁窗，返回列向量。"""
    return np.hanning(int(n)).reshape(-1, 1)


def hamming(n):
    """MATLAB ``hamming(n)``，对称海明窗，返回列向量。"""
    return np.hamming(int(n)).reshape(-1, 1)


def blackman(n):
    """MATLAB ``blackman(n)``，对称布莱克曼窗，返回列向量。"""
    return np.blackman(int(n)).reshape(-1, 1)


def boxcar(n):
    """MATLAB ``boxcar(n)``，矩形窗，返回列向量。"""
    return np.ones((int(n), 1))


# ---------------------------------------------------------------- 数值
def round_(x):
    """MATLAB ``round``：0.5 远离零取整。"""
    x = np.asarray(x, dtype=float)
    return np.floor(np.abs(x) + 0.5) * np.sign(x)


def var(x):
    """MATLAB ``var``：无偏方差。"""
    a = np.asarray(x, dtype=complex).ravel()
    if a.size < 2:
        return np.nan
    return float(np.var(a, ddof=1))


def rms(x):
    """MATLAB ``rms``。"""
    a = np.asarray(x).ravel()
    return float(np.sqrt(np.mean(np.abs(a) ** 2)))


def deg2rad(deg):
    """MATLAB ``deg2rad``。"""
    return np.deg2rad(deg)


def rad2deg(rad):
    """MATLAB ``rad2deg``。"""
    return np.rad2deg(rad)


def polyval(p, x):
    """MATLAB ``polyval``（Horner，最高次在前）。"""
    return np.polyval(np.asarray(p), x)


def log10(x):
    """MATLAB ``log10``：0 得 -Inf、负数得 NaN，而且不告警。"""
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.log10(x)


def reshape_F(a, shape):
    """MATLAB ``reshape`` —— 列主序填充。"""
    return np.asarray(a).reshape(tuple(int(s) for s in shape), order="F")


def factor(n):
    """MATLAB ``factor``：质因数分解，返回一维整型数组。"""
    n = int(round(n))
    if n < 1:
        raise ValueError("factor: N 必须是正整数")
    out = []
    d = 2
    while d * d <= n:
        while n % d == 0:
            out.append(d)
            n //= d
        d += 1 if d == 2 else 2
    if n > 1:
        out.append(n)
    return np.asarray(out if out else [1], dtype=int)


# ---------------------------------------------------------------- QAM 调制
def _qam_level(value, nbits):
    """MATLAB ``qammod`` 方形星座每个维度的电平编号（实测反推）。

    对一维电平号 b：

        h(b) = h_{n-1}(b)                        , b <  2^(n-1)
        h(b) = (2^n - 1) - h_{n-1}(b - 2^(n-1))  , b >= 2^(n-1)
    """
    if nbits == 1:
        return value
    half = 1 << (nbits - 1)
    if value < half:
        return _qam_level(value, nbits - 1)
    return ((1 << nbits) - 1) - _qam_level(value - half, nbits - 1)


def qammod(bits, M, input_type="bit"):
    """MATLAB ``qammod``（方形 QAM，默认格雷映射，不归一化）。

    输入 ``input_type='bit'`` 时是 0/1 序列（每组 log2(M) 个比特，第一个是 MSB）；
    ``'integer'`` 时是符号索引。输出 (N,1) 复数，标度与 MATLAB 相同——
    256QAM 最外点是 15+15j。
    """
    nbits = int(round(np.log2(M)))
    if 1 << nbits != M:
        raise ValueError("M 必须是 2 的幂")
    if nbits % 2:
        raise ValueError("方形 QAM 要求 M 是 4 的幂")

    if input_type.lower() == "bit":
        b = np.asarray(bits).ravel()
        if b.size % nbits:
            raise ValueError("比特数必须是 log2(M) 的整数倍")
        b = b.reshape(-1, nbits)
        idx = np.zeros(b.shape[0], dtype=np.int64)
        for k in range(nbits):
            idx = idx * 2 + (b[:, k].astype(np.int64) & 1)
    elif input_type.lower() == "integer":
        idx = np.asarray(bits).ravel().astype(np.int64)
    else:
        raise ValueError("input_type 只能是 'bit' 或 'integer'")

    n = nbits // 2
    if np.any(idx < 0) or np.any(idx >= M):
        raise ValueError("符号索引超出 M 的范围")

    i_idx = idx >> n
    q_idx = idx & ((1 << n) - 1)
    lv = np.array([_qam_level(int(v), n) for v in range(1 << n)], dtype=float)
    max_lv = (1 << n) - 1
    amp_i = 2.0 * lv[i_idx] - max_lv
    amp_q = max_lv - 2.0 * lv[q_idx]
    return (amp_i + 1j * amp_q).reshape(-1, 1)


# ---------------------------------------------------------------- 功率谱
def pwelch(x, window, noverlap, nfft, fs):
    """MATLAB ``pwelch``（显式窗、显式重叠、复信号双边谱、默认 'psd' 标度）。

        PSD(f) = mean( |fft(seg .* win, nfft)|^2 ) / (fs * sum(win^2))

    返回 ``(psd, f)``，``psd`` 形状 (nfft,1)，与 MATLAB 一致。
    """
    x = np.asarray(x, dtype=complex).ravel()
    win = np.asarray(window, dtype=float).ravel()
    fs = float(fs)
    nwin = win.size
    step = nwin - int(noverlap)
    if step <= 0:
        raise ValueError("noverlap 必须小于窗长")

    n_seg = int(np.floor((x.size - int(noverlap)) / step))
    if n_seg < 1:
        raise ValueError("信号长度不足一个窗段")

    acc = np.zeros(int(nfft), dtype=float)
    for s in range(n_seg):
        seg = x[s * step:s * step + nwin]
        spec = np.fft.fft(seg * win, int(nfft))
        acc += np.abs(spec) ** 2
    acc /= n_seg
    acc /= fs * np.sum(win ** 2)
    freq = np.arange(int(nfft), dtype=float) * (fs / float(nfft))
    return acc.reshape(-1, 1), freq.reshape(-1, 1)


# ---------------------------------------------------------------- 插值
def interp1(x, v, xi):
    """MATLAB ``interp1(x, v, xi)``（默认 'linear'）。

    采样区间外按 MATLAB 返回 NaN（不外插）；复数按实部、虚部分别插值。
    """
    x = np.asarray(x, dtype=float).ravel()
    v = np.asarray(v).ravel()
    xi = np.asarray(xi, dtype=float).ravel()
    if x.size != v.size:
        raise ValueError("x 与 v 长度必须相同")

    complex_in = np.iscomplexobj(v)
    out = np.full(xi.shape, np.nan + 1j * np.nan if complex_in else np.nan,
                  dtype=complex if complex_in else float)
    inside = (xi >= x.min()) & (xi <= x.max())
    if np.any(inside):
        xin = xi[inside]
        re = np.interp(xin, x, np.real(v))
        if complex_in:
            im = np.interp(xin, x, np.imag(v))
            out[inside] = re + 1j * im
        else:
            out[inside] = re
    return out


# ---------------------------------------------------------------- EVM
def comm_evm(reference, received):
    """MATLAB ``comm.EVM``（默认配置：按参考信号平均功率归一化）。

        rmsEVM[%] = 100 * sqrt( mean(|rx - ref|^2) / mean(|ref|^2) )
    """
    ref = np.asarray(reference).ravel()
    rx = np.asarray(received).ravel()
    if ref.size != rx.size:
        raise ValueError("参考信号与接收信号长度必须相同")
    err = rx - ref
    return float(100.0 * np.sqrt(np.mean(np.abs(err) ** 2) /
                                 np.mean(np.abs(ref) ** 2)))
