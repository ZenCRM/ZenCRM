"""Read-only OSV scan of pinned requirements; sends only package names/versions."""
import json
import sys
from importlib import metadata
from pathlib import Path
import requests

root = Path(__file__).resolve().parents[1]
packages = []
for line in (root / 'requirements.txt').read_text(encoding='utf-8').splitlines():
    line = line.strip()
    if line and not line.startswith('#') and '==' in line:
        name, version = line.split('==', 1)
        packages.append((name, version))

try:
    response = requests.post('https://api.osv.dev/v1/querybatch', json={'queries': [
        {'package': {'ecosystem': 'PyPI', 'name': name}, 'version': version}
        for name, version in packages]}, timeout=45)
    response.raise_for_status()
    matches = response.json()['results']
    if len(matches) != len(packages):
        raise ValueError('Incomplete OSV batch result')
except Exception as error:
    print(json.dumps({'osv_scan_completed': False, 'error_type': type(error).__name__}))
    sys.exit(1)

drift = []
for name, version in packages:
    try:
        installed = metadata.version(name)
    except metadata.PackageNotFoundError:
        installed = None
    if installed != version:
        drift.append({'package': name, 'declared': version, 'installed': installed})

print(json.dumps({'osv_scan_completed': True, 'declared_packages': len(packages),
    'vulnerabilities': [{'package': name, 'version': version, 'ids': [v['id'] for v in result.get('vulns', [])]}
                       for (name, version), result in zip(packages, matches) if result.get('vulns')],
    'local_dependency_drift': drift}, indent=2))
