const SPECIES_COLORS = {
    KU: '#2d5016', MA: '#4a7c28', KS: '#7ab356', HB: '#a0c4a0',
    LH: '#3d6b1e', LM: '#6b8e23', LV: '#7a9e3a', TA: '#5c4033',
    SA: '#7a5c3a', VA: '#8b6f47',
};

const VALUE_COLORS = {
    log: '#2d5016',
    pulp: '#4a7c28',
    harvest: '#e63946',
    transport: '#f4a261',
};

let compositionChart = null;
let valueChart = null;

// Chart.js global defaults
Chart.defaults.font.family = "'Inter', -apple-system, BlinkMacSystemFont, sans-serif";
Chart.defaults.font.size = 12;
Chart.defaults.color = '#4a5568';

function renderCompositionChart(species) {
    const ctx = document.getElementById('chart-composition');
    if (!ctx || !species || species.length === 0) return;

    if (compositionChart) compositionChart.destroy();

    const names = { MA: 'Mänd', KU: 'Kuusk', KS: 'Kask', HB: 'Haab', LH: 'Lehis', LM: 'Sanglepp', LV: 'Hall lepp', TA: 'Tamm', SA: 'Saar', VA: 'Vaher' };
    const labels = species.map(s => names[s.puuliik_kood || s.puuliik] || s.puuliik);
    const values = species.map(s => s.osakaal);
    const colors = species.map(s => SPECIES_COLORS[s.puuliik_kood || s.puuliik] || '#6c757d');

    compositionChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels,
            datasets: [{
                data: values,
                backgroundColor: colors,
                borderWidth: 3,
                borderColor: '#ffffff',
                hoverBorderWidth: 0,
                hoverOffset: 6,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            cutout: '62%',
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 16,
                        usePointStyle: true,
                        pointStyleWidth: 10,
                        font: { size: 12, weight: '500' },
                    },
                },
                tooltip: {
                    backgroundColor: 'rgba(26, 29, 35, 0.9)',
                    titleFont: { weight: '600' },
                    bodyFont: { size: 13 },
                    padding: 12,
                    cornerRadius: 8,
                    displayColors: true,
                    callbacks: {
                        label: (ctx) => ` ${ctx.label}: ${ctx.parsed}%`,
                    },
                },
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
                data: [
                    Math.round(logValue),
                    Math.round(pulpValue),
                    Math.round(harvestCost),
                    Math.round(transportCost),
                ],
                backgroundColor: [
                    VALUE_COLORS.log,
                    VALUE_COLORS.pulp,
                    VALUE_COLORS.harvest,
                    VALUE_COLORS.transport,
                ],
                borderRadius: 8,
                borderSkipped: false,
                barPercentage: 0.7,
                categoryPercentage: 0.8,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: 'rgba(26, 29, 35, 0.9)',
                    titleFont: { weight: '600' },
                    bodyFont: { size: 13 },
                    padding: 12,
                    cornerRadius: 8,
                    callbacks: {
                        label: (ctx) => {
                            const v = ctx.parsed.y;
                            return ` ${v.toLocaleString('et-EE').replace(/,/g, ' ')} €`;
                        },
                    },
                },
            },
            scales: {
                x: {
                    grid: { display: false },
                    ticks: {
                        font: { size: 11, weight: '500' },
                        color: '#4a5568',
                    },
                },
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0,0,0,0.04)',
                        drawBorder: false,
                    },
                    ticks: {
                        font: { size: 11 },
                        color: '#8896a6',
                        callback: v => {
                            if (v >= 1000) return (v / 1000).toFixed(0) + 'k €';
                            return v + ' €';
                        },
                    },
                },
            },
        },
    });
}
