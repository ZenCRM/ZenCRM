"""Renderowanie szablonów ofert/dokumentów do HTML (Jinja2)."""
from ..utils.i18n import t
from datetime import datetime, timedelta
from jinja2.sandbox import SandboxedEnvironment
from ..models.client import Client
from ..models.template import Template


COMPANY = {
    "name": "ZenCRM Sp. z o.o.",
    "address": "ul. Przykładowa 1, 00-001 Warszawa",
    "nip": "0000000000",
    "email": "kontakt@zencrm.pl",
    "phone": "+48 22 000 00 00",
    "www": "zencrm.pl",
}


def _attr(obj, name, default=None):
    return getattr(obj, name, default)


def build_context(obj, entity_type="offer"):
    client = Client.query.get(obj.client_id) if obj.client_id else None
    data = obj.data or {}
    raw_total = _attr(obj, "total_amount", None)
    if raw_total:
        default_items = [{"name": obj.title, "qty": 1,
                          "price": float(raw_total), "total": float(raw_total)}]
    else:
        default_items = [{"name": obj.title, "qty": 1, "price": 0, "total": 0}]
    items = data.get("items") or default_items
    try:
        total = sum(float(i.get("total", 0)) for i in items)
    except (TypeError, ValueError):
        total = float(raw_total or 0)
    if not total and raw_total:
        total = float(raw_total)
    number = _attr(obj, "number", None) or ("DOC/" + str(obj.id))
    vu = _attr(obj, "valid_until", None)
    if vu and hasattr(vu, "strftime"):
        valid_until = vu.strftime("%Y-%m-%d")
    else:
        valid_until = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    ctx = {
        "offer": obj.to_dict() if entity_type == "offer" else None,
        "document": obj.to_dict() if entity_type == "document" else None,
        "client": client.to_dict() if client else {"name": "---"},
        "company": COMPANY,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "valid_until": valid_until,
        "items": items,
        "total_amount": total,
        "number": number,
        "title": obj.title,
        "description": data.get("description", ""),
        "custom": data.get("custom", {}) if isinstance(data.get("custom", {}), dict) else {},
        "type_fields": data.get("type_fields", {}) if isinstance(data.get("type_fields", {}), dict) else {},
    }
    for k, v in data.items():
        if k not in ctx:
            ctx[k] = v
    return ctx


def render_template_string(t, ctx):
    return SandboxedEnvironment(autoescape=True).from_string(t).render(**ctx)


def render_offer(offer):
    if not offer.template_id:
        raise ValueError("Oferta nie ma szablonu")
    tpl = Template.query.get(offer.template_id)
    if not tpl:
        raise ValueError("Szablon nie istnieje")
    html = render_template_string(tpl.content, build_context(offer, "offer"))
    offer.rendered_html = html
    return html


def render_document(doc):
    if not doc.template_id:
        raise ValueError("Dokument nie ma szablonu")
    tpl = Template.query.get(doc.template_id)
    if not tpl:
        raise ValueError("Szablon nie istnieje")
    html = render_template_string(tpl.content, build_context(doc, "document"))
    doc.rendered_html = html
    return html


def render_preview(template_str, entity_type="offer", variables=None, type_fields=None):
    class DC:
        id = 1
        name = t("Przykladowy Klient")
        email = "k@example.com"
        phone = "+48 22 111 22 33"
        company = t("Przykladowy")
        address = t("ul. Testowa 10")
        status = "active"
        def to_dict(self):
            return {"id": self.id, "name": self.name, "email": self.email,
                    "phone": self.phone, "company": self.company,
                    "address": self.address, "status": self.status}

    class DO:
        def __init__(self):
            self.id = 1
            self.number = "OF/2026/001"
            self.title = t("Przykladowa oferta")
            self.client_id = 1
            self.total_amount = 12500.0
            self.valid_until = datetime.now() + timedelta(days=30)
            self.data = {
                "items": [
                    {"name": t("Wdrozenie"), "qty": 1, "price": 8000, "total": 8000},
                    {"name": t("Szkolenie"), "qty": 2, "price": 1500, "total": 3000},
                    {"name": t("Wsparcie"), "qty": 1, "price": 1500, "total": 1500},
                ],
                "description": t("Dziekujemy za zainteresowanie oferta."),
            }
        def to_dict(self):
            return {"id": self.id, "number": self.number, "title": self.title,
                    "client_id": self.client_id,
                    "total_amount": self.total_amount,
                    "valid_until": self.valid_until.isoformat(),
                    "data": self.data}

    obj = DO()
    c = DC()
    d = obj.data
    total = sum(i["total"] for i in d["items"])
    ctx = {
        "offer": obj.to_dict() if entity_type == "offer" else None,
        "document": obj.to_dict() if entity_type == "document" else None,
        "client": c.to_dict(),
        "company": COMPANY,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "valid_until": obj.valid_until.strftime("%Y-%m-%d"),
        "items": d["items"],
        "total_amount": total,
        "number": obj.number,
        "title": obj.title,
        "description": d["description"],
        "custom": {v['name']: v['label'] for v in (variables or []) if isinstance(v, dict) and 'name' in v and 'label' in v},
        "type_fields": {f['key']: (f.get('options') or [f['label']])[0] for f in (type_fields or []) if isinstance(f, dict) and f.get('key')},
    }
    for k, v in d.items():
        if k not in ctx:
            ctx[k] = v
    return render_template_string(template_str, ctx)
