"""Static catalog coverage audit; run from the repository root."""
import html
import json
import pathlib
import re
import ast

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


if __name__ == '__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    pl, en = catalog('pl'), catalog('en')
    missing = [(p, n, k) for p, n, k in [*calls(), *backend_messages()] if k not in pl or k not in en]
    for p, n, k in missing:
        print(f'{p}:{n}: {k}')
    print(f'PL: {len(pl)}, EN: {len(en)}, missing calls: {len(missing)}')
    sys.exit(bool(missing or pl.keys() != en.keys()))
