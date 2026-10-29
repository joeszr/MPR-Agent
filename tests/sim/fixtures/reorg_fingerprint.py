"""搬迁对照指纹：在重组前后各算一次，两次结果必须逐位相同。

用法（在仓库根目录运行）：
    搬迁前：python tests/sim/fixtures/reorg_fingerprint.py --layout old --root . --out tests/sim/fixtures/reorg_before.json
    搬迁后：由 tests/sim/test_reorg_equivalence.py 自动调用 compute('new')
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import sys
from pathlib import Path

import numpy as np

# 两种布局下同一个模块的导入名
MODULES = {
    'cp':            ('CP_ofdm_mainV6',  'rf_copilot.sim.legacy.cp_ofdm_v6'),
    'dft':           ('DFT_ofdm_mainV2', 'rf_copilot.sim.legacy.dft_ofdm_v2'),
    'pa':            ('apply_pa_model',  'rf_copilot.sim.pa'),
    'pa_huawei':     ('plotPA_HUAWEI',   'rf_copilot.plots.pa_huawei'),
    'pa_memory':     ('plotPA_memory',   'rf_copilot.plots.pa_memory'),
    'pa_memoryless': ('plotPA_memoryless', 'rf_copilot.plots.pa_memoryless'),
    'pa_mp_k7':      ('plotPA_mp_K7',    'rf_copilot.plots.pa_mp_k7'),
    'mpr_map':       ('figure_plot',     'rf_copilot.plots.mpr_map'),
}
PA_TYPES = ('HZW_HB', 'MP1', 'MP', 'MEMORYLESS', 'MEMORY')


def _load(layout: str, key: str):
    old, new = MODULES[key]
    return importlib.import_module(old if layout == 'old' else new)


def _put(out: dict, prefix: str, value) -> None:
    """把元组 / 字典 / 数组统一展开成 {名字: ndarray}。"""
    if isinstance(value, dict):
        for k, v in value.items():
            out[f'{prefix}_{k}'] = np.asarray(v)
    elif isinstance(value, tuple):
        for i, v in enumerate(value):
            out[f'{prefix}_{i}'] = np.asarray(v)
    else:
        out[prefix] = np.asarray(value)


def digest(a: np.ndarray) -> str:
    """dtype + shape + 原始字节的 SHA-256；摘要相同 ⇔ 数组逐位相同。"""
    a = np.ascontiguousarray(a)
    h = hashlib.sha256(f'{a.dtype.str}|{a.shape}|'.encode())
    h.update(a.tobytes())
    return h.hexdigest()


def compute(layout: str, root: Path | None = None) -> dict[str, np.ndarray]:
    if layout == 'old':
        root = Path(root or '.').resolve()
        for p in (root / 'plotfigure', root / 'PAmodel', root):
            sys.path.insert(0, str(p))
    out: dict[str, np.ndarray] = {}

    cp = _load(layout, 'cp')
    cp.MONTE_CARLO = 1
    _put(out, 'cp_a', cp.simulate_config(1, 0, 0, np.random.RandomState(42)))
    _put(out, 'cp_b', cp.simulate_config(12, 120, 131, np.random.RandomState(42)))

    dft = _load(layout, 'dft')
    dft.MONTE_CARLO = 1
    _put(out, 'dft_a', dft.simulate_config(12, 0, 11, np.random.RandomState(42)))

    pa = _load(layout, 'pa')
    rng = np.random.RandomState(0)
    sig = rng.standard_normal((1024, 1)) + 1j * rng.standard_normal((1024, 1))
    sig = sig / np.max(np.abs(sig))
    for kind in PA_TYPES:
        try:
            _put(out, f'pa_{kind}', pa.apply_pa_model(sig, -10, kind))
        except NotImplementedError:
            print(f'跳过未实现的功放类型: {kind}')

    for key in ('pa_huawei', 'pa_memory', 'pa_memoryless', 'pa_mp_k7'):
        _put(out, f'plot_{key}', _load(layout, key).compute())
    _put(out, 'mpr_map', _load(layout, 'mpr_map').build_map(np.arange(55.0), 10))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--layout', choices=['old', 'new'], required=True)
    ap.add_argument('--root', default='.')
    ap.add_argument('--out', required=True)
    args = ap.parse_args(argv)
    result = {k: digest(v) for k, v in compute(args.layout, Path(args.root)).items()}
    Path(args.out).write_text(json.dumps(result, indent=2, sort_keys=True), encoding='utf-8')
    print(f'已写入 {args.out}，共 {len(result)} 项')
    return 0


if __name__ == '__main__':
    sys.exit(main())
