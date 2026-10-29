"""apply_pa_model —— 功放模型统一入口（apply_pa_model.m 的 Python 版）。

一个分发器：把回退量 k（dB）换算成幅度比例 10^(k/20)，再调用具体模型。

k 是功率回退量（dB）；每个分支都用 10**(k/20) 作幅度缩放，因为作用对象是电压幅度。

各分支对应的 .m：见下面每个 case 的注释。原工程里缺少实现的模型（AM.m、PM.m、
AM_oppo.m、PM_oppo.m、pa_GaN_28GHz.m、HZW_MB_*.m、HZW_LB_*.m、AM_fit.m、PM_fit.m）
在 MATLAB 里同样会报 "Undefined function"，这里抛 NotImplementedError 并说明缺哪个文件。
"""

from __future__ import annotations

import numpy as np

from HZW_HB_am import HZW_HB_am
from HZW_HB_pm import HZW_HB_pm
from pa_model_memory_38803 import pa_model_memory_38803
from pa_model_memoryless import pa_model_memoryless
from pa_model_mp import pa_model_mp
from pa_model_mp_K7 import pa_model_mp_K7

_MISSING = {
    "AMPM": "AM.m / PM.m",
    "AMPM_OPPO": "AM_oppo.m / PM_oppo.m",
    "MEMORYLESS_GAN": "pa_GaN_28GHz.m",
    "MEMORYLESS_GAN_ADJ": "pa_GaN_28GHz.m",
    "MEMORYLESS_GAN_ADJ2": "pa_GaN_28GHz.m",
    "AMPM_FIT": "AM_fit.m / PM_fit.m",
    "HZW_MB": "HZW_MB_am.m / HZW_MB_pm.m",
    "HZW_LB": "HZW_LB_am.m / HZW_LB_pm.m",
}


def _raise_missing(kind):
    raise NotImplementedError(
        f"功放模型 '{kind}' 没有实现：它的 MATLAB 源文件（{_MISSING[kind]}）"
        f"不在本工程里，原 MATLAB 代码同样无法运行该分支。")


def apply_pa_model(signal_in, k, PA_MODEL_TYPE):
    """``output = apply_pa_model(signal_in, k, PA_MODEL_TYPE)``。"""
    kind = str(PA_MODEL_TYPE).upper()

    if kind == "AMPM":                                  # AM.m / PM.m
        _raise_missing(kind)
    elif kind == "AMPM_OPPO":                           # AM_oppo.m / PM_oppo.m
        _raise_missing(kind)
    elif kind == "MEMORYLESS":                          # pa_model_memoryless.m
        signal_input = np.asarray(signal_in) * 10 ** (k / 20)
        return pa_model_memoryless(signal_input)
    elif kind == "MEMORYLESS_GAN":                      # pa_GaN_28GHz.m
        _raise_missing(kind)
    elif kind == "MEMORYLESS_GAN_ADJ":                  # pa_GaN_28GHz.m + 增益搬移
        _raise_missing(kind)
    elif kind == "MEMORYLESS_GAN_ADJ2":
        _raise_missing(kind)
    elif kind == "MP":                                  # pa_model_mp.m
        signal_input = np.asarray(signal_in) * 10 ** (k / 20)
        return pa_model_mp(signal_input)
    elif kind == "MP1":                                 # pa_model_mp_K7.m * sqrt(20)
        signal_input = np.asarray(signal_in) * 10 ** (k / 20)
        return pa_model_mp_K7(signal_input) * np.sqrt(20)
    elif kind == "MEMORY":                              # pa_model_memory_38803.m
        signal_input = np.asarray(signal_in) * 10 ** (k / 20)
        return pa_model_memory_38803(signal_input)
    elif kind == "AMPM_FIT":                            # AM_fit.m / PM_fit.m
        _raise_missing(kind)
    elif kind == "HZW_HB":                              # HZW_HB_am.m / HZW_HB_pm.m
        scale_factor = 10 ** (k / 20)
        r_linear = np.abs(signal_in) * scale_factor
        A_out = HZW_HB_am(r_linear)
        phi_out = HZW_HB_pm(r_linear)
        return A_out * np.exp(1j * (np.angle(signal_in) + phi_out))
    elif kind == "HZW_MB":                              # HZW_MB_am.m / HZW_MB_pm.m
        _raise_missing(kind)
    elif kind == "HZW_LB":                              # HZW_LB_am.m / HZW_LB_pm.m
        _raise_missing(kind)
    else:
        raise ValueError(f"不支持的功放模型类型: {PA_MODEL_TYPE}")
