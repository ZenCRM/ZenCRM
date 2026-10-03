"""HTTP responses for untrusted rendered document content."""
from flask import Response

RENDERED_HTML_CSP = "sandbox; default-src 'none'; img-src data: https:; style-src 'unsafe-inline'; font-src data:"


def rendered_html_response(html):
    response = Response(html, mimetype='text/html')
    response.headers['Content-Security-Policy'] = RENDERED_HTML_CSP
    return response
