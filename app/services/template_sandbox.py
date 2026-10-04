"""Bounded subprocess rendering for every offer, document and preview."""
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
from jinja2.exceptions import SecurityError

_slots = threading.BoundedSemaphore(1)
_worker = Path(__file__).with_name('template_sandbox_worker.py')
_message = 'Szablon jest nieprawidłowy lub przekracza limit czasu, pamięci albo rozmiaru.'


def run_template(content, context=None, validate=False):
    if not isinstance(content, str) or len(content) > 1_000_000:
        raise ValueError('Treść szablonu może mieć do 1 000 000 znaków.')
    payload = json.dumps({'content': content, 'context': context or {}, 'validate': validate},
                         ensure_ascii=False, allow_nan=False).encode('utf-8')
    if len(payload) > 4 * 1024 * 1024:
        raise ValueError('Dane szablonu przekraczają limit 4 MiB.')
    if not _slots.acquire(blocking=False):
        raise ValueError('Trwa renderowanie innego dokumentu. Spróbuj ponownie za chwilę.')
    process = None
    try:
        process = subprocess.Popen([sys.executable, '-I', str(_worker)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            env={key: os.environ[key] for key in ('SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP', 'LANG', 'LC_ALL') if key in os.environ},
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        try:
            output, _ = process.communicate(payload, timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
            raise ValueError(_message) from None
        if process.returncode:
            raise ValueError(_message)
        response = json.loads(output)
        if response.get('security_error'):
            raise SecurityError('Niedozwolona operacja w szablonie.')
        if response.get('error'):
            raise ValueError(_message)
        return response['result']
    finally:
        if process is not None:
            if process.poll() is None:
                process.kill()
            process.communicate()
        _slots.release()
