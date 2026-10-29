"""任务 0：证明「按功能重组」只搬了家，没有改动任何数值。"""

import importlib.util
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).resolve().parent / 'fixtures'


def _load_fingerprint():
    spec = importlib.util.spec_from_file_location(
        'reorg_fingerprint', FIXTURES / 'reorg_fingerprint.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_reorg_is_bit_identical():
    fp = _load_fingerprint()
    before = json.loads((FIXTURES / 'reorg_before.json').read_text(encoding='utf-8'))
    after = {k: fp.digest(v) for k, v in fp.compute('new').items()}
    assert set(after) == set(before)
    changed = sorted(k for k in before if after[k] != before[k])
    assert changed == [], f'以下结果与搬迁前不一致: {changed}'


def test_no_python_files_at_repo_root():
    assert sorted(p.name for p in REPO.glob('*.py')) == []
