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
    const sourceLabels = {tasks:'Zadania', clients:'Klienci', leads:'Leady', projects:'Projekty', tickets:'Zgłoszenia',
        documents:'Dokumenty', offers:'Oferty', services:'Usługi', meetings:'Spotkania'};
    const fieldLabels = {status:'Status', priority:'Priorytet', month:'Miesiąc', source:'Źródło', country:'Kraj', category:'Kategoria',
        type:'Typ', billing_type:'Typ rozliczenia', billing_cycle:'Cykl rozliczeniowy', created_at:'Data utworzenia', updated_at:'Data aktualizacji',
        due_date:'Termin zadania', expected_close_date:'Planowane zamknięcie', start_date:'Data rozpoczęcia', end_date:'Data zakończenia',
        valid_until:'Ważność oferty', resolved_at:'Data rozwiązania', closed_at:'Data zamknięcia', start_time:'Początek spotkania', end_time:'Koniec spotkania'};
    window.pluginReport = entry => ({
        entity: 'tasks', groupBy: 'status', dateFrom: '', dateTo: '', statusFilter: '', overdueOnly: false,
        report: null, reportError: '', busy: false, generation: 0,
        capabilities:{tasks:{groups:['status','priority','month'],dates:['created_at','due_date'],overdue:true},clients:{groups:['status','country','month'],dates:['created_at']}},
        dateField:'created_at', comparePrevious:false, amountMin:'', amountMax:'', driveBusy:false, driveResult:null,
        async init() {
            this.preset('30');
            this.$watch('token', () => { this.generation++; this.report = null; this.reportError = ''; this.busy = false; });
            const token=this.token, view=this.currentView, generation=this.generation;
            try {
                const capabilities=await this.api('/plugins/apps/'+entry.app.id+'/invoke', {method:'POST',body:JSON.stringify({operation:'reports.capabilities',params:{}})});
                if(token!==this.token || view!==this.currentView || generation!==this.generation || !this.active()) return;
                this.capabilities=capabilities; await this.generate();
            } catch(error) { if(token===this.token && view===this.currentView) this.reportError=error.message; }
        },
        destroy() { this.generation++; this.report = null; },
        datasetChanged() { this.groupBy = 'status'; this.dateField='created_at'; this.statusFilter = ''; this.overdueOnly = false; this.amountMin=''; this.amountMax=''; },
        sourceLabel(key) { return t(Object.hasOwn(sourceLabels,key) ? sourceLabels[key] : key); },
        fieldLabel(key) { return t(Object.hasOwn(fieldLabels,key) ? fieldLabels[key] : key); },
        sourceOptions() { return Object.keys(sourceLabels).filter(key => Object.hasOwn(this.capabilities,key)); },
        groups() { return this.capabilities[this.entity]?.groups || ['status']; },
        dates() { return this.capabilities[this.entity]?.dates || ['created_at']; },
        allowsAmount() { return !!this.capabilities[this.entity]?.amount; },
        allowsOverdue() { return !!this.capabilities[this.entity]?.overdue; },
        preset(period) {
            const now = new Date(), end = now.toISOString().slice(0, 10);
            if (period === 'all') { this.dateFrom = ''; this.dateTo = ''; this.comparePrevious=false; return; }
            const start = new Date(now);
            if (period === 'month') start.setUTCDate(1);
            else start.setUTCDate(start.getUTCDate() - 29);
            this.dateFrom = start.toISOString().slice(0, 10); this.dateTo = end;
        },
        async generate() {
            const session = this.token, view = this.currentView, generation = ++this.generation;
            this.report = null; this.reportError = ''; this.driveResult=null; this.busy = true;
            const alive = () => session === this.token && view === this.currentView && generation === this.generation && this.active();
            try {
                const params = {entity: this.entity, group_by: this.groupBy, date_from: this.dateFrom || null,
                    date_to: this.dateTo || null, status: this.statusFilter, overdue_only: this.allowsOverdue() && this.overdueOnly,
                    ...(this.dateField!=='created_at' ? {date_field:this.dateField} : {}),
                    ...(this.comparePrevious && this.dateFrom && this.dateTo ? {compare_previous:true} : {}),
                    ...(this.allowsAmount() && this.amountMin!=='' ? {amount_min:this.amountMin} : {}),
                    ...(this.allowsAmount() && this.amountMax!=='' ? {amount_max:this.amountMax} : {})};
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
        csvRows() {
            const r = this.report;
            const rows = [[t('Studio raportów')], [t('Dane'), this.sourceLabel(r.entity)],
                [t('Grupowanie'), this.fieldLabel(r.group_by)], [t('Pole daty'), this.fieldLabel(r.date_field || 'created_at')],
                [t('Data od'), r.date_from || ''], [t('Data do'), r.date_to || ''], [t('Status'), r.status],
                [t('Tylko zaległe'), r.overdue_only ? t('Tak') : t('Nie')],
                [t('Wartość od'), r.amount_min || ''], [t('Wartość do'), r.amount_max || ''],
                [t('Wygenerowano (UTC)'), r.generated_at], [t('Liczba rekordów'), r.total]];
            if (r.metrics?.amount!==undefined) rows.push([t('Wartość nominalna'),r.metrics.amount]);
            if (r.comparison) rows.push([t('Poprzedni okres'),r.comparison.date_from,r.comparison.date_to],
                [t('Liczba rekordów w poprzednim okresie'),r.comparison.total], [t('Zmiana liczby rekordów'),r.comparison.change],
                [t('Zmiana (%)'),r.comparison.change_percent??''], ...(r.comparison.amount!==undefined ? [[t('Poprzednia wartość nominalna'),r.comparison.amount]] : []));
            rows.push([], [t('Grupa'),t('Liczba rekordów'),t('Udział (%)'),...(r.metrics?.amount!==undefined?[t('Wartość nominalna')]:[])],
                ...r.rows.map(row=>[this.rowLabel(row),row.count,row.percent,...(row.amount!==undefined?[row.amount]:[])]));
            return rows;
        },
        csvBlob() { return new Blob([csv(this.csvRows())], {type:'text/csv;charset=utf-8'}); },
        filename() { return 'zencrm-report-' + this.report.entity + '-' + this.report.generated_at.slice(0,10) + '.csv'; },
        exportCSV() {
            if (!this.report || !this.token || !this.active()) return;
            const url = URL.createObjectURL(this.csvBlob());
            const link = document.createElement('a'); link.href = url;
            link.download = this.filename();
            link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
        },
        async saveToDrive() {
            if (!this.report || !this.token || !this.active() || this.driveBusy || this.busy) return;
            const token=this.token, view=this.currentView, report=this.report;
            this.driveBusy=true; this.driveResult=null; this.reportError='';
            try {
                const result=await window.ZenDrive.upload(this,this.csvBlob(),this.filename());
                if(token===this.token && view===this.currentView && this.active() && report===this.report) this.driveResult=result;
            } catch(error) { if(token===this.token && view===this.currentView && report===this.report) this.reportError=error.message; }
            finally { this.driveBusy=false; }
        }
    });
})();
