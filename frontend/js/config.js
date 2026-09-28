/* ═══════════════════════════════════════════════
   ZenCRM - konfiguracja
   ═══════════════════════════════════════════════ */
window.ZenConfig = {

    FIELDS: {
        clients: [
            { key: 'name', label: window.ZenI18n.t('Nazwa'), type: 'text', required: true },
            { key: 'email', label: window.ZenI18n.t('Email'), type: 'email' },
            { key: 'phone', label: window.ZenI18n.t('Telefon'), type: 'text' },
            { key: 'company', label: window.ZenI18n.t('Firma'), type: 'text' },
            { key: 'address', label: window.ZenI18n.t('Adres'), type: 'textarea' },
                        { key: 'status', label: window.ZenI18n.t('Status'), type: 'select', options: [
                { value: 'active',   label: window.ZenI18n.t('Aktywny') },
                { value: 'inactive', label: window.ZenI18n.t('Nieaktywny') },
                { value: 'prospect', label: window.ZenI18n.t('Prospect') },
            ]},
            { key: 'notes', label: window.ZenI18n.t('Dodatkowe informacje'), type: 'textarea' },
        ],

        leads: [
            { key: 'title', label: window.ZenI18n.t('Tytul'), type: 'text', required: true },
            { key: 'client_id', label: window.ZenI18n.t('Klient'), type: 'client-select' },
                        { key: 'value', label: window.ZenI18n.t('Wartosc (zl)'), type: 'number' },
            { key: 'stage', label: window.ZenI18n.t('Etap'), type: 'select', options: [
                { value: 'new',         label: window.ZenI18n.t('Nowy') },
                { value: 'contacted',   label: window.ZenI18n.t('Kontakt') },
                { value: 'qualified',   label: window.ZenI18n.t('Kwalifikowany') },
                { value: 'proposal',    label: window.ZenI18n.t('Oferta') },
                { value: 'negotiation', label: window.ZenI18n.t('Negocjacje') },
                { value: 'won',         label: window.ZenI18n.t('Wygrany') },
                { value: 'lost',        label: window.ZenI18n.t('Przegrany') },
            ]},
            { key: 'source', label: window.ZenI18n.t('Zrodlo'), type: 'text' },
            { key: 'probability', label: window.ZenI18n.t('Prawdopodobieństwo'), type: 'range' },
            { key: 'expected_close_date', label: window.ZenI18n.t('Przewidywane zamkniecie'), type: 'date' },
            { key: 'notes', label: window.ZenI18n.t('Notatki'), type: 'textarea' },
        ],

        tasks: [
            { key: 'title', label: window.ZenI18n.t('Tytul'), type: 'text', required: true },
            { key: 'description', label: window.ZenI18n.t('Opis'), type: 'textarea' },
            { key: 'status', label: window.ZenI18n.t('Status'), type: 'select', options: [
                { value: 'todo',        label: window.ZenI18n.t('Do zrobienia') },
                { value: 'in_progress', label: window.ZenI18n.t('W toku') },
                { value: 'done',        label: window.ZenI18n.t('Zrobione') },
            ]},
            { key: 'priority', label: window.ZenI18n.t('Priorytet'), type: 'select', options: [
                { value: 'low',    label: window.ZenI18n.t('Niski') },
                { value: 'medium', label: window.ZenI18n.t('Sredni') },
                { value: 'high',   label: window.ZenI18n.t('Wysoki') },
            ]},
            { key: 'due_date', label: window.ZenI18n.t('Termin'), type: 'datetime-local' },
            { key: 'reminder_offset', label: 'Moje przypomnienie (dodaj lub zmień)', type: 'select', options: [
                {value:'',label:'Bez zmian'}, {value:'off',label:'Wyłącz przypomnienie'},
                {value:'0',label:'W terminie zadania'}, {value:'15',label:'15 minut przed terminem'},
                {value:'60',label:'Godzinę przed terminem'}, {value:'1440',label:'24 godziny przed terminem'},
            ]},
            { key: 'client_id', label: window.ZenI18n.t('Klient'), type: 'client-select' },
            { key: 'project_id', label: window.ZenI18n.t('Projekt (opcjonalnie)'), type: 'project-select' },
            { key: 'lead_id', label: window.ZenI18n.t('Lead (opcjonalnie)'), type: 'document-relation' },
            { key: 'service_id', label: window.ZenI18n.t('Usługa (opcjonalnie)'), type: 'document-relation' },
        ],

        meetings: [
            { key: 'title', label: window.ZenI18n.t('Tytul'), type: 'text', required: true },
            { key: 'description', label: window.ZenI18n.t('Opis'), type: 'textarea' },
            { key: 'start_time', label: window.ZenI18n.t('Poczatek'), type: 'datetime-local', required: true },
            { key: 'end_time', label: window.ZenI18n.t('Koniec'), type: 'datetime-local', required: true },
            { key: 'location', label: window.ZenI18n.t('Miejsce'), type: 'text' },
            { key: 'client_id', label: window.ZenI18n.t('Klient'), type: 'client-select' },
            { key: 'lead_id', label: window.ZenI18n.t('Lead (opcjonalnie)'), type: 'lead-select' },
            { key: 'status', label: window.ZenI18n.t('Status'), type: 'select', options: [
                { value: 'scheduled', label: window.ZenI18n.t('Zaplanowane') },
                { value: 'completed', label: window.ZenI18n.t('Odbyto sie') },
                { value: 'cancelled', label: window.ZenI18n.t('Odwolane') },
            ]},
        ],

        serviceCatalog: [
            { key: 'name', label: window.ZenI18n.t('Nazwa uslugi'), type: 'text', required: true },
            { key: 'description', label: window.ZenI18n.t('Krotki opis'), type: 'textarea' },
            { key: 'billing_type', label: window.ZenI18n.t('Typ rozliczenia'), type: 'select', options: [
                { value: 'subscription', label: window.ZenI18n.t('Abonament (cykliczne)') },
                { value: 'one_time',     label: window.ZenI18n.t('Jednorazowe') },
            ]},
            { key: 'term_type', label: window.ZenI18n.t('Okres'), type: 'select', options: [
                { value: 'indefinite', label: window.ZenI18n.t('Na czas nieokreslony') },
                { value: 'fixed',      label: window.ZenI18n.t('Na czas okreslony') },
            ]},
            { key: 'default_billing_cycle', label: window.ZenI18n.t('Cykl'), type: 'select', options: [
                { value: 'monthly',  label: window.ZenI18n.t('Miesieczny') },
                { value: 'yearly',   label: window.ZenI18n.t('Roczny') },
                { value: 'one_time', label: window.ZenI18n.t('Jednorazowy') },
            ]},
            { key: 'default_price', label: window.ZenI18n.t('Domyslna cena (zl)'), type: 'number' },
            { key: 'is_price_fixed', label: window.ZenI18n.t('Cena stala?'), type: 'select', options: [
                { value: 'true',  label: window.ZenI18n.t('Tak - cena stala') },
                { value: 'false', label: window.ZenI18n.t('Nie - do ustalenia') },
            ]},
            { key: 'content', label: 'Wzory / warunki / informacje', type: 'textarea' },
            { key: 'is_active', label: window.ZenI18n.t('Aktywna'), type: 'select', options: [
                { value: 'true',  label: window.ZenI18n.t('Tak') },
                { value: 'false', label: window.ZenI18n.t('Nie') },
            ]},
        ],

        services: [
            { key: 'name', label: window.ZenI18n.t('Nazwa'), type: 'text', required: true },
            { key: 'client_id', label: window.ZenI18n.t('Klient'), type: 'client-select' },
            { key: 'catalog_id', label: window.ZenI18n.t('Z katalogu'), type: 'catalog-select' },
            { key: 'assignee_ids', label: window.ZenI18n.t('Opiekunowie usługi'), type: 'multi-user-select' },
            { key: 'billing_type', label: window.ZenI18n.t('Typ'), type: 'select', options: [
                { value: 'subscription', label: window.ZenI18n.t('Abonament') },
                { value: 'one_time',     label: window.ZenI18n.t('Jednorazowe') },
            ]},
            { key: 'term_type', label: window.ZenI18n.t('Okres'), type: 'select', options: [
                { value: 'indefinite', label: window.ZenI18n.t('Nieokreslony') },
                { value: 'fixed',      label: window.ZenI18n.t('Okreslony') },
            ]},
            { key: 'billing_cycle', label: window.ZenI18n.t('Cykl'), type: 'select', options: [
                { value: 'monthly',  label: window.ZenI18n.t('Miesieczny') },
                { value: 'yearly',   label: window.ZenI18n.t('Roczny') },
                { value: 'one_time', label: window.ZenI18n.t('Jednorazowy') },
            ]},
            { key: 'price', label: window.ZenI18n.t('Kwota (zl)'), type: 'number' },
            { key: 'start_date', label: window.ZenI18n.t('Data rozpoczecia'), type: 'date' },
            { key: 'end_date', label: window.ZenI18n.t('Data zakonczenia'), type: 'date' },
            { key: 'status', label: window.ZenI18n.t('Status uslugi'), type: 'select', options: [
                { value: 'exemplary',   label: window.ZenI18n.t('Wzorowa') },
                { value: 'good',        label: window.ZenI18n.t('Dobra') },
                { value: 'problematic', label: window.ZenI18n.t('Problematyczna') },
                { value: 'critical',    label: window.ZenI18n.t('Krytyczna') },
            ]},
            { key: 'risk_level', label: window.ZenI18n.t('Ryzyko wypowiedzenia (1-10)'), type: 'number' },
            { key: 'notes', label: window.ZenI18n.t('Notatki'), type: 'textarea' },
        ],

        offers: [
            { key: 'number', label: window.ZenI18n.t('Numer'), type: 'text', required: true },
            { key: 'title', label: window.ZenI18n.t('Tytul'), type: 'text', required: true },
            { key: 'client_id', label: window.ZenI18n.t('Klient'), type: 'client-select', required: true },
            { key: 'template_id', label: window.ZenI18n.t('Szablon oferty'), type: 'template-select' },
            { key: 'total_amount', label: window.ZenI18n.t('Kwota (zl)'), type: 'number' },
            { key: 'status', label: window.ZenI18n.t('Status'), type: 'select', options: [
                { value: 'draft',    label: window.ZenI18n.t('Szkic') },
                { value: 'sent',     label: window.ZenI18n.t('Wyslana') },
                { value: 'accepted', label: window.ZenI18n.t('Zaakceptowana') },
                { value: 'rejected', label: window.ZenI18n.t('Odrzucona') },
            ]},
            { key: 'valid_until', label: window.ZenI18n.t('Wazna do'), type: 'date' },
        ],

        documents: [
            { key: 'title', label: window.ZenI18n.t('Tytul'), type: 'text', required: true },
            { key: 'type', label: window.ZenI18n.t('Typ'), type: 'select', options: [
                { value: 'contract', label: window.ZenI18n.t('Umowa') },
                { value: 'invoice',  label: window.ZenI18n.t('Faktura') },
                { value: 'report',   label: window.ZenI18n.t('Raport') },
                { value: 'other',    label: window.ZenI18n.t('Inne') },
            ]},
            { key: 'client_id', label: window.ZenI18n.t('Klient'), type: 'client-select' },
            { key: 'lead_id', label: window.ZenI18n.t('Lead (opcjonalnie)'), type: 'document-relation' },
            { key: 'service_id', label: window.ZenI18n.t('Usługa (opcjonalnie)'), type: 'document-relation' },
            { key: 'template_id', label: window.ZenI18n.t('Szablon dokumentu'), type: 'template-select' },
            { key: 'content', label: window.ZenI18n.t('Tresc'), type: 'textarea' },
            { key: 'status', label: window.ZenI18n.t('Status'), type: 'select', options: [
                { value: 'draft', label: window.ZenI18n.t('Szkic') },
                { value: 'final', label: window.ZenI18n.t('Finalny') },
            ]},
        ],

        templates: [
            { key: 'name', label: window.ZenI18n.t('Nazwa'), type: 'text', required: true },
            { key: 'type', label: window.ZenI18n.t('Typ'), type: 'select', required: true, options: [
                { value: 'offer',    label: window.ZenI18n.t('Oferta') },
                { value: 'document', label: window.ZenI18n.t('Dokument') },
            ]},
            { key: 'content', label: 'Tresc (HTML/Jinja2)', type: 'textarea', required: true },
        ],

        contacts: [
            { key: 'first_name', label: window.ZenI18n.t('Imie'), type: 'text', required: true },
            { key: 'last_name', label: window.ZenI18n.t('Nazwisko'), type: 'text' },
            { key: 'is_primary', label: window.ZenI18n.t('Główny kontakt'), type: 'checkbox' },
            { key: 'email', label: window.ZenI18n.t('Email'), type: 'email' },
            { key: 'phone', label: window.ZenI18n.t('Telefon'), type: 'text' },
            { key: 'position', label: window.ZenI18n.t('Stanowisko'), type: 'text' },
            { key: 'client_id', label: window.ZenI18n.t('Klient'), type: 'client-select' },
            { key: 'lead_id', label: window.ZenI18n.t('Lead (opcjonalnie)'), type: 'lead-select' },
            { key: 'notes', label: window.ZenI18n.t('Notatki'), type: 'textarea' },
        ],

        users: [
            { key: 'email', label: window.ZenI18n.t('Email'), type: 'email', required: true },
            { key: 'password', label: window.ZenI18n.t('Haslo (puste = bez zmiany)'), type: 'password' },
            { key: 'first_name', label: window.ZenI18n.t('Imie'), type: 'text', required: true },
            { key: 'last_name', label: window.ZenI18n.t('Nazwisko'), type: 'text', required: true },
            { key: 'role', label: window.ZenI18n.t('Rola'), type: 'select', options: [
                { value: 'admin',    label: window.ZenI18n.t('Admin') },
                { value: 'manager',  label: window.ZenI18n.t('Manager') },
                { value: 'employee', label: window.ZenI18n.t('Pracownik') },
            ]},
            { key: 'team_ids', label: window.ZenI18n.t('Zespoły'), type: 'teams-select' },
        ],

        projects: [
            { key: 'name', label: window.ZenI18n.t('Nazwa projektu'), type: 'text', required: true },
            { key: 'client_id', label: window.ZenI18n.t('Klient'), type: 'client-select' },
            { key: 'manager_id', label: window.ZenI18n.t('Opiekun projektu'), type: 'user-select' },
            { key: 'status', label: window.ZenI18n.t('Status'), type: 'select', options: [
                { value: 'planned',     label: window.ZenI18n.t('Planowany') },
                { value: 'in_progress', label: window.ZenI18n.t('W realizacji') },
                { value: 'on_hold',     label: window.ZenI18n.t('Wstrzymany') },
                { value: 'completed',   label: window.ZenI18n.t('Zakończony') },
                { value: 'cancelled',   label: window.ZenI18n.t('Anulowany') },
            ]},
            { key: 'budget', label: window.ZenI18n.t('Budżet (zł)'), type: 'number' },
            { key: 'start_date', label: window.ZenI18n.t('Data rozpoczęcia'), type: 'date' },
            { key: 'end_date', label: window.ZenI18n.t('Termin zakończenia'), type: 'date' },
            { key: 'description', label: window.ZenI18n.t('Opis'), type: 'textarea' },
            { key: 'member_ids', label: window.ZenI18n.t('Członkowie zespołu'), type: 'multi-user-select' },
        ],
    },

    MENU: [
        { id: 'dashboard', label: window.ZenI18n.t('Dashboard'), icon: '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"/></svg>' },
        {
            id: 'crm',
            label: window.ZenI18n.t('CRM'),
            icon: '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"/></svg>',
            children: [
                { id: 'clients',   label: window.ZenI18n.t('Klienci'), icon: '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/></svg>' },
                { id: 'leads',     label: window.ZenI18n.t('Leady'), icon: '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"/></svg>' },
                { id: 'contacts',  label: window.ZenI18n.t('Kontakty'), icon: '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/></svg>' },
            ]
        },
        { id: 'projects',  label: window.ZenI18n.t('Projekty'), icon: '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/></svg>' },
        { id: 'tasks',     label: window.ZenI18n.t('Zadania'), icon: '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"/></svg>' },
        { id: 'meetings',  label: window.ZenI18n.t('Kalendarz'), icon: '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>' },
        {
            id: 'services_group',
            label: window.ZenI18n.t('Usługi'),
            icon: '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/></svg>',
            children: [
                { id: 'services',  label: window.ZenI18n.t('Usługi'), icon: '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/></svg>' },
                { id: 'serviceCatalog', label: window.ZenI18n.t('Katalog usług'), icon: '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"/></svg>' },
            ]
        },
        {
            id: 'documents_group',
            label: window.ZenI18n.t('Dokumenty'),
            icon: '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>',
            children: [
                { id: 'offers',    label: window.ZenI18n.t('Oferty'), icon: '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>' },
                { id: 'documents', label: window.ZenI18n.t('Dokumenty'), icon: '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"/></svg>' },
                { id: 'templates', label: window.ZenI18n.t('Szablony'), icon: '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z"/></svg>' },
            ]
        },
        {
            id: 'tickets_group',
            label: window.ZenI18n.t('Tickety'),
            icon: '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 5v2m0 4v2m0 4v2M5 5a2 2 0 00-2 2v3a2 2 0 110 4v3a2 2 0 002 2h14a2 2 0 002-2v-3a2 2 0 110-4V7a2 2 0 00-2-2H5z"/></svg>',
            children: [
                { id: 'tickets', label: window.ZenI18n.t('Lista ticketów'), icon: '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"/></svg>' },
                { id: 'ticketSettings', label: window.ZenI18n.t('Ustawienia ticketów'), icon: '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/></svg>' },
            ]
        },
        { id: 'sms',       label: window.ZenI18n.t('Telefonia & SMS'), icon: '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 18h.01M8 21h8a2 2 0 002-2V5a2 2 0 00-2-2H8a2 2 0 00-2 2v14a2 2 0 002 2z"/></svg>' },
        { id: 'portal_group', label: 'Portal użytkownika', adminOnly: true, icon: '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-width="2" d="M4 4h16v16H4zM4 9h16M9 9v11"/></svg>', children: [
            { id: 'portalTickets', label: 'Tickety', icon: '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h8m-8 4h5m-8 7l2.5-3H19a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v11a2 2 0 002 2v3z"/></svg>' },
            { id: 'portalSpaces', label: 'Portale', icon: '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7h18M5 7v12h14V7M8 11h3m-3 4h8"/></svg>' },
            { id: 'portalSettings', label: 'Ustawienia portalu', icon: '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-width="2" d="M4 4h16v16H4zM4 9h16M9 9v11"/></svg>' },
            { id: 'portalUsers', label: 'Użytkownicy portalu', icon: '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-width="2" d="M4 4h16v16H4zM4 9h16M9 9v11"/></svg>' },
        ] },
        { id: 'users',     label: window.ZenI18n.t('Pracownicy'), icon: '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"/></svg>' },
        { id: 'notifications', label: window.ZenI18n.t('Powiadomienia'), icon: '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"/></svg>' },
        { id: 'settings',  label: window.ZenI18n.t('Ustawienia'), icon: '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/></svg>' },
        { id: 'archive',   label: window.ZenI18n.t('Archiwum'), icon: '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4"/></svg>' },
    ],

    LEAD_STAGES: [
        { id: 'new', accent: '#0057b8',         label: window.ZenI18n.t('Nowy'),          gradient: 'linear-gradient(135deg, #007fce, #009fb9)' },
        { id: 'contacted', accent: '#007fce',   label: window.ZenI18n.t('Kontakt'),       gradient: 'linear-gradient(135deg, #3b82f6, #06b6d4)' },
        { id: 'qualified', accent: '#009fb9',   label: window.ZenI18n.t('Kwalifikowany'), gradient: 'linear-gradient(135deg, #10b981, #14b8a6)' },
        { id: 'proposal', accent: '#27b8ce',    label: window.ZenI18n.t('Oferta'),        gradient: 'linear-gradient(135deg, #f59e0b, #f97316)' },
        { id: 'negotiation', accent: '#008e98', label: window.ZenI18n.t('Negocjacje'),    gradient: 'linear-gradient(135deg, #ef4444, #ec4899)' },
        { id: 'won', accent: '#27ad8a',         label: window.ZenI18n.t('Wygrany'),       gradient: 'linear-gradient(135deg, #10b981, #059669)' },
        { id: 'lost', accent: '#20364b',        label: window.ZenI18n.t('Przegrany'),     gradient: 'linear-gradient(135deg, #6b7280, #4b5563)' },
    ],

    DASHBOARD_CARDS: [
        { key: 'clients',   label: window.ZenI18n.t('Klienci'),       color: 'bg-blue-100 text-blue-600',
          icon: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"/></svg>' },
        { key: 'leads',     label: window.ZenI18n.t('Leady'),         color: 'bg-green-100 text-green-600',
          icon: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"/></svg>' },
        { key: 'projects',  label: window.ZenI18n.t('Projekty'),      color: 'bg-indigo-100 text-indigo-600',
          icon: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/></svg>' },
        { key: 'tasks',     label: window.ZenI18n.t('Zadania'),       color: 'bg-yellow-100 text-yellow-600',
          icon: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/></svg>' },
        { key: 'tickets',   label: window.ZenI18n.t('Tickety'),       color: 'bg-rose-100 text-rose-600',
          icon: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 5v2m0 4v2m0 4v2M5 5a2 2 0 00-2 2v3a2 2 0 110 4v3a2 2 0 002 2h14a2 2 0 002-2v-3a2 2 0 110-4V7a2 2 0 00-2-2H5z"/></svg>' },
        { key: 'services',  label: window.ZenI18n.t('Usługi'),        color: 'bg-cyan-100 text-cyan-600',
          icon: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/></svg>' },
        { key: 'won_value', label: window.ZenI18n.t('Wygrane (zl)'),  color: 'bg-brand-100 text-brand-600',
          icon: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>' },
    ],
};

window.DEFAULT_TEMPLATE = '<h1>{{ title }}</h1><p>{{ description }}</p>';
