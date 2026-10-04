"""Keep slow mailbox requests from occupying every HTTP thread."""
from functools import wraps
import threading
from flask import jsonify

_slots = threading.BoundedSemaphore(2)


def mail_operation(func):
    @wraps(func)
    def limited(*args, **kwargs):
        if not _slots.acquire(blocking=False):
            return jsonify(error='Serwer obsługuje inne operacje poczty. Spróbuj ponownie za chwilę.'), 429
        try:
            return func(*args, **kwargs)
        finally:
            _slots.release()
    return limited
