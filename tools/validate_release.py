"""Check a pristine release checkout before running bounded regression fixtures."""
import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
names = set()
for line in (ROOT / 'FILES.sha256').read_text(encoding='utf-8').splitlines():
    digest, name = line.split('  ', 1)
    path = ROOT / name
    assert name not in names and path.resolve().is_relative_to(ROOT), name
    names.add(name)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, name
assert 'README.md' in names and 'NOTICE' in names
assert 'RUSSELL PHILIP SMITHSON' in (ROOT / 'LICENSE').read_text()
assert 'Apache License' in (ROOT / 'LICENSE').read_text()
assert (ROOT / 'VERSION').read_text().strip() == '1.0.1'
node = shutil.which('node')
if not node:
    raise SystemExit('Node.js is required for JavaScript syntax checks')
for name in sorted(names):
    path = ROOT / name
    if path.suffix == '.py':
        ast.parse(path.read_text(encoding='utf-8'), filename=name)
    elif path.suffix == '.json':
        json.loads(path.read_text(encoding='utf-8'))
    elif path.suffix == '.js':
        subprocess.run([node, '--check', str(path)], check=True, timeout=30)
print('RELEASE_INVENTORY_AND_SYNTAX_PASS', len(names), flush=True)
subprocess.run([sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'tests', '-v'], check=True, timeout=240)
