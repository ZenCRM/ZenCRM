"""Bezpieczne przypisywanie danych JSON do modeli SQLAlchemy."""
from datetime import datetime, date
from decimal import Decimal, InvalidOperation


# Pola, których NIGDY nie nadpisujemy z requestu
SKIP_FIELDS = frozenset({
    'id',
    'created_at',
    'updated_at',
    'password_hash',
    'public_token',
    'pdf_path',
    'rendered_html',
    'deleted_at',
})


def apply_payload(obj, data):
    """Przypisuje dane z JSON do istniejącego obiektu modelu,
    konwertując typy (str → date/datetime/Decimal/int/float/bool)."""
    if not data:
        return
    columns = {c.name: c for c in obj.__table__.columns}
    for key, value in data.items():
        if key in SKIP_FIELDS or key not in columns:
            continue
        coerced = _coerce(value, columns[key].type)
        setattr(obj, key, coerced)


def build_model(Model, data):
    """Tworzy nową instancję modelu z bezpieczną konwersją typów."""
    obj = Model()
    apply_payload(obj, data)
    return obj


# ─────────── Konwersje ───────────

def _coerce(value, col_type):
    if value is None or value == '':
        return None
    try:
        py_type = col_type.python_type
    except NotImplementedError:
        return value

    if py_type is datetime:
        return _to_datetime(value)
    if py_type is date:
        return _to_date(value)
    if py_type is Decimal:
        return _to_decimal(value)
    if py_type is int:
        return _to_int(value)
    if py_type is float:
        return _to_float(value)
    if py_type is bool:
        return _to_bool(value)
    return value


def _to_datetime(v):
    if isinstance(v, datetime):
        return v
    if isinstance(v, date):
        return datetime.combine(v, datetime.min.time())
    if isinstance(v, str):
        s = v.strip().replace('Z', '+00:00')
        try:
            return datetime.fromisoformat(s)
        except ValueError:
            return None
    return None


def _to_date(v):
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    if isinstance(v, str):
        try:
            return date.fromisoformat(v.strip()[:10])
        except ValueError:
            return None
    return None


def _to_decimal(v):
    try:
        return Decimal(str(v))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _to_int(v):
    try:
        return int(v)
    except (ValueError, TypeError):
        return None


def _to_float(v):
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def _to_bool(v):
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() in ('1', 'true', 'yes', 'tak', 'y', 't')
    return bool(v)
