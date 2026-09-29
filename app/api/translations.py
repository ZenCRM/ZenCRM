import re
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from ..extensions import db
from ..models.translation import TranslationLanguage, TranslationEntry
from ..utils.deletion import is_admin, current_user
from ..utils.i18n import browser_catalogs, catalog

translations_bp = Blueprint('translations', __name__)
CODE = re.compile(r'^[a-z]{2,3}(?:-[a-zA-Z]{2,4})?$')


@translations_bp.route('/catalog', methods=['GET'])
@jwt_required()
def user_catalog():
    user = current_user()
    if not user or not user.is_active:
        return jsonify({'error': 'Brak dostępu'}), 403
    response = jsonify(browser_catalogs())
    response.headers['Cache-Control'] = 'no-store'
    return response


@translations_bp.route('', methods=['GET'])
@jwt_required()
def list_translations():
    if not is_admin():
        return jsonify({'error': 'Wymagane uprawnienia administratora'}), 403
    return jsonify(browser_catalogs())


@translations_bp.route('/languages', methods=['POST'])
@jwt_required()
def create_language():
    if not is_admin():
        return jsonify({'error': 'Wymagane uprawnienia administratora'}), 403
    data = request.get_json(silent=True) or {}
    code = str(data.get('code', '')).strip().lower()
    name = str(data.get('name', '')).strip()
    base = data.get('base_locale', 'pl')
    if not CODE.fullmatch(code) or code in ('pl', 'en') or TranslationLanguage.query.filter_by(code=code).first():
        return jsonify({'error': 'Podaj unikalny kod języka, np. de lub fr-CA.'}), 400
    if not name or len(name) > 80 or base not in ('pl', 'en'):
        return jsonify({'error': 'Podaj nazwę i język bazowy (polski lub angielski).'}), 400
    db.session.add(TranslationLanguage(code=code, name=name, base_locale=base))
    db.session.commit()
    return jsonify(browser_catalogs()), 201


@translations_bp.route('/<locale>/entries', methods=['PUT'])
@jwt_required()
def save_entries(locale):
    if not is_admin():
        return jsonify({'error': 'Wymagane uprawnienia administratora'}), 403
    if locale not in ('pl', 'en') and not TranslationLanguage.query.filter_by(code=locale).first():
        return jsonify({'error': 'Nieznany język.'}), 404
    data = request.get_json(silent=True) or {}
    entries = data.get('entries')
    if not isinstance(entries, dict) or len(entries) > 5000:
        return jsonify({'error': 'Nieprawidłowa lista tłumaczeń.'}), 400
    source_keys = set(catalog('pl')) | set(catalog('en'))
    for key, value in entries.items():
        if key not in source_keys or not isinstance(value, str) or len(value) > 10000:
            return jsonify({'error': 'Nieprawidłowe pole tłumaczenia.'}), 400
        row = TranslationEntry.query.filter_by(locale=locale, key=key).first()
        if value.strip():
            if row:
                row.value = value
            else:
                db.session.add(TranslationEntry(locale=locale, key=key, value=value))
        elif row:
            db.session.delete(row)
    db.session.commit()
    return jsonify(browser_catalogs())
