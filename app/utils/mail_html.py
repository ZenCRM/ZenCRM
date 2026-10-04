"""Allow document formatting without active content or remote CSS."""
import re
from html import escape
from html.parser import HTMLParser
from urllib.parse import urlsplit
import tinycss2

TAGS = set('p div span br hr h1 h2 h3 h4 h5 h6 strong b em i u s small sub sup blockquote pre code ul ol li table thead tbody tfoot tr th td a img'.split())
VOID = {'br', 'hr', 'img'}
STYLES = set('color background background-color font-family font-size font-weight font-style text-decoration text-align line-height border border-top border-bottom border-left border-right border-collapse border-spacing border-radius padding padding-top padding-bottom padding-left padding-right margin margin-top margin-bottom margin-left margin-right width max-width min-width height max-height min-height vertical-align white-space overflow overflow-x overflow-y display letter-spacing word-spacing box-shadow opacity table-layout float clear object-fit'.split())


def safe_css_tokens(tokens):
    for token in tokens:
        if token.type in ('url', 'bad-url', 'error', 'at-keyword'):
            return False
        if token.type == 'function':
            if token.lower_name in ('url', 'expression') or not safe_css_tokens(token.arguments):
                return False
        if hasattr(token, 'content') and not safe_css_tokens(token.content):
            return False
    return True


def safe_style(value):
    rules = []
    for declaration in tinycss2.parse_declaration_list(value, skip_comments=True, skip_whitespace=True):
        if declaration.type == 'declaration' and declaration.lower_name in STYLES and safe_css_tokens(declaration.value):
            rules.append(declaration.lower_name + ':' + tinycss2.serialize(declaration.value) + ('!important' if declaration.important else ''))
    return ';'.join(rules)


def safe_stylesheet(value, depth=0):
    if depth > 15:
        return ''
    result = []
    for rule in tinycss2.parse_stylesheet(value, skip_comments=True, skip_whitespace=True):
        if rule.type == 'qualified-rule' and safe_css_tokens(rule.prelude):
            declarations = safe_style(tinycss2.serialize(rule.content))
            if declarations:
                result.append(tinycss2.serialize(rule.prelude) + '{' + declarations + '}')
        elif rule.type == 'at-rule' and rule.lower_at_keyword in ('media', 'supports') and rule.content and safe_css_tokens(rule.prelude):
            result.append('@' + rule.lower_at_keyword + ' ' + tinycss2.serialize(rule.prelude) + '{' + safe_stylesheet(tinycss2.serialize(rule.content), depth + 1) + '}')
    return ''.join(result).replace('<', '\\3c ')


class MailHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.result = []
        self.hidden = 0
        self.in_style = False
        self.css = []

    def handle_starttag(self, tag, attrs):
        if tag == 'style' and not self.hidden:
            self.in_style = True
            self.css = []
            return
        if tag in ('script', 'iframe', 'object', 'svg', 'math'):
            self.hidden += 1
            return
        if tag == 'body':
            tag = 'div'
        if self.hidden or tag not in TAGS:
            return
        clean = []
        for name, value in attrs:
            value = value or ''
            if name == 'style':
                value = safe_style(value)
            elif name in ('title', 'alt'):
                value = value[:500]
            elif name in ('class', 'id'):
                value = value[:500]
            elif name == 'bgcolor':
                if not re.fullmatch(r'#[0-9a-fA-F]{3,8}|[a-zA-Z]{1,30}', value):
                    continue
            elif name in ('colspan', 'rowspan', 'width', 'height', 'cellpadding', 'cellspacing', 'border', 'align', 'valign'):
                if not re.fullmatch(r'[a-zA-Z0-9% .-]{1,30}', value):
                    continue
            elif name == 'href' and tag == 'a':
                try:
                    scheme = urlsplit(value.strip()).scheme.lower()
                except ValueError:
                    continue
                if scheme not in ('https', 'http', 'mailto', 'tel'):
                    continue
            elif name == 'src' and tag == 'img':
                # Inline CID images stay as attachment metadata; no implicit fetch.
                if not (value.startswith('https://') or re.match(r'^data:image/(png|jpeg|gif|webp);base64,[a-zA-Z0-9+/=\s]+$', value)):
                    continue
            else:
                continue
            clean.append(f'{name}="{escape(value, quote=True)}"')
        if tag == 'a':
            clean.append('target="_blank" rel="noopener noreferrer"')
        self.result.append('<' + tag + (' ' + ' '.join(clean) if clean else '') + '>')

    def handle_endtag(self, tag):
        if tag == 'style' and self.in_style:
            self.result.append('<style>' + safe_stylesheet(''.join(self.css)) + '</style>')
            self.in_style = False
            return
        if tag == 'body':
            tag = 'div'
        if tag in ('script', 'iframe', 'object', 'svg', 'math'):
            self.hidden = max(0, self.hidden - 1)
            return
        if not self.hidden and tag in TAGS and tag not in VOID:
            self.result.append('</' + tag + '>')

    def handle_data(self, data):
        if self.in_style:
            self.css.append(data)
        elif not self.hidden:
            self.result.append(escape(data))


