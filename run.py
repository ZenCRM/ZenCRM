import os
import sys
import subprocess
from pathlib import Path

# Ensure project venv is used when running run.py directly
_project_root = Path(__file__).resolve().parent
_venv_python = _project_root / 'venv' / ('Scripts' if os.name == 'nt' else 'bin') / ('python.exe' if os.name == 'nt' else 'python')

if __name__ == '__main__' and _venv_python.is_file() and Path(sys.executable).resolve() != _venv_python.resolve():
    sys.exit(subprocess.call([str(_venv_python)] + sys.argv))

from app import create_app

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 80))
    app.run(debug=True, host='0.0.0.0', port=port)

