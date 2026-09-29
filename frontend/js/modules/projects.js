window.ZenModules = window.ZenModules || {};
window.ZenModules.projects = function () {
    return {
        projects: [],
        projectSearch: '',
        projectStatusFilter: '',
        activeProject: null,
        projectTasks: [],
        projectTaskFilter: '',
        projectTaskSearch: '',
        projectKanbanMode: 'kanban',
        projectTab: 'kanban',
        projectStageDraft: [],
        projectStageEditorOpen: false,
        projectStageSaving: false,
        projectStageError: '',
        draggedProjectTask: null,
        dragOverProjectStage: null,
        newMemberUserId: '',
        newMemberRole: 'member',

        projectStatusLabel(s) {
            return {
                planned: window.ZenI18n.t('Planowany'),
                in_progress: window.ZenI18n.t('W realizacji'),
                on_hold: window.ZenI18n.t('Wstrzymany'),
                completed: window.ZenI18n.t('Zakończony'),
                cancelled: window.ZenI18n.t('Anulowany')
            }[s] || s || '—';
        },

        projectStatusClass(s) {
            return {
                planned: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
                in_progress: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
                on_hold: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300',
                completed: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
                cancelled: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300'
            }[s] || 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300';
        },

        get filteredProjects() {
            let list = this.projects || [];
            if (this.projectStatusFilter) {
                list = list.filter(p => p.status === this.projectStatusFilter);
            }
            if (this.projectSearch) {
                const s = this.projectSearch.toLowerCase();
                list = list.filter(p =>
                    (p.name || '').toLowerCase().includes(s) ||
                    (p.description || '').toLowerCase().includes(s) ||
                    (this.clientName(p.client_id) || '').toLowerCase().includes(s) ||
                    (p.manager ? this.fullName(p.manager) : '').toLowerCase().includes(s)
                );
            }
            return list;
        },

        get rawProjectStages() {
            if (this.activeProject?.task_stages && Array.isArray(this.activeProject.task_stages) && this.activeProject.task_stages.length > 0) {
                return this.activeProject.task_stages;
            }
            return [
                { id: 'todo', label: window.ZenI18n.taskStageLabels.todo, accent: '#64748b' },
                { id: 'in_progress', label: window.ZenI18n.taskStageLabels.in_progress, accent: '#f59e0b' },
                { id: 'done', label: window.ZenI18n.taskStageLabels.done, accent: '#10b981' }
            ];
        },
        get projectStages() { return this.rawProjectStages.map(stage => window.ZenI18n.taskStage(stage)); },

        get filteredProjectTasks() {
            let list = this.projectTasks || [];
            if (this.projectTaskFilter) {
                list = list.filter(t => t.status === this.projectTaskFilter);
            }
            if (this.projectTaskSearch) {
                const s = this.projectTaskSearch.toLowerCase();
                list = list.filter(t =>
                    (t.title || '').toLowerCase().includes(s) ||
                    (t.description || '').toLowerCase().includes(s)
                );
            }
            return list;
        },

        projectProgress(p) {
            if (!p) return 0;
            if (p.tasks && p.tasks.length) {
                const done = p.tasks.filter(t => t.status === 'done').length;
                return Math.round((done / p.tasks.length) * 100);
            }
            if (p.percent_done !== undefined && p.percent_done !== null) {
                return Number(p.percent_done) || 0;
            }
            if (p.tasks_count) {
                return Math.round(((p.tasks_done_count || 0) / p.tasks_count) * 100);
            }
            return 0;
        },

        async openProject(pOrId, skipHash = false) {
            const id = typeof pOrId === 'object' ? pOrId.id : pOrId;
            if (!id) return;
            try {
                const full = await this.api('/projects/' + id);
                this.activeProject = full;
                this.projectTab = 'kanban';
                if (!skipHash) {
                    const newHash = '#project/' + id;
                    if (location.hash !== newHash) {
                        history.pushState(null, '', newHash);
                    }
                }
                await this.loadProjectTasks();
            } catch (e) {
                this.notify(window.ZenI18n.t('Błąd: ') + e.message);
            }
        },

        closeProject(skipHash = false) {
            this.activeProject = null;
            this.projectTasks = [];
            if (!skipHash && location.hash.startsWith('#project/')) {
                history.pushState(null, '', '#projects');
            }
        },

        async loadProjectTasks() {
            if (!this.activeProject) return;
            try {
                const res = await this.api('/tasks?project_id=' + this.activeProject.id);
                this.projectTasks = Array.isArray(res) ? res : (res.items || res.tasks || []);
            } catch (e) {
                console.warn('Błąd wczytywania zadań projektu:', e);
            }
        },

        editProjectStages() {
            if (!this.activeProject) return;
            this.projectStageDraft = JSON.parse(JSON.stringify(this.rawProjectStages));
            this.projectStageError = '';
            this.projectStageEditorOpen = true;
        },

        addProjectStage() {
            if (this.projectStageDraft.length >= 20) return;
            const id = 'stage_' + Date.now();
            const colors = ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4', '#64748b'];
            const accent = colors[this.projectStageDraft.length % colors.length];
            this.projectStageDraft.push({
                id,
                label: window.ZenI18n.t('Nowy status'),
                accent,
            });
        },

        moveProjectStage(index, delta) {
            const target = index + delta;
            if (target < 0 || target >= this.projectStageDraft.length) return;
            const item = this.projectStageDraft.splice(index, 1)[0];
            this.projectStageDraft.splice(target, 0, item);
        },

        removeProjectStage(id) {
            if (['todo', 'done'].includes(id)) {
                this.projectStageError = window.ZenI18n.t('Nie można usunąć domyślnego statusu.');
                return;
            }
            this.projectStageDraft = this.projectStageDraft.filter(s => s.id !== id);
        },

        async saveProjectStages() {
            if (!this.activeProject) return;
            this.projectStageSaving = true;
            this.projectStageError = '';
            try {
                const res = await this.api(`/projects/${this.activeProject.id}/stages`, {
                    method: 'PUT',
                    body: JSON.stringify({ stages: this.projectStageDraft })
                });
                this.activeProject.task_stages = res.task_stages || this.projectStageDraft;
                this.projectStageEditorOpen = false;
                this.notify(window.ZenI18n.t('Zapisano statusy zadań'));
            } catch (e) {
                this.projectStageError = e.message;
            } finally {
                this.projectStageSaving = false;
            }
        },

        startProjectTaskDrag(e, task) {
            this.draggedProjectTask = task;
            if (e.dataTransfer) {
                e.dataTransfer.effectAllowed = 'move';
                e.dataTransfer.setData('text/plain', String(task.id));
            }
        },

        endProjectTaskDrag() {
            this.draggedProjectTask = null;
            this.dragOverProjectStage = null;
        },

        async moveProjectTask(stageId) {
            if (!this.draggedProjectTask) return;
            const task = this.draggedProjectTask;
            this.endProjectTaskDrag();
            if (task.status === stageId) return;
            await this.changeProjectTaskStage(task, stageId);
        },

        async changeProjectTaskStage(task, newStageId) {
            try {
                await this.api(`/tasks/${task.id}`, {
                    method: 'PUT',
                    body: JSON.stringify({ status: newStageId })
                });
                task.status = newStageId;
                const glob = (this.tasks || []).find(t => t.id === task.id);
                if (glob) glob.status = newStageId;
            } catch (e) {
                this.notify(window.ZenI18n.t('Błąd: ') + e.message);
            }
        },

        quickAddProjectTask(stageId = 'todo') {
            if (!this.activeProject) return;
            const prefill = { project_id: this.activeProject.id, status: stageId };
            if (this.activeProject.client_id) prefill.client_id = this.activeProject.client_id;
            this.openModal(null, null, false, 'tasks', {
                prefill, lockedRelations: ['project_id', 'client_id', 'lead_id'],
            });
        },

        async addProjectMember() {
            if (!this.activeProject || !this.newMemberUserId) return;
            try {
                const res = await this.api(`/projects/${this.activeProject.id}/members`, {
                    method: 'POST',
                    body: JSON.stringify({
                        user_id: parseInt(this.newMemberUserId, 10),
                        role: this.newMemberRole || 'member'
                    })
                });
                this.activeProject.members = res.members || [];
                this.newMemberUserId = '';
                this.notify(window.ZenI18n.t('Dodano członka'));
            } catch (e) {
                this.notify(window.ZenI18n.t('Błąd: ') + e.message);
            }
        },

        async removeProjectMember(userId) {
            if (!this.activeProject) return;
            if (!confirm(window.ZenI18n.t('Usunąć tego członka z projektu?'))) return;
            try {
                const res = await this.api(`/projects/${this.activeProject.id}/members/${userId}`, {
                    method: 'DELETE'
                });
                this.activeProject.members = res.members || [];
                this.notify(window.ZenI18n.t('Usunięto członka'));
            } catch (e) {
                this.notify(window.ZenI18n.t('Błąd: ') + e.message);
            }
        },

        availableProjectUsers() {
            const currentIds = (this.activeProject?.members || []).map(m => m.user_id);
            if (this.activeProject?.manager_id) currentIds.push(this.activeProject.manager_id);
            return (this.users || []).filter(u => !currentIds.includes(u.id));
        }
    };
};