def sanitize_mail_html(value):
    parser = MailHTML()
    parser.feed(value or '')
    return ''.join(parser.result)


class SignatureHTML(HTMLParser):
    """Preserve email layout and CSS while removing executable HTML."""
    blocked = {'script', 'iframe', 'object', 'embed', 'form', 'button', 'input', 'textarea', 'select', 'base', 'link', 'meta', 'title'}

    def __init__(self, fragment=False):
        super().__init__(convert_charrefs=False)
        self.result, self.hidden = [], []
        self.fragment = fragment

    def handle_starttag(self, tag, attrs):
        if self.hidden:
            if tag == self.hidden[-1]:
                self.hidden.append(tag)
            return
        if tag in self.blocked:
            if tag not in {'embed', 'input', 'base', 'link', 'meta'}:
                self.hidden.append(tag)
            return
        if self.fragment and tag in {'html', 'head', 'body'}:
            return
        clean = []
        changed = False
        for name, value in attrs:
            if name.startswith('on') or name in {'srcdoc', 'formaction'}:
                changed = True
                continue
            if name in {'href', 'src', 'xlink:href', 'action', 'background'} and value:
                compact = re.sub(r'[\x00-\x20]', '', value)
                try:
                    scheme = urlsplit(compact).scheme.lower()
                except ValueError:
                    changed = True
                    continue
                if scheme not in {'', 'http', 'https', 'mailto', 'tel', 'cid'} and not (name == 'src' and re.match(r'^data:image/(png|jpeg|gif|webp);base64,', compact, re.I)):
                    changed = True
                    continue
            clean.append(name if value is None else name + '="' + escape(value, quote=True) + '"')
        self.result.append('<' + tag + (' ' + ' '.join(clean) if clean else '') + '>' if changed else self.get_starttag_text())

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if self.hidden:
            if tag == self.hidden[-1]:
                self.hidden.pop()
            return
        if tag not in self.blocked and not (self.fragment and tag in {'html', 'head', 'body'}):
            self.result.append('</' + tag + '>')

    def handle_data(self, data):
        if not self.hidden:
            self.result.append(data)

    def handle_entityref(self, name):
        if not self.hidden:
            self.result.append('&' + name + ';')

    def handle_charref(self, name):
        if not self.hidden:
            self.result.append('&#' + name + ';')

    def handle_comment(self, data):
        if not self.hidden:
            self.result.append('<!--' + data + '-->')

    def handle_decl(self, decl):
        if not self.hidden and not self.fragment:
            self.result.append('<!' + decl + '>')


def sanitize_signature_html(value, fragment=False):
    parser = SignatureHTML(fragment=fragment)
    parser.feed(value or '')
    parser.close()
    return ''.join(parser.result)
