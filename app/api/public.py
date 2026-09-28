"""Publiczne endpointy bez autoryzacji – widok ofert/dokumentów przez token."""
from flask import Blueprint, Response, abort
from ..models.offer import Offer
from ..models.document import Document

public_bp = Blueprint('public', __name__)


@public_bp.route('/offer/<token>', methods=['GET'])
def view_offer(token):
    offer = Offer.query.filter_by(public_token=token).first()
    if not offer:
        abort(404, description='Oferta nie znaleziona lub link wygasł')
    if not offer.rendered_html:
        abort(404, description='Oferta nie została jeszcze wygenerowana')
    html = _wrap_public_page(offer.rendered_html, offer.title,
                             f'Oferta {offer.number}')
    return Response(html, mimetype='text/html')


@public_bp.route('/document/<token>', methods=['GET'])
def view_document(token):
    doc = Document.query.filter_by(public_token=token).first()
    if not doc:
        abort(404, description='Dokument nie znaleziony lub link wygasł')
    if not doc.rendered_html:
        abort(404, description='Dokument nie został jeszcze wygenerowany')
    html = _wrap_public_page(doc.rendered_html, doc.title, doc.title)
    return Response(html, mimetype='text/html')


def _wrap_public_page(content, title, subtitle=''):
    """Opakowuje treść w stronę z przyciskiem 'Drukuj / Zapisz PDF'."""
    return f"""<!DOCTYPE html>
<html lang="pl"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
body {{ margin: 0; padding: 0; background: #f3f4f6; font-family: system-ui, sans-serif; }}
.bar {{
    position: sticky; top: 0; z-index: 10;
    background: #fff; padding: 12px 24px;
    border-bottom: 1px solid #e5e7eb;
    display: flex; justify-content: space-between; align-items: center;
    box-shadow: 0 1px 3px rgba(0,0,0,.05);
}}
.bar .meta {{ color: #6b7280; font-size: 14px; }}
.bar button {{
    background: #7e3af2; color: #fff; border: 0;
    padding: 8px 16px; border-radius: 8px; font-weight: 600;
    cursor: pointer; font-size: 14px;
}}
.bar button:hover {{ background: #6c2bd9; }}
.page {{
    max-width: 900px; margin: 24px auto;
    background: #fff; padding: 40px;
    border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,.06);
}}
@media print {{
    .bar {{ display: none !important; }}
    body {{ background: #fff; }}
    .page {{ box-shadow: none; margin: 0; padding: 0; max-width: 100%; }}
}}
</style>
</head><body>
<div class="bar">
    <div class="meta">{subtitle}</div>
    <button onclick="window.print()"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="vertical-align:middle;margin-right:6px" aria-hidden="true"><path d="M6 9V3h12v6 M6 18H3V9h18v9h-3 M6 14h12v7H6z"/></svg>Drukuj / Zapisz PDF</button>
</div>
<div class="page">{content}</div>
</body></html>"""
