"""Offers domain helpers. The API caller owns authorization and transactions."""
import secrets
from ..models.template import Template


def ensure_token(offer):
    if not offer.public_token:
        offer.public_token = secrets.token_urlsafe(32)
    return offer.public_token


def ensure_template(offer):
    if offer.template_id:
        return True
    tpl = Template.query.filter_by(type='offer', is_active=True).first()
    if not tpl:
        return False
    offer.template_id = tpl.id
    return True
