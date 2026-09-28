// Only fixed SVG paths are returned; no user content is inserted into markup.
window.zenIcon = function(name) {
    const paths = {
        trash: 'M3 6h18 M9 6V3h6v3 M5 6l1 15h12l1-15 M10 10v7 M14 10v7',
        download: 'M12 3v12 M7 10l5 5 5-5 M4 16v5h16v-5',
        document: 'M5 3h9l5 5v13H5z M14 3v6h5 M8 13h8 M8 17h6',
        folder: 'M4 4h5l2 3h9a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z',
        restore: 'M3 10a9 9 0 1 1 1 8 M3 4v6h6',
        eye: 'M2 12s4-7 10-7 10 7 10 7-4 7-10 7-10-7-10-7 M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6',
        phone: 'M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6A19.79 19.79 0 0 1 2.12 4.2 2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.12.96.35 1.9.69 2.79a2 2 0 0 1-.45 2.11L8.08 9.89a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.9.34 1.83.57 2.79.69A2 2 0 0 1 22 16.92z',
        mail: 'M3 5h18v14H3z M3 6l9 7 9-7',
        copy: 'M9 9h12v12H9z M5 15H3V3h12v2',
        plus: 'M12 5v14 M5 12h14',
        edit: 'M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z M15 5l4 4',
        pencil: 'M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z M15 5l4 4',
        comment: 'M21 15a3 3 0 0 1-3 3H8l-5 4V6a3 3 0 0 1 3-3h12a3 3 0 0 1 3 3z',
        user: 'M20 21v-2a7 7 0 0 0-14 0v2 M13 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8',
        flag: 'M5 21V3 M5 3c5-4 9 4 14 0v10c-5 4-9-4-14 0',
        check: 'M4 12l5 5L20 6',
        activity: 'M3 12h4l3-8 4 16 3-8h4',
        settings: 'M4 7h16 M4 17h16 M8 4v6 M16 14v6',
        sun: 'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8 M12 2v2 M12 20v2 M2 12h2 M20 12h2 M5 5l1 1 M18 18l1 1 M5 19l1-1 M18 6l1-1',
        moon: 'M21 13A9 9 0 0 1 11 3a9 9 0 1 0 10 10z',
        calendar: 'M3 5h18v16H3z M7 3v4 M17 3v4 M3 11h18',
        arrow: 'M7 17L17 7 M7 7h10v10',
        left: 'M19 12H5 M11 6l-6 6 6 6',
        right: 'M5 12h14 M13 6l6 6-6 6',
    };
    return '<svg class="zen-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="' + (paths[name] || paths.activity) + '"/></svg>';
};
