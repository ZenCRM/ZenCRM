window.renderZenDashboard = async function(app) {
    await app.$nextTick();
    const donut = document.getElementById('funnelChart');
    const bars = document.getElementById('leadValueChart');
    const tasks = document.getElementById('taskStatusChart');
    if (!donut || !bars || app.currentView !== 'dashboard') return;
    app.chartError = window.Chart ? '' : window.ZenI18n.t('Wykresy są niedostępne. Odśwież stronę, aby ponowić ładowanie biblioteki.');
    if (!window.Chart) return;
    const stages = app.leadStages;
    const counts = stages.map(s => Number(app.stats.funnel?.[s.id] || 0));
    const total = counts.reduce((a,b) => a+b, 0);
    const styles = getComputedStyle(document.body);
    const muted = styles.getPropertyValue('--wm-muted').trim();
    const border = styles.getPropertyValue('--wm-border').trim();
    const surface = styles.getPropertyValue('--wm-surface').trim();
    const colors = stages.map(s => s.accent);
    const money = n => new Intl.NumberFormat(window.ZenI18n.locale, { style: 'currency', currency: window.ZenI18n.t('PLN'), maximumFractionDigits: 0 }).format(n);
    const common = {
        responsive: true, maintainAspectRatio: false,
        animation: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? false : { duration: 350 },
        plugins: { legend: { display: false } },
    };
    // Keep Chart instances outside Alpine's reactive state.
    Chart.getChart(donut)?.destroy();
    Chart.getChart(bars)?.destroy();
    if (tasks) Chart.getChart(tasks)?.destroy();
    new Chart(donut, {
        type: 'doughnut',
        data: {
            labels: total ? stages.map(s => s.label) : [window.ZenI18n.t('Brak leadów')],
            datasets: [{ data: total ? counts : [1], backgroundColor: total ? colors : [border],
                borderColor: surface, borderWidth: 4, hoverOffset: total ? 6 : 0, borderRadius: 5 }],
        },
        options: { ...common, cutout: '76%', layout: { padding: 10 }, plugins: {
            legend: { display: false },
            tooltip: { enabled: total > 0, displayColors: true, padding: 12, callbacks: {
                label: c => ` ${c.label}: ${c.raw} (${Math.round(Number(c.raw) / total * 100)}%)`,
            } },
        } },
    });
    new Chart(bars, {
        type: 'bar',
        data: { labels: stages.map(s => s.label), datasets: [{
            data: stages.map(s => Number(app.stats.lead_values?.[s.id] || 0)),
            backgroundColor: colors, borderRadius: 6, maxBarThickness: 20,
        }] },
        options: { ...common, indexAxis: 'y', plugins: {
            legend: { display: false }, tooltip: { padding: 12, callbacks: { label: c => ' ' + money(c.raw) } },
        }, scales: {
            x: { beginAtZero: true, grid: { color: border }, border: { display: false }, ticks: {
                color: muted, maxTicksLimit: 5,
                callback: n => new Intl.NumberFormat(window.ZenI18n.locale, { notation: 'compact', maximumFractionDigits: 1 }).format(n) + window.ZenI18n.t(' zł'),
            } },
            y: { grid: { display: false }, border: { display: false }, ticks: { color: muted, font: { size: 12 } } },
        } },
    });
    if (tasks) {
        const statuses = app.dashboardTaskStages.map(stage => stage.id);
        const values = statuses.map(status => Number(app.stats.task_status?.[status] || 0));
        new Chart(tasks, {
            type: 'bar',
            data: { labels: app.dashboardTaskStages.map(stage => stage.label),
                datasets: [{ data: values, backgroundColor: statuses.map(status => app.taskStageColor(status)), borderRadius: 8, maxBarThickness: 52 }] },
            options: { ...common, plugins: { legend: { display: false }, tooltip: { padding: 12, callbacks: { label: c => ` ${c.raw}` } } },
                scales: { x: { grid: { display: false }, border: { display: false }, ticks: { color: muted } },
                    y: { beginAtZero: true, grid: { color: border }, border: { display: false }, ticks: { color: muted, precision: 0 } } } },
        });
    }
};
