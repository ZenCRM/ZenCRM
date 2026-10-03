"""Documents domain helpers. The API caller owns authorization and transactions."""
import secrets
from ..extensions import db
from ..models.template import Template
from ..models.document_type import DocumentType
from ..utils.i18n import t


def validate_relations(doc):
    """Optional associations must belong to the document's selected client."""
    from ..models.lead import Lead
    from ..models.service import Service
    for field, model, label in (('lead_id', Lead, 'Lead'), ('service_id', Service, 'Usługa')):
        value = getattr(doc, field)
        if value is None:
            continue
        related = db.session.get(model, value)
        if not related:
            raise ValueError(t('{label} nie istnieje', {'label': t(label)}))
        if doc.client_id and related.client_id != doc.client_id:
            raise ValueError(t('{label} nie należy do wybranego klienta', {'label': t(label)}))


def ensure_token(doc):
    if not doc.public_token:
        doc.public_token = secrets.token_urlsafe(32)
    return doc.public_token


def ensure_template(doc):
    if doc.template_id:
        tpl = db.session.get(Template, doc.template_id)
        if not tpl or tpl.type != 'document' or (tpl.document_type_key and tpl.document_type_key != doc.type):
            raise ValueError('Szablon nie pasuje do typu dokumentu')
        return True
    tpl = Template.query.filter_by(type='document', document_type_key=doc.type, is_active=True).first()
    if not tpl:
        tpl = Template.query.filter_by(type='document', document_type_key=None, is_active=True).first()
    if not tpl:
        return False
    doc.template_id = tpl.id
    return True


def validate_type_fields(doc):
    kind = db.session.get(DocumentType, doc.type or 'other')
    if not kind:
        raise ValueError('Typ dokumentu nie istnieje')
    values = (doc.data or {}).get('type_fields', {})
    if not isinstance(values, dict):
        raise ValueError('Nieprawidłowe pola typu dokumentu')
    from datetime import date
    from decimal import Decimal, InvalidOperation
    for field in kind.fields or []:
        value = values.get(field['key'], '')
        if field.get('required') and (value == '' or value is None):
            raise ValueError('Wymagane pole: ' + field['label'])
        if value in ('', None):
            continue
        try:
            if field['kind'] == 'number' and not Decimal(str(value).replace(',', '.')).is_finite():
                raise ValueError()
            if field['kind'] == 'date':
                date.fromisoformat(str(value))
            if field['kind'] == 'boolean' and not isinstance(value, bool):
                raise ValueError()
            if field['kind'] == 'select' and value not in field['options']:
                raise ValueError()
            if len(str(value)) > 10000:
                raise ValueError()
        except (ValueError, InvalidOperation, TypeError):
            raise ValueError('Nieprawidłowa wartość pola: ' + field['label'])
