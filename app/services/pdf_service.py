"""Konwersja HTML → PDF. Próbuje WeasyPrint, potem xhtml2pdf."""
import os
import tempfile
from urllib.parse import urlsplit


def _data_only_link(uri, relative):
    if urlsplit(uri).scheme.lower() != 'data':
        raise ValueError('External resources are not allowed in PDFs')
    return uri


def html_to_pdf(html_content, output_path):
    """Zapisuje PDF do output_path. Zwraca ścieżkę lub None przy błędzie."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fd, temporary_path = tempfile.mkstemp(suffix='.pdf', dir=os.path.dirname(output_path))
    os.close(fd)

    try:
        # WeasyPrint first; the fallback is for systems without its native libraries.
        try:
            from weasyprint import HTML
            from weasyprint.urls import URLFetcher
            fetcher = URLFetcher(allowed_protocols=('data',), allow_redirects=False)
            HTML(string=html_content, url_fetcher=fetcher).write_pdf(temporary_path)
            os.replace(temporary_path, output_path)
            return output_path
        except Exception as e:
            print(f'[pdf] WeasyPrint nie zadziałał: {e}')

        try:
            from xhtml2pdf import pisa
            with open(temporary_path, 'wb') as f:
                result = pisa.CreatePDF(html_content, dest=f, encoding='utf-8',
                                        link_callback=_data_only_link)
            if not result.err:
                os.replace(temporary_path, output_path)
                return output_path
            print(f'[pdf] xhtml2pdf zwrócił błędy: {result.err}')
        except Exception as e:
            print(f'[pdf] xhtml2pdf nie zadziałał: {e}')
        return None
    finally:
        if os.path.exists(temporary_path):
            os.remove(temporary_path)
