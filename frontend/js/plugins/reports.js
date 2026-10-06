/* Local, reviewed report renderer. Provider manifests cannot supply executable UI. */
(function () {
    'use strict';
    const t = key => window.ZenI18n.t(key);
    function csvCell(value) {
        let text = String(value ?? '');
        // Quoting alone does not prevent spreadsheet formula execution.
        if (/^[\s\uFEFF]*[=+\-@]/.test(text) || /^[\t\r\n]/.test(text)) text = "'" + text;
        return '"' + text.replace(/"/g, '""') + '"';
    }
    const csv = rows => '\uFEFF' + rows.map(row => row.map(csvCell).join(';')).join('\r\n') + '\r\n';
    window.ZenReportCSV = {encode: csv};
    window.pluginReport = entry => ({
        entity: 'tasks', groupBy: 'status', dateFrom: '', dateTo: '', statusFilter: '', overdueOnly: false,
        report: null, reportError: '', busy: false, generation: 0,
        init() {
            this.preset('30'); this.generate();
            this.$watch('token', () => { this.generation++; this.report = null; this.reportError = ''; this.busy = false; });
        },
        destroy() { this.generation++; this.report = null; },
        datasetChanged() { this.groupBy = 'status'; this.statusFilter = ''; this.overdueOnly = false; },
        preset(period) {
            const now = new Date(), end = now.toISOString().slice(0, 10);
            if (period === 'all') { this.dateFrom = ''; this.dateTo = ''; return; }
            const start = new Date(now);
            if (period === 'month') start.setUTCDate(1);
            else start.setUTCDate(start.getUTCDate() - 29);
            this.dateFrom = start.toISOString().slice(0, 10); this.dateTo = end;
        },
        async generate() {
            const session = this.token, view = this.currentView, generation = ++this.generation;
            this.report = null; this.reportError = ''; this.busy = true;
            const alive = () => session === this.token && view === this.currentView && generation === this.generation && this.active();
            try {
                const params = {entity: this.entity, group_by: this.groupBy, date_from: this.dateFrom || null,
                    date_to: this.dateTo || null, status: this.statusFilter, overdue_only: this.entity === 'tasks' && this.overdueOnly};
                const report = await this.api('/plugins/apps/' + entry.app.id + '/invoke',
                    {method: 'POST', body: JSON.stringify({operation: 'reports.aggregate', params})});
                if (alive()) this.report = report;
            } catch (error) { if (alive()) this.reportError = error.message; }
            finally { if (generation === this.generation) this.busy = false; }
        },
        rowLabel(row) {
            if (row.other) return t('Pozostałe grupy');
            if (!row.label) return t('Bez wartości');
            const labels = {todo: 'Do zrobienia', in_progress: 'W trakcie', done: 'Ukończone',
                low: 'Niski', medium: 'Średni', high: 'Wysoki', active: 'Aktywny', inactive: 'Nieaktywny'};
            return Object.hasOwn(labels, row.label) ? t(labels[row.label]) : row.label;
        },
        reportPeriod() { return this.report ? (this.report.date_from || '…') + ' — ' + (this.report.date_to || '…') : ''; },
        exportCSV() {
            const r = this.report;
            if (!r || !this.token || !this.active()) return;
            const rows = [[t('Studio raportów')], [t('Dane'), t(r.entity === 'tasks' ? 'Zadania' : 'Klienci')],
                [t('Grupowanie'), t(r.group_by === 'priority' ? 'Priorytet' : 'Status')],
                [t('Data od'), r.date_from || ''], [t('Data do'), r.date_to || ''], [t('Status'), r.status],
                [t('Tylko zaległe zadania'), r.overdue_only ? t('Tak') : t('Nie')],
                [t('Wygenerowano (UTC)'), r.generated_at], [t('Liczba rekordów'), r.total], [],
                [t('Grupa'), t('Liczba rekordów'), t('Udział (%)')],
                ...r.rows.map(row => [this.rowLabel(row), row.count, row.percent])];
            const url = URL.createObjectURL(new Blob([csv(rows)], {type: 'text/csv;charset=utf-8'}));
            const link = document.createElement('a'); link.href = url;
            link.download = 'zencrm-report-' + r.entity + '-' + r.generated_at.slice(0, 10) + '.csv';
            link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
        }
    });
})();
