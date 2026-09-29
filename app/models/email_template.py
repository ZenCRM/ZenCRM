from datetime import datetime
from ..extensions import db


DEFAULT_TEMPLATES = [
    {
        'key': 'client_ticket_created',
        'name': 'Klient: Potwierdzenie utworzenia zgłoszenia (ticketa)',
        'category': 'client',
        'subject': 'Potwierdzenie przyjęcia zgłoszenia [{{ticket_number}}] - {{ticket_title}}',
        'body_html': (
            '<div style="font-family: Arial, sans-serif; font-size: 14px; line-height: 1.6; color: #1f2937;">'
            '<h2 style="color: #007fce; margin-top: 0;">Twoje zgłoszenie zostało zarejestrowane</h2>'
            '<p>Dzień dobry <strong>{{client_name}}</strong>,</p>'
            '<p>Dziękujemy za kontakt. Twoje zgłoszenie zostało pomyślnie zarejestrowane w naszym systemie obsługi klienta.</p>'
            '<div style="background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px; margin: 16px 0;">'
            '<p style="margin: 0 0 8px 0;"><strong>Numer zgłoszenia:</strong> {{ticket_number}}</p>'
            '<p style="margin: 0 0 8px 0;"><strong>Temat:</strong> {{ticket_title}}</p>'
            '<p style="margin: 0 0 8px 0;"><strong>Kategoria:</strong> {{ticket_category}}</p>'
            '<p style="margin: 0;"><strong>Status:</strong> Nowe</p>'
            '</div>'
            '<p>Nasz konsultant wkrótce zapozna się ze sprawą i udzieli odpowiedzi. Możesz w każdej chwili sprawdzić status i historię zgłoszenia:</p>'
            '<p><a href="{{ticket_url}}" style="display: inline-block; background: #007fce; color: #ffffff; padding: 10px 20px; text-decoration: none; border-radius: 6px; font-weight: bold;">Zobacz zgłoszenie online &rarr;</a></p>'
            '<p style="margin-top: 24px; color: #6b7280; font-size: 12px;">Wiadomość wygenerowana automatycznie przez {{company_name}}.</p>'
            '</div>'
        ),
        'variables': '{{client_name}}, {{ticket_number}}, {{ticket_title}}, {{ticket_category}}, {{ticket_url}}, {{company_name}}'
    },
    {
        'key': 'client_ticket_reply',
        'name': 'Klient: Nowa odpowiedź konsultanta na ticket',
        'category': 'client',
        'subject': 'Nowa odpowiedź w zgłoszeniu [{{ticket_number}}] - {{ticket_title}}',
        'body_html': (
            '<div style="font-family: Arial, sans-serif; font-size: 14px; line-height: 1.6; color: #1f2937;">'
            '<h2 style="color: #007fce; margin-top: 0;">Nowa wiadomość w Twoim zgłoszeniu</h2>'
            '<p>Dzień dobry <strong>{{client_name}}</strong>,</p>'
            '<p>Nasz konsultant (<strong>{{agent_name}}</strong>) udzielił odpowiedzi na zgłoszenie <strong>[{{ticket_number}}] {{ticket_title}}</strong>:</p>'
            '<div style="background: #f3f4f6; border-left: 4px solid #007fce; padding: 14px 18px; border-radius: 4px; margin: 16px 0; font-size: 14px;">'
            '{{reply_content}}'
            '</div>'
            '<p>Możesz odpowiedzieć bezpośrednio lub przejść do panelu zgłoszenia:</p>'
            '<p><a href="{{ticket_url}}" style="display: inline-block; background: #007fce; color: #ffffff; padding: 10px 20px; text-decoration: none; border-radius: 6px; font-weight: bold;">Otwórz zgłoszenie i odpowiedz &rarr;</a></p>'
            '<p style="margin-top: 24px; color: #6b7280; font-size: 12px;">Pozdrawiamy,<br>Zespół {{company_name}}</p>'
            '</div>'
        ),
        'variables': '{{client_name}}, {{agent_name}}, {{ticket_number}}, {{ticket_title}}, {{reply_content}}, {{ticket_url}}, {{company_name}}'
    },
    {
        'key': 'client_portal_access',
        'name': 'Klient: Dane dostępowe do Portalu Klienta',
        'category': 'client',
        'subject': 'Twoje dane dostępowe do Portalu Klienta {{company_name}}',
        'body_html': (
            '<div style="font-family: Arial, sans-serif; font-size: 14px; line-height: 1.6; color: #1f2937;">'
            '<h2 style="color: #007fce; margin-top: 0;">Witaj w Portalu Klienta {{company_name}}!</h2>'
            '<p>Dzień dobry <strong>{{client_name}}</strong>,</p>'
            '<p>Utworzyliśmy dla Ciebie dostęp do dedykowanego Portalu Klienta. W portalu możesz w prosty sposób zgłaszać awarie, zamawiać usługi oraz śledzić postępy projektów.</p>'
            '<div style="background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px; margin: 16px 0;">'
            '<p style="margin: 0 0 8px 0;"><strong>Adres logowania:</strong> <a href="{{portal_url}}">{{portal_url}}</a></p>'
            '<p style="margin: 0 0 8px 0;"><strong>Login / E-mail:</strong> <code style="background: #e5e7eb; padding: 2px 6px; border-radius: 4px;">{{login_email}}</code></p>'
            '<p style="margin: 0;"><strong>Hasło tymczasowe:</strong> <code style="background: #e5e7eb; padding: 2px 6px; border-radius: 4px; font-weight: bold;">{{password}}</code></p>'
            '</div>'
            '<p><a href="{{portal_url}}" style="display: inline-block; background: #007fce; color: #ffffff; padding: 10px 20px; text-decoration: none; border-radius: 6px; font-weight: bold;">Przejdź do portalu &rarr;</a></p>'
            '<p style="margin-top: 16px; font-size: 13px; color: #4b5563;">Zalecamy zmianę hasła na własne po pierwszym zalogowaniu w zakładce ustawień profilu.</p>'
            '<p style="margin-top: 24px; color: #6b7280; font-size: 12px;">W razie pytań zapraszamy do kontaktu z {{company_email}}.</p>'
            '</div>'
        ),
        'variables': '{{client_name}}, {{portal_url}}, {{login_email}}, {{password}}, {{company_name}}, {{company_email}}'
    },
    {
        'key': 'employee_new_ticket',
        'name': 'Pracownik: Nowy ticket w systemie / przypisany',
        'category': 'employee',
        'subject': 'Nowy ticket [{{ticket_number}}] - {{ticket_title}}',
        'body_html': (
            '<div style="font-family: Arial, sans-serif; font-size: 14px; line-height: 1.6; color: #1f2937;">'
            '<h2 style="color: #007fce; margin-top: 0;">Nowe zgłoszenie do obsługi</h2>'
            '<p>Cześć <strong>{{employee_name}}</strong>,</p>'
            '<p>W systemie pojawiło się nowe zgłoszenie od klienta <strong>{{client_name}}</strong> ({{client_email}}):</p>'
            '<div style="background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px; margin: 16px 0;">'
            '<p style="margin: 0 0 8px 0;"><strong>Ticket:</strong> [{{ticket_number}}] {{ticket_title}}</p>'
            '<p style="margin: 0 0 8px 0;"><strong>Priorytet:</strong> {{ticket_priority}} | <strong>Kategoria:</strong> {{ticket_category}}</p>'
            '<p style="margin: 0;"><strong>Treść zgłoszenia:</strong></p>'
            '<div style="margin-top: 8px; font-style: italic; color: #4b5563;">{{ticket_description}}</div>'
            '</div>'
            '<p><a href="{{crm_ticket_url}}" style="display: inline-block; background: #007fce; color: #ffffff; padding: 10px 20px; text-decoration: none; border-radius: 6px; font-weight: bold;">Obsłuż ticket w CRM &rarr;</a></p>'
            '<p style="margin-top: 24px; color: #6b7280; font-size: 12px;">Powiadomienie z systemu ZenCRM.</p>'
            '</div>'
        ),
        'variables': '{{employee_name}}, {{ticket_number}}, {{ticket_title}}, {{client_name}}, {{client_email}}, {{ticket_priority}}, {{ticket_category}}, {{ticket_description}}, {{crm_ticket_url}}, {{company_name}}'
    },
    {
        'key': 'employee_ticket_reply',
        'name': 'Pracownik: Klient odpowiedział w tickecie',
        'category': 'employee',
        'subject': 'Odpowiedź klienta w tickecie [{{ticket_number}}] - {{ticket_title}}',
        'body_html': (
            '<div style="font-family: Arial, sans-serif; font-size: 14px; line-height: 1.6; color: #1f2937;">'
            '<h2 style="color: #007fce; margin-top: 0;">Nowa odpowiedź od klienta</h2>'
            '<p>Cześć <strong>{{employee_name}}</strong>,</p>'
            '<p>Klient <strong>{{client_name}}</strong> dodał nową odpowiedź w zgłoszeniu <strong>[{{ticket_number}}] {{ticket_title}}</strong>:</p>'
            '<div style="background: #f3f4f6; border-left: 4px solid #10b981; padding: 14px 18px; border-radius: 4px; margin: 16px 0;">'
            '{{reply_content}}'
            '</div>'
            '<p><a href="{{crm_ticket_url}}" style="display: inline-block; background: #007fce; color: #ffffff; padding: 10px 20px; text-decoration: none; border-radius: 6px; font-weight: bold;">Otwórz ticket w CRM &rarr;</a></p>'
            '<p style="margin-top: 24px; color: #6b7280; font-size: 12px;">Powiadomienie z systemu ZenCRM.</p>'
            '</div>'
        ),
        'variables': '{{employee_name}}, {{client_name}}, {{ticket_number}}, {{ticket_title}}, {{reply_content}}, {{crm_ticket_url}}, {{company_name}}'
    },
    {
        'key': 'employee_new_task',
        'name': 'Pracownik: Przypisano nowe zadanie',
        'category': 'employee',
        'subject': 'Przypisano nowe zadanie: {{task_title}}',
        'body_html': (
            '<div style="font-family: Arial, sans-serif; font-size: 14px; line-height: 1.6; color: #1f2937;">'
            '<h2 style="color: #007fce; margin-top: 0;">Nowe zadanie przypisane do Ciebie</h2>'
            '<p>Cześć <strong>{{employee_name}}</strong>,</p>'
            '<p>Zostało do Ciebie przypisane nowe zadanie w systemie CRM:</p>'
            '<div style="background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px; margin: 16px 0;">'
            '<p style="margin: 0 0 8px 0; font-size: 16px; font-weight: bold; color: #111827;">{{task_title}}</p>'
            '<p style="margin: 0 0 8px 0;"><strong>Termin:</strong> {{task_due_date}} | <strong>Priorytet:</strong> {{task_priority}}</p>'
            '<p style="margin: 0 0 8px 0;"><strong>Powiązany klient:</strong> {{client_name}}</p>'
            '<div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid #e5e7eb; color: #4b5563;">{{task_description}}</div>'
            '</div>'
            '<p><a href="{{crm_task_url}}" style="display: inline-block; background: #007fce; color: #ffffff; padding: 10px 20px; text-decoration: none; border-radius: 6px; font-weight: bold;">Zobacz zadanie w CRM &rarr;</a></p>'
            '<p style="margin-top: 24px; color: #6b7280; font-size: 12px;">Powiadomienie z systemu ZenCRM.</p>'
            '</div>'
        ),
        'variables': '{{employee_name}}, {{task_title}}, {{task_due_date}}, {{task_priority}}, {{client_name}}, {{task_description}}, {{crm_task_url}}, {{company_name}}'
    },
    {
        'key': 'employee_client_assigned',
        'name': 'Pracownik: Przypisanie nowego klienta',
        'category': 'employee',
        'subject': 'Zostałeś wyznaczony jako opiekun klienta: {{client_name}}',
        'body_html': (
            '<div style="font-family: Arial, sans-serif; font-size: 14px; line-height: 1.6; color: #1f2937;">'
            '<h2 style="color: #007fce; margin-top: 0;">Przypisano nowego klienta</h2>'
            '<p>Cześć <strong>{{employee_name}}</strong>,</p>'
            '<p>Zostałeś wyznaczony jako opiekun klienta <strong>{{client_name}}</strong> w systemie CRM.</p>'
            '<div style="background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px; margin: 16px 0;">'
            '<p style="margin: 0 0 8px 0;"><strong>Klient:</strong> {{client_name}}</p>'
            '<p style="margin: 0 0 8px 0;"><strong>E-mail:</strong> {{client_email}}</p>'
            '<p style="margin: 0;"><strong>Telefon:</strong> {{client_phone}}</p>'
            '</div>'
            '<p><a href="{{crm_client_url}}" style="display: inline-block; background: #007fce; color: #ffffff; padding: 10px 20px; text-decoration: none; border-radius: 6px; font-weight: bold;">Otwórz kartę klienta &rarr;</a></p>'
            '<p style="margin-top: 24px; color: #6b7280; font-size: 12px;">Powiadomienie z systemu ZenCRM.</p>'
            '</div>'
        ),
        'variables': '{{employee_name}}, {{client_name}}, {{client_email}}, {{client_phone}}, {{crm_client_url}}, {{company_name}}'
    },
    {
        'key': 'password_reset',
        'name': 'Bezpieczeństwo: Reset / przypomnienie hasła',
        'category': 'auth',
        'subject': 'Instrukcja resetowania hasła w {{company_name}}',
        'body_html': (
            '<div style="font-family: Arial, sans-serif; font-size: 14px; line-height: 1.6; color: #1f2937;">'
            '<h2 style="color: #007fce; margin-top: 0;">Reset hasła do konta</h2>'
            '<p>Dzień dobry <strong>{{user_name}}</strong>,</p>'
            '<p>Otrzymaliśmy zgłoszenie prośby o zresetowanie hasła do Twojego konta w systemie <strong>{{company_name}}</strong>.</p>'
            '<div style="background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px; margin: 16px 0;">'
            '<p style="margin: 0 0 8px 0;">Twoje nowe hasło tymczasowe:</p>'
            '<p style="margin: 0; font-size: 18px; font-weight: bold; letter-spacing: 1px; color: #111827; background: #e5e7eb; display: inline-block; padding: 6px 14px; border-radius: 6px; font-family: monospace;">{{temp_password}}</p>'
            '</div>'
            '<p>Zaloguj się pod poniższym adresem i niezwłocznie zmień hasło w ustawieniach profilu:</p>'
            '<p><a href="{{login_url}}" style="display: inline-block; background: #007fce; color: #ffffff; padding: 10px 20px; text-decoration: none; border-radius: 6px; font-weight: bold;">Zaloguj się do CRM &rarr;</a></p>'
            '<p style="margin-top: 16px; font-size: 12px; color: #ef4444;">Jeśli to nie Ty zgłaszałeś próbę resetu hasła, skontaktuj się natychmiast z administratorem systemu ({{admin_email}}).</p>'
            '<p style="margin-top: 24px; color: #6b7280; font-size: 12px;">Pozdrawiamy,<br>Zespół {{company_name}}</p>'
            '</div>'
        ),
        'variables': '{{user_name}}, {{temp_password}}, {{login_url}}, {{admin_email}}, {{company_name}}'
    }
]


class EmailTemplate(db.Model):
    __tablename__ = 'email_templates'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(60), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(40), default='client')
    subject = db.Column(db.String(255), nullable=False)
    body_html = db.Column(db.Text, nullable=False)
    variables = db.Column(db.Text, default='')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        from ..utils.i18n import default_email
        return {
            'id': self.id,
            'key': self.key,
            'name': default_email(self.key, 'name', self.name),
            'category': self.category,
            'subject': self.subject,
            'body_html': self.body_html,
            'variables': [v.strip() for v in (self.variables or '').split(',') if v.strip()],
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def get_by_key(cls, key):
        return cls.query.filter_by(key=key).first()

    @classmethod
    def seed_defaults(cls):
        added = 0
        for item in DEFAULT_TEMPLATES:
            tpl = cls.query.filter_by(key=item['key']).first()
            if not tpl:
                tpl = cls(
                    key=item['key'],
                    name=item['name'],
                    category=item['category'],
                    subject=item['subject'],
                    body_html=item['body_html'],
                    variables=item.get('variables', '')
                )
                db.session.add(tpl)
                added += 1
        if added:
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()
        return added
