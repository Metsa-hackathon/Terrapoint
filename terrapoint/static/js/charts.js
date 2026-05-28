const SPECIES_COLORS = {
    KU: '#2d5016', MA: '#4a7c28', KS: '#8fbc8f', HB: '#a0c4a0',
    LH: '#3d6b1e', LM: '#6b8e23', LV: '#7a9e3a', TA: '#5c4033',
    SA: '#7a5c3a', VA: '#8b6f47',
};

let compositionChart = null;
let valueChart = null;

function renderCompositionChart(species) {
    const ctx = document.getElementById('chart-composition');
    if (!ctx || !species || species.length === 0) return;

    if (compositionChart) compositionChart.destroy();

    const labels = species.map(s => {
        const names = { MA: 'Mänd', KU: 'Kuusk', KS: 'Kask', HB: 'Haab', LH: 'Lehis', LM: 'Sanglepp', LV: 'Hall lepp', TA: 'Tamm', SA: 'Saar', VA: 'Vaher' };
        return names[s.puuliik_kood || s.puuliik] || s.puuliik;
    });
    const values = species.map(s => s.osakaal);
    const colors = species.map(s => SPECIES_COLORS[s.puuliik_kood || s.puuliik] || '#6c757d');

    compositionChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels,
            datasets: [{ data: values, backgroundColor: colors, borderWidth: 2, borderColor: '#fff' }],
        },
        options: {
            responsive: true,
            plugins: {
                legend: { position: 'bottom', labels: { padding: 12, font: { size: 12 } } },
            },
        },
    });
}

function renderValueChart(data) {
    const ctx = document.getElementById('chart-value');
    if (!ctx || !data) return;

    if (valueChart) valueChart.destroy();

    const harvestCost = data.tagavara_m3 * 18;
    const transportCost = data.tagavara_m3 * 9;
    const logValue = data.tagavara_m3 * 0.6 * data.log_price;
    const pulpValue = data.tagavara_m3 * 0.4 * data.pulp_price;

    valueChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Palk', 'Paberipuit', 'Varumine', 'Transport'],
            datasets: [{
                data: [Math.round(logValue), Math.round(pulpValue), Math.round(harvestCost), Math.round(transportCost)],
                backgroundColor: ['#2d5016', '#4a7c28', '#e63946', '#f4a261'],
                borderRadius: 6,
            }],
        },
        options: {
            responsive: true,
            plugins: { legend: { display: false } },
            scales: {
                y: { beginAtZero: true, ticks: { callback: v => v.toLocaleString('et-EE').replace(/,/g, ' ') + ' €' } },
            },
        },
    });
}
