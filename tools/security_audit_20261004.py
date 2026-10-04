"""Offline regression runner for all five findings from the mail audit."""
import sys
import unittest
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
sys.path.insert(0, str(root / 'tests'))

if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromName('test_security_mail_fixes')
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(not result.wasSuccessful())
