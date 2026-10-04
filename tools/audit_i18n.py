"""Static catalog coverage audit; run from the repository root."""
import html
import json
import pathlib
import re
import ast
from html.parser import HTMLParser

ROOT = pathlib.Path(__file__).resolve().parents[1]
CALL = re.compile(r'\bt\(\s*([\x22\x27])((?:\\.|(?!\1).)*?)\1')


def catalog(lang):
    text = (ROOT / f'frontend/locales/{lang}.js').read_text(encoding='utf-8')
    return json.loads(text[text.index('{', text.index('window.ZenLocales.')):text.rfind('}') + 1])


def literal(text):
    return re.sub(r'\\([\x22\x27\\])', r'\1', text).replace('\\n', '\n')


def calls():
    for path in (ROOT / 'frontend').rglob('*'):
        if path.suffix not in ('.js', '.html') or {'vendor', 'locales'} & set(path.parts):
            continue
        text = html.unescape(path.read_text(encoding='utf-8'))
        for match in CALL.finditer(text):
            yield path.relative_to(ROOT).as_posix(), text[:match.start()].count('\n') + 1, literal(match[2])
        for match in re.finditer(r'\bdata-i18n(?:-(?:placeholder|title|aria-label|alt))?="([^"]+)"', path.read_text(encoding='utf-8')):
            yield path.relative_to(ROOT).as_posix(), text[:match.start()].count('\n') + 1, html.unescape(match[1])


def backend_messages():
    """Collect literal response and validation messages, not business data."""
    for path in (ROOT / 'app').rglob('*.py'):
        tree = ast.parse(path.read_text(encoding='utf-8-sig'))
        values = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Dict):
                values.extend(value for key, value in zip(node.keys, node.values)
                              if isinstance(key, ast.Constant) and key.value in ('error', 'message'))
            if isinstance(node, ast.Call):
                name = getattr(node.func, 'id', '')
                if name in ('ValueError', 'ValidationError', 't') and node.args:
                    values.append(node.args[0])
                if name == 'jsonify':
                    values.extend(k.value for k in node.keywords if k.arg in ('error', 'message'))
                if name == 'abort':
                    values.extend(k.value for k in node.keywords if k.arg == 'description')
        for value in values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                yield path.relative_to(ROOT).as_posix(), value.lineno, value.value


def untranslated_feature_copy():
    """Check new feature views for copy that bypasses the translation catalog."""
    technical = {'CRM', 'E-Mail', 'HTML / Jinja2', 'STARTTLS', 'SSL', 'B', 'I', 'U',
                 'imap.example.com', 'smtp.example.com', 'termin_realizacji'}
    void_tags = {'input', 'br', 'hr', 'img', 'meta', 'link', 'path'}

    class Copy(HTMLParser):
        def __init__(self, path):
            super().__init__(convert_charrefs=True)
            self.path, self.stack, self.missing = path, [], []

        def report(self, text):
            text = text.strip()
            if text not in technical and re.search('[A-Za-ząćęłńóśźżĄĆĘŁŃÓŚŹŻ]', text):
                self.missing.append((self.path.relative_to(ROOT).as_posix(), self.getpos()[0], text))

        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            for name, value in attrs.items():
                if value and name in ('placeholder', 'aria-label', 'title'):
                    self.report(value)
                elif value and (name.startswith(':') or name == 'x-text'):
                    remaining = CALL.sub('', value)
                    for match in re.finditer(r"'([^']*)'|\"([^\"]*)\"", remaining):
                        text = match[1] or match[2] or ''
                        if re.search('[ąćęłńóśźżĄĆĘŁŃÓŚŹŻ]', text) or text in ('Co ', 'Sprawdzono ', ' z ', 'Do', 'DW', 'UDW'):
                            self.report(text)
            if tag not in void_tags:
                self.stack.append((tag, attrs))

        def handle_endtag(self, tag):
            for i in range(len(self.stack) - 1, -1, -1):
                if self.stack[i][0] == tag:
                    del self.stack[i:]
                    break

        def handle_data(self, data):
            if any(tag in ('script', 'style', 'pre', 'code') or 'x-text' in attrs or 'x-html' in attrs
                   for tag, attrs in self.stack):
                return
            if data.strip().startswith('% include '):
                return
            self.report(data)

    for name in ('mailboxes.html', 'template-editor.html', 'templates.html'):
        path = ROOT / 'frontend/views' / name
        parser = Copy(path)
        parser.feed(path.read_text(encoding='utf-8'))
        yield from parser.missing


if __name__ == '__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    pl, en = catalog('pl'), catalog('en')
    missing = [(p, n, k) for p, n, k in [*calls(), *backend_messages()] if k not in pl or k not in en]
    for p, n, k in missing:
        print(f'{p}:{n}: {k}')
    untranslated = list(untranslated_feature_copy())
    for p, n, k in untranslated:
        print(f'{p}:{n}: untranslated UI: {k}')
    print(f'PL: {len(pl)}, EN: {len(en)}, missing calls: {len(missing)}, untranslated feature UI: {len(untranslated)}')
    sys.exit(bool(missing or untranslated or pl.keys() != en.keys()))
