/* Interakcje list i kart. Bez dodatkowych bibliotek. */
window.formatDate = function(dateStr) {
    if (!dateStr) return '—';
    try {
        if (typeof dateStr === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(dateStr.trim())) {
            const [y, m, d] = dateStr.trim().split('-');
            return `${d}.${m}.${y}`;
        }
        const d = new Date(dateStr);
        if (isNaN(d.getTime())) return dateStr;
        return d.toLocaleDateString(window.ZenI18n?.locale || window.ZenI18n.locale, {
            year: 'numeric', month: '2-digit', day: '2-digit'
        });
    } catch (_) {
        return dateStr;
    }
};
window.formatDateTime = function(dateStr) {
    if (!dateStr) return '—';
    try {
        const d = new Date(dateStr);
        if (isNaN(d.getTime())) return dateStr;
        return d.toLocaleString(window.ZenI18n?.locale || window.ZenI18n.locale, {
            year: 'numeric', month: '2-digit', day: '2-digit',
            hour: '2-digit', minute: '2-digit'
        });
    } catch (_) {
        return dateStr;
    }
};

window.ZenUX = {
    formatDate(d) { return window.formatDate(d); },
    formatDateTime(d) { return window.formatDateTime(d); },
    dashboardSearch: '', directory: [], directoryLoading: false, directoryError: '',
    dashboardTaskTab: 'today',
    journal: {open:false,kind:'note',status:'',content:'',address:'',selected:null,search:'',history:[],saving:false,error:'',loading:false,revision:0,editingId:null},
    recordLabel(r) { return r.name || r.title || r.full_name || [r.first_name,r.last_name].filter(Boolean).join(' '); },
    recordType(type) { return {client:window.ZenI18n.t('Klient'),lead:window.ZenI18n.t('Lead'),contact:window.ZenI18n.t('Kontakt'),task:window.ZenI18n.t('Zadanie')}[type] || type; },
    noteLabel(c) { return ({note:window.ZenI18n.t('Notatka'),call:window.ZenI18n.t('Telefon'),email:window.ZenI18n.t('E-mail')}[c.kind] || window.ZenI18n.t('Notatka')) + (c.communication_status ? ' · ' + ({answered:window.ZenI18n.t('Odebrane'),missed:window.ZenI18n.t('Nieodebrane'),outgoing:window.ZenI18n.t('Wychodzący'),incoming:window.ZenI18n.t('Przychodzący')}[c.communication_status] || '') : ''); },
    async loadDirectory() {
        if (this.directoryLoading) return;
        this.directoryLoading=true; this.directoryError='';
        try { const types=['client','lead','contact','task']; const lists=await Promise.all([this.loadClientOptions(),...['leads','contacts','tasks'].map(p=>this.api('/'+p))]); this.directory=lists.flatMap((list,i)=>list.map(r=>({...r,_type:types[i]}))); }
        catch(e) { this.directoryError=e.message; } finally { this.directoryLoading=false; }
    },
    searchDirectory(term, forJournal=false) { const q=term.trim().toLocaleLowerCase(window.ZenI18n.locale); return this.directory.filter(r=>(!forJournal || r._type!=='task') && [this.recordLabel(r),r.email,r.phone].join(' ').toLocaleLowerCase(window.ZenI18n.locale).includes(q)).slice(0,20); },
    openSearchRecord(r) { this.dashboardSearch=''; if(r._type==='contact') this.openJournal('note','contact',r); else this.openDetail(r._type,r.id); },
    openJournal(kind='note',type=null,record=null) {
        this.journalReturnFocus=document.activeElement; this.journal={open:true,kind,status:kind==='call'?'answered':kind==='email'?'outgoing':'',content:'',address:'',selected:null,search:'',history:[],saving:false,error:'',loading:false,revision:this.journal.revision+1,editingId:null};
        this.loadDirectory(); if(type && record) this.selectJournalRecord({...record,_type:type});
        this.$nextTick(()=>document.getElementById(record?'journal-content':'journal-search')?.focus());
    },
    trapJournal(event) { const nodes=[...event.currentTarget.querySelectorAll('button,input,select,textarea,[tabindex="0"]')].filter(el=>!el.disabled && el.getClientRects().length); const first=nodes[0],last=nodes[nodes.length-1]; if(event.shiftKey && document.activeElement===first) { event.preventDefault(); last?.focus(); } else if(!event.shiftKey && document.activeElement===last) { event.preventDefault(); first?.focus(); } },
    closeJournal() { if(this.journal.saving) return; this.journal.open=false; this.journal.revision++; this.$nextTick(()=>this.journalReturnFocus?.focus()); },
    setJournalKind(kind) { this.journal.kind=kind; this.journal.status=kind==='call'?'answered':kind==='email'?'outgoing':''; this.journal.address=this.journal.selected?.[kind==='call'?'phone':'email'] || ''; this.journal.editingId=null; },
    editJournalCall(entry) {
        this.journal.kind='call'; this.journal.status=entry.communication_status || 'answered';
        this.journal.address=entry.address || ''; this.journal.content=entry.content;
        this.journal.editingId=entry.id;
        this.$nextTick(()=>document.getElementById('journal-content')?.focus());
    },
    async selectJournalRecord(r) {
        this.journal.selected=r; this.journal.search=''; this.journal.history=[]; this.journal.error=''; this.setJournalKind(this.journal.kind);
        const revision=++this.journal.revision; this.journal.loading=true;
        try { const items=await this.api('/comments?entity_type='+r._type+'&entity_id='+r.id); if(revision===this.journal.revision) this.journal.history=items.slice().reverse(); }
        catch(e) { if(revision===this.journal.revision) this.journal.error=e.message; }
        finally { if(revision===this.journal.revision) this.journal.loading=false; }
    },
    async saveJournal() {
        const j=this.journal; if(j.saving || j.loading) return;
        if(!j.selected || !j.content.trim()) { j.error=window.ZenI18n.t('Wybierz rekord i wpisz treść notatki.'); return; }
        j.saving=true; j.error='';
        try { const entry=await this.api(j.editingId ? `/comments/${j.editingId}` : '/comments',{method:j.editingId?'PUT':'POST',body:JSON.stringify({entity_type:j.selected._type,entity_id:j.selected.id,kind:j.kind,communication_status:j.status || null,address:j.kind==='note'?null:j.address.trim(),content:j.content.trim()})}); if(j.editingId) j.history=j.history.map(item=>item.id===entry.id?entry:item); else j.history.unshift(entry); j.content=''; j.editingId=null; this.notify(window.ZenI18n.t('Zapisano wpis w historii')); if(this.detailView.open && this.detailView.type===j.selected._type && this.detailView.id===j.selected.id) await this.loadDetail(); }
        catch(e) { j.error=e.message; } finally { j.saving=false; }
    },

    contactSearch: '', customLeadStages: null, stageEditorOpen: false, stageDraft: [], stageError: '', stageSaving: false,
    taskStatusStages: [
        { id: 'todo', label: window.ZenI18n.taskStageLabels.todo, accent: '#865528' },
        { id: 'in_progress', label: window.ZenI18n.taskStageLabels.in_progress, accent: '#008c9f' },
        { id: 'done', label: window.ZenI18n.taskStageLabels.done, accent: '#16886e' },
    ],
    taskStageEditorOpen: false, taskStageDraft: [], taskStageError: '', taskStageSaving: false,
    get displayedTaskStages() { return (this.taskStatusStages || []).map(stage => window.ZenI18n.taskStage(stage)); },
    taskStageLabel(id) { return this.displayedTaskStages.find(stage => stage.id === id)?.label || id || '—'; },
    taskStageColor(id) { return this.taskStatusStages.find(stage => stage.id === id)?.accent || '#8b9cad'; },
    get taskBoardStages() {
        const configured = this.displayedTaskStages;
        const known = new Set(configured.map(stage => stage.id));
        return [...configured, ...(this.tasks || []).filter(task => !known.has(task.status)).map(task => task.status)
            .filter((status, index, statuses) => status && statuses.indexOf(status) === index)
            .map(id => ({ id, label: id, accent: '#8b9cad' }))];
    },
    get dashboardTaskStages() {
        const configured = this.displayedTaskStages;
        const known = new Set(configured.map(stage => stage.id));
        return [...configured, ...Object.keys(this.stats?.task_status || {}).filter(id => !known.has(id))
            .map(id => ({ id, label: id, accent: '#8b9cad' }))];
    },
    editTaskStages() { this.taskStageDraft = this.taskStatusStages.map(stage => ({ ...stage })); this.taskStageError = ''; this.taskStageEditorOpen = true; },
    addTaskStage() {
        if (this.taskStageDraft.length >= 20) return;
        let id;
        do { id = 'stage_' + Math.random().toString(36).slice(2, 10); }
        while (this.taskStageDraft.some(stage => stage.id === id));
        this.taskStageDraft.splice(this.taskStageDraft.length - 1, 0,
            { id, label: window.ZenI18n.t('Nowy status'), accent: '#009fb9' });
    },
    moveTaskStage(index, direction) {
        const next = index + direction;
        if (index <= 0 || index >= this.taskStageDraft.length - 1 || next <= 0 || next >= this.taskStageDraft.length - 1) return;
        const draft = [...this.taskStageDraft];
        [draft[index], draft[next]] = [draft[next], draft[index]];
        this.taskStageDraft = draft;
    },
    removeTaskStage(id) {
        if (id === 'todo' || id === 'done') return;
        this.taskStageDraft = this.taskStageDraft.filter(stage => stage.id !== id);
    },
    async saveTaskStages() {
        this.taskStageError = ''; this.taskStageSaving = true;
        try {
            const result = await this.api('/tasks/board-settings', { method: 'PUT', body: JSON.stringify({ stages: this.taskStageDraft }) });
            this.taskStatusStages = result.stages;
            this.settingsForm.task_stages = JSON.stringify(result.stages);
            if (this.taskFilter && !result.stages.some(stage => stage.id === this.taskFilter)) this.taskFilter = '';
            this.taskStageEditorOpen = false;
            this.notify(window.ZenI18n.t('Zapisano statusy zadań'));
        } catch (error) { this.taskStageError = error.message; }
        finally { this.taskStageSaving = false; }
    },
    boardColumns: Math.min(6, Math.max(2, Number(localStorage.getItem('zen-board-columns')) || 4)),
    calendarSelected: new Date(),
    localDateKey(date) { return [date.getFullYear(), String(date.getMonth()+1).padStart(2,'0'), String(date.getDate()).padStart(2,'0')].join('-'); },
    get filteredContacts() { const term = this.contactSearch.trim().toLocaleLowerCase(window.ZenI18n.locale); return this.contacts.filter(c => [c.first_name,c.last_name,c.email,c.phone,this.clientName(c.client_id)].join(' ').toLocaleLowerCase(window.ZenI18n.locale).includes(term)); },
    openCalendarEvent(event) { if (event._type === 'task') this.openDetail('task',event.id); else this.openModal(event, null, false, 'meetings'); },
    setBoardColumns() { localStorage.setItem('zen-board-columns', this.boardColumns); this.$nextTick(() => this.recomputeVisibleCols()); },
    editStages() { this.stageDraft = (this.customLeadStages || window.ZenConfig.LEAD_STAGES.map(s => ({...s,label:window.ZenI18n.stageLabels[s.id] || s.label}))).map(s => ({...s})); this.stageError = ''; this.stageEditorOpen = true; },
    addStage() { if (this.stageDraft.length < 20) this.stageDraft.push({id: 'stage_' + Date.now().toString(36),label:window.ZenI18n.t('Nowy status'),accent:'#009fb9'}); },
    moveStage(index, direction) { const next = index + direction; if (next < 0 || next >= this.stageDraft.length) return; const draft = [...this.stageDraft]; [draft[index],draft[next]] = [draft[next],draft[index]]; this.stageDraft = draft; },
    async saveStages() {
        this.stageError = ''; this.stageSaving = true;
        try { const result = await this.api('/leads/board-settings', {method:'PUT',body:JSON.stringify({stages:this.stageDraft})}); this.customLeadStages = result.stages; this.settingsForm.lead_stages = JSON.stringify(result.stages); this.stageEditorOpen = false; this.$nextTick(() => this.recomputeVisibleCols()); this.notify(window.ZenI18n.t('Zapisano statusy leadów')); }
        catch (e) { this.stageError = e.message; } finally { this.stageSaving = false; }
    },
    leadSearch: '', leadFilter: '', taskScope: '', taskSearch: '',
    notice: null, noticeTimer: null, undoAction: null, savingLead: null, savingTask: null,
    canScrollLeft: false, canScrollRight: false, kanbanLeft: 0,
    dragFrame: null, dragSpeed: 0, dragY: 0, lastDragEnd: 0, detailError: '',
    listError: '', returnScroll: 0,
    chartError: '',
    canChangeTaskPerson(person) { return this.user?.role === 'admin' || Number(person.user_id) === Number(this.user?.id); },
    documentRelationPicker(field) {
        const app = this;
        const key = field.key;
        const endpoint = key === 'lead_id' ? 'leads' : 'services';
        return {
            enabled: !!app.modal.form[key], formReference: app.modal.form,
            search: '', items: [], loading: false, error: '', revision: 0,
            init() {
                this.load();
                this.$watch('modal.open', open => {
                    if (!open) { ++this.revision; return; }
                    this.formReference = app.modal.form;
                    this.enabled = !!app.modal.form[key];
                    this.search = '';
                    this.load();
                });
                this.$watch('modal.form.client_id', (value, old) => {
                    if (String(value || '') === String(old || '')) return;
                    if (this.formReference === app.modal.form) app.modal.form[key] = null;
                    else {
                        this.formReference = app.modal.form;
                        this.enabled = !!app.modal.form[key];
                    }
                    this.search = '';
                    this.load();
                });
            },
            async load() {
                const revision = ++this.revision;
                const client = app.modal.form.client_id;
                this.items = []; this.error = ''; this.loading = false;
                if (!client && (app.modal.view || app.currentView) !== 'tasks') return;
                this.loading = true;
                try {
                    const items = await app.api('/' + endpoint + (client ? '?client_id=' + encodeURIComponent(client) : ''));
                    if (revision === this.revision) this.items = items;
                } catch (e) { if (revision === this.revision) this.error = e.message; }
                finally { if (revision === this.revision) this.loading = false; }
            },
            get matches() {
                const term = this.search.trim().toLocaleLowerCase(window.ZenI18n.locale);
                return this.items.filter(item => (item.title || item.name || '').toLocaleLowerCase(window.ZenI18n.locale).includes(term));
            },
            get chosen() { return this.items.find(item => Number(item.id) === Number(app.modal.form[key])); },
            choose(item) { app.modal.form[key] = item.id; this.search = ''; },
            clear() { app.modal.form[key] = null; this.search = ''; },
        };
    },
    get funnelTotal() { return this.leadStages.reduce((sum, s) => sum + Number(this.stats.funnel?.[s.id] || 0), 0); },
    detailPanel: false, returnFocus: null, boardTasks: [], boardTasksLoaded: false,

    panelKeydown(event) {
        if (!this.detailPanel || this.modal.open) return;
        if (event.key === 'Escape') { event.preventDefault(); this.closeDetail(); }
        if (event.key !== 'Tab') return;
        const nodes = [...event.currentTarget.querySelectorAll('button, a[href], input, select, textarea, [tabindex="0"]')]
            .filter(el => !el.disabled && el.getClientRects().length);
        const first = nodes[0], last = nodes[nodes.length - 1];
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
    },
    leadNextTask(lead) {
        return this.boardTasks.filter(t => t.lead_id === lead.id && t.status !== 'done')
            .sort((a,b) => (a.due_date ? new Date(a.due_date).getTime() : Infinity) - (b.due_date ? new Date(b.due_date).getTime() : Infinity))[0];
    },
    leadNextLabel(lead) {
        if (!this.boardTasksLoaded) return window.ZenI18n.t('Następne działanie: brak danych');
        const task = this.leadNextTask(lead);
        if (!task) return window.ZenI18n.t('Brak zaplanowanego działania');
        return task.title + ' · ' + (task.due_date ? new Date(task.due_date).toLocaleDateString(window.ZenI18n.locale) : window.ZenI18n.t('bez terminu'));
    },

    async loadClientOptions() {
        const first = await this.api('/clients?page=1');
        if (Array.isArray(first)) return first;
        const clients = [...(first.clients || [])];
        for (let page = 2; page <= (first.pages || 1); page++) {
            const result = await this.api('/clients?page=' + page);
            clients.push(...(result.clients || []));
        }
        return clients;
    },

    notify(message, undo = null) {
        clearTimeout(this.noticeTimer);
        // Alpine evaluates function-valued expressions, including x-show.
        // Expose a boolean to the template, never the undo callback itself.
        this.undoAction = undo;
        this.notice = { message, canUndo: typeof undo === 'function' };
        this.noticeTimer = setTimeout(() => this.dismissNotice(), undo ? 15000 : 7000);
    },
    dismissNotice() {
        clearTimeout(this.noticeTimer);
        this.notice = null;
        this.undoAction = null;
    },
    async undoNotice() {
        const action = this.undoAction;
        this.dismissNotice();
        if (action) await action();
    },
    get boardLeads() {
        const q = this.leadSearch.trim().toLocaleLowerCase(window.ZenI18n.locale);
        return this.leads.filter(l => (!q || `${l.title} ${this.clientName(l.client_id)} ${l.source || ''}`.toLocaleLowerCase(window.ZenI18n.locale).includes(q))
            && (this.leadFilter !== 'mine' || Number(l.assignee_id) === Number(this.user?.id))
            && (this.leadFilter !== 'unassigned' || !l.assignee_id));
    },
    isOverdue(task) {
        return task.status !== 'done' && task.due_date && new Date(task.due_date).getTime() < Date.now();
    },
    taskProgress(task) {
        const assignees = Array.isArray(task?.assignees) ? task.assignees : [];
        if (assignees.length) {
            return Math.round(assignees.filter(person => person.status === 'done').length / assignees.length * 100);
        }
        return task?.status === 'done' ? 100 : 0;
    },
    get visibleTasks() {
        const q = this.taskSearch.trim().toLocaleLowerCase(window.ZenI18n.locale);
        const now = new Date();
        const start = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
        const end = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1).getTime();
        return this.tasks.filter(t => {
            const date = t.due_date ? new Date(t.due_date).getTime() : NaN;
            return (!this.taskFilter || t.status === this.taskFilter)
                && (!q || `${t.title} ${this.clientName(t.client_id)}`.toLocaleLowerCase(window.ZenI18n.locale).includes(q))
                && (this.taskScope !== 'mine' || Number(t.assignee_id) === Number(this.user?.id) || (t.assignees || []).some(a => Number(a.user_id) === Number(this.user?.id)))
                && (this.taskScope !== 'today' || (date >= start && date < end && t.status !== 'done'))
                && (this.taskScope !== 'overdue' || this.isOverdue(t))
                && (this.taskScope !== 'upcoming' || (date >= end && t.status !== 'done'))
                && (this.taskScope !== 'undated' || (!t.due_date && t.status !== 'done'));
        });
    },
    dashboardTasksByTab(tab) {
        if (tab === 'overdue' && Array.isArray(this.stats?.overdue_tasks)) {
            return this.stats.overdue_tasks;
        }
        if (tab === 'today' && Array.isArray(this.stats?.today_tasks)) {
            return this.stats.today_tasks;
        }
        if (tab === 'upcoming' && Array.isArray(this.stats?.upcoming_tasks)) {
            return this.stats.upcoming_tasks;
        }
        const all = this.tasks?.length ? this.tasks : (this.stats?.upcoming_tasks || []);
        const now = new Date();
        const start = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
        const end = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1).getTime();
        return all.filter(t => {
            if (t.status === 'done') return false;
            const d = t.due_date ? new Date(t.due_date).getTime() : NaN;
            if (tab === 'overdue') return !isNaN(d) && d < now.getTime();
            if (tab === 'today') return !isNaN(d) && d >= start && d < end;
            if (tab === 'upcoming') return isNaN(d) || d >= end;
            return true;
        });
    },
    formatTaskDate(task, tab) {
        if (!task || !task.due_date) return window.ZenI18n.t('Bez terminu');
        try {
            const d = new Date(task.due_date);
            if (isNaN(d.getTime())) return task.due_date;
            const now = new Date();
            const isToday = d.getFullYear() === now.getFullYear() && d.getMonth() === now.getMonth() && d.getDate() === now.getDate();
            const hasTime = task.due_date.includes('T') && !task.due_date.endsWith('00:00:00') && !task.due_date.endsWith('T00:00');
            if (tab === 'today') {
                if (hasTime) {
                    return d.toLocaleTimeString(window.ZenI18n?.locale || window.ZenI18n.locale, { hour: '2-digit', minute: '2-digit' });
                }
                return window.ZenI18n.t('Dzisiaj');
            }
            if (tab === 'overdue' && isToday && hasTime) {
                return window.ZenI18n.t('Dzisiaj') + ', ' + d.toLocaleTimeString(window.ZenI18n?.locale || window.ZenI18n.locale, { hour: '2-digit', minute: '2-digit' });
            }
            return window.formatDate ? window.formatDate(task.due_date) : d.toLocaleDateString(window.ZenI18n?.locale || window.ZenI18n.locale);
        } catch (_) {
            return task.due_date || '—';
        }
    },
    get nextDetailTask() {
        return [...(this.detailView.tasks || [])].filter(t => t.status !== 'done')
            .sort((a, b) => (a.due_date ? new Date(a.due_date).getTime() : Infinity) - (b.due_date ? new Date(b.due_date).getTime() : Infinity))[0] || null;
    },
    async changeLeadStage(lead, stage) {
        if (!lead || !this.leadStages.some(s => s.id === stage)) return;
        const current = this.leads.find(l => l.id === lead.id) || lead;
        if (this.savingLead || stage === current.stage) return;
        const previous = current.stage;
        this.savingLead = lead.id;
        try {
            const saved = await this.api(`/leads/${lead.id}`, { method: 'PUT', body: JSON.stringify({ stage }) });
            // Keep the source DOM intact until the drop finishes and the server confirms.
            const committed = saved.stage || stage;
            lead.stage = committed;
            const listed = this.leads.find(l => l.id === lead.id);
            if (listed) listed.stage = committed;
            if (this.detailView.type === 'lead' && this.detailView.id === lead.id && this.detailView.data) {
                this.detailView.data.stage = committed;
            }
            this.notify(window.ZenI18n.t('Przeniesiono do: ') + (this.leadStages.find(s => s.id === stage)?.label || stage), async () => {
                const latest = this.leads.find(l => l.id === lead.id) || lead;
                if (latest.stage === committed) await this.changeLeadStage(latest, previous);
            });
        } catch (e) { this.notify(window.ZenI18n.t('Nie zapisano zmiany: ') + e.message); }
        finally { this.savingLead = null; this.$nextTick(() => this.updateKanbanScroll()); }
    },
    startLeadDrag(event, lead) {
        if (this.savingLead || event.target.closest('select, button, a, input')) { event.preventDefault(); return; }
        this.draggedLead = lead;
        event.dataTransfer.effectAllowed = 'move';
        event.dataTransfer.setData('application/x-zencrm-lead', String(lead.id));
        event.dataTransfer.setData('text/plain', String(lead.id));
    },
    endLeadDrag() {
        this.draggedLead = null; this.dragOverStage = null; this.lastDragEnd = Date.now();
        this.stopBoardDrag();
    },
    async moveLead(event, stage) {
        event.preventDefault();
        const id = Number(event.dataTransfer?.getData('application/x-zencrm-lead'));
        const lead = this.draggedLead && this.leads.find(l => l.id === (id || this.draggedLead.id));
        this.endLeadDrag();
        // Let native dragend run before Alpine relocates any card between x-for lists.
        await new Promise(resolve => setTimeout(resolve, 0));
        await this.changeLeadStage(lead, stage);
    },
    boardDrag(event) {
        if (!this.draggedLead) return;
        event.dataTransfer.dropEffect = 'move';
        const el = this.$refs.kanbanCols;
        const box = el.getBoundingClientRect();
        this.dragY = event.clientY;
        this.dragSpeed = event.clientX < box.left + 65 ? -12 : event.clientX > box.right - 65 ? 12 : 0;
        if (this.dragFrame !== null) return;
        const tick = () => {
            if (!this.draggedLead) { this.stopBoardDrag(); return; }
            el.scrollLeft += this.dragSpeed;
            const column = el.querySelector('.kanban-col-new.dragover .kanban-col-body');
            if (column) {
                const bounds = column.getBoundingClientRect();
                column.scrollTop += this.dragY < bounds.top + 40 ? -8 : this.dragY > bounds.bottom - 40 ? 8 : 0;
            }
            this.dragFrame = requestAnimationFrame(tick);
        };
        this.dragFrame = requestAnimationFrame(tick);
    },
    stopBoardDrag() {
        cancelAnimationFrame(this.dragFrame); this.dragFrame = null; this.dragSpeed = 0;
    },
    updateKanbanScroll() {
        const el = this.$refs.kanbanCols;
        if (!el || !el.clientWidth) return;
        this.kanbanLeft = el.scrollLeft;
        this.canScrollLeft = el.scrollLeft > 2;
        this.canScrollRight = el.scrollWidth - el.clientWidth - el.scrollLeft > 2;
        const cols = [...el.querySelectorAll('.kanban-col-new')];
        this.kanbanScrollIndex = Math.max(0, cols.findIndex(c => c.offsetLeft + c.offsetWidth > el.scrollLeft + 8));
        this.visibleKanbanCols = Math.max(1, cols.filter(c => c.offsetLeft >= el.scrollLeft - 4 && c.offsetLeft + c.offsetWidth <= el.scrollLeft + el.clientWidth + 4).length);
    },
    recomputeVisibleCols() { this.updateKanbanScroll(); },
    scrollKanban(direction) {
        const el = this.$refs.kanbanCols;
        if (!el) return;
        const cols = [...el.querySelectorAll('.kanban-col-new')];
        const positions = cols.map(c => c.offsetLeft - cols[0].offsetLeft);
        const target = direction > 0 ? positions.find(p => p > el.scrollLeft + 3) : positions.reverse().find(p => p < el.scrollLeft - 3);
        el.scrollTo({ left: target ?? (direction > 0 ? el.scrollWidth : 0), behavior: 'smooth' });
    },
    scrollKanbanTo(index) {
        const el = this.$refs.kanbanCols;
        const cols = el?.querySelectorAll('.kanban-col-new');
        if (cols?.[index]) el.scrollTo({ left: cols[index].offsetLeft - cols[0].offsetLeft, behavior: 'smooth' });
    },
    async patchTask(task, fields) {
        if (this.savingTask) return;
        this.savingTask = task.id;
        const previous = Object.fromEntries(Object.keys(fields).map(k => [k, task[k]]));
        try {
            const fresh = await this.api(`/tasks/${task.id}`, { method: 'PUT', body: JSON.stringify(fields) });
            Object.assign(task, fresh);
            this.notify(window.ZenI18n.t('Zapisano zadanie'), () => this.patchTask(task, previous));
        } catch (e) { this.notify(window.ZenI18n.t('Nie zapisano zadania: ') + e.message); }
        finally { this.savingTask = null; }
    },
    async copyText(value) {
        try { await navigator.clipboard.writeText(value); this.notify(window.ZenI18n.t('Skopiowano')); }
        catch (_) { this.notify(window.ZenI18n.t('Nie można skopiować. Zaznacz i skopiuj tekst ręcznie.')); }
    },
    startTaskDrag(event, task) {
        if (this.savingTask || event.target.closest('select, button, a, input')) { event.preventDefault(); return; }
        this.draggedTask = task;
        event.dataTransfer.effectAllowed = 'move';
        event.dataTransfer.setData('application/x-zencrm-task', String(task.id));
        event.dataTransfer.setData('text/plain', String(task.id));
    },
    endTaskDrag() {
        this.draggedTask = null;
        this.dragOverTaskStatus = null;
    },
    async moveTaskToStatus(event, status) {
        event?.preventDefault?.();
        const id = Number(event?.dataTransfer?.getData('application/x-zencrm-task'));
        const task = (id ? (this.tasks || []).find(t => t.id === id) : null) || this.draggedTask;
        this.endTaskDrag();
        if (!task || task.status === status) return;
        await this.patchTask(task, { status });
    },
};
