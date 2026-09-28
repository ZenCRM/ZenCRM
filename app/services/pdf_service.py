"""Konwersja HTML → PDF. Próbuje WeasyPrint, potem xhtml2pdf."""
import os


def html_to_pdf(html_content, output_path):
    """Zapisuje PDF do output_path. Zwraca ścieżkę lub None przy błędzie."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Próba 1: WeasyPrint (lepszy CSS, ale wymaga GTK na Windows)
    try:
        from weasyprint import HTML
        HTML(string=html_content).write_pdf(output_path)
        return output_path
    except Exception as e:
        print(f'[pdf] WeasyPrint nie zadziałał: {e}')

    # Próba 2: xhtml2pdf (pure Python, działa wszędzie)
    try:
        from xhtml2pdf import pisa
        with open(output_path, 'wb') as f:
            result = pisa.CreatePDF(html_content, dest=f, encoding='utf-8')
        if result.err:
            print(f'[pdf] xhtml2pdf zwrócił błędy: {result.err}')
            return None
        return output_path
    except Exception as e:
        print(f'[pdf] xhtml2pdf nie zadziałał: {e}')

    return None
