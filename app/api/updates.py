"""Read-only GitHub release information for the settings screen."""
import json
import os
import re
import subprocess
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from ..utils.deletion import is_admin

updates_bp = Blueprint('updates', __name__)
REPO = 'ZenCRM/ZenCRM'
API = f'https://api.github.com/repos/{REPO}/releases?per_page=10'
ROOT = Path(__file__).resolve().parents[2]


def installed_version():
    configured = os.environ.get('ZENCRM_VERSION', '').strip()
    if configured:
        return configured
    version_file = ROOT / 'VERSION'
    if version_file.is_file():
        return version_file.read_text(encoding='utf-8').strip() or None
    try:
        result = subprocess.run(['git', 'describe', '--tags', '--always', '--dirty'],
                                cwd=ROOT, capture_output=True, text=True, timeout=2, check=True)
        return result.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def newer_release(current, latest):
    if not current or not latest:
        return None
    pattern = r'^v?(\d+)\.(\d+)\.(\d+)(?:\.(\d+))?$'
    a, b = re.fullmatch(pattern, current), re.fullmatch(pattern, latest)
    if not a or not b:
        return None
    return tuple(int(part or 0) for part in b.groups()) > tuple(int(part or 0) for part in a.groups())


@updates_bp.route('/releases', methods=['GET'])
@jwt_required()
def releases():
    if not is_admin():
        return jsonify({'error': 'Wymagane uprawnienia administratora'}), 403
    request = Request(API, headers={'Accept': 'application/vnd.github+json',
                                    'User-Agent': 'ZenCRM-release-checker'})
    try:
        with urlopen(request, timeout=6) as response:
            payload = json.load(response)
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as error:
        return jsonify({'error': 'Nie można pobrać wydań z GitHub.', 'details': str(error)}), 502
    if not isinstance(payload, list):
        return jsonify({'error': 'Nieprawidłowa odpowiedź GitHub.'}), 502
    items = [{'tag': item.get('tag_name'), 'name': item.get('name') or item.get('tag_name'),
              'published_at': item.get('published_at'), 'body': (item.get('body') or '')[:10000],
              'url': item.get('html_url'), 'prerelease': bool(item.get('prerelease'))}
             for item in payload if isinstance(item, dict) and not item.get('draft')]
    current = installed_version()
    latest = next((item for item in items if not item['prerelease']), None)
    return jsonify({'installed': current, 'latest': latest, 'releases': items,
                    'update_available': newer_release(current, latest['tag']) if latest else None,
                    'repository': f'https://github.com/{REPO}'})
