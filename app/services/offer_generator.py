from jinja2 import Template
from weasyprint import HTML
from datetime import datetime, timedelta
import os

class OfferGenerator:
    def __init__(self, template_content, client_data, offer_data):
        self.template_content = template_content
        self.client_data = client_data
        self.offer_data = offer_data

    def generate_html(self):
        jinja_template = Template(self.template_content)
        context = {
            'client': self.client_data,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'valid_until': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
            **self.offer_data
        }
        return jinja_template.render(**context)

    def generate_pdf(self, html_content, output_path):
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        HTML(string=html_content).write_pdf(output_path)
        return output_path
