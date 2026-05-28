const SPECIES_NAMES = {
    MA: 'Mänd', KU: 'Kuusk', KS: 'Kask', HB: 'Haab',
    LH: 'Lehis', LM: 'Sanglepp', LV: 'Hall lepp', TA: 'Tamm',
    SA: 'Saar', VA: 'Vaher',
};
const BONITEET_LABELS = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII'];

function formatEur(n) {
    if (n == null) return '—';
    return Math.round(n).toLocaleString('et-EE').replace(/,/g, ' ') + ' €';
}

function formatNum(n, decimals) {
    if (n == null) return '—';
    if (decimals !== undefined) return n.toFixed(decimals).replace('.', ',');
    return Math.round(n).toLocaleString('et-EE').replace(/,/g, ' ');
}

function speciesName(code) {
    return SPECIES_NAMES[code] || code;
}

function renderKataster(data) {
    const el = document.getElementById('kataster-info');
    el.innerHTML = `
        <div class="info-row"><span class="label">Number</span><span class="value">${data.number || '—'}</span></div>
        <div class="info-row"><span class="label">Pindala</span><span class="value">${formatNum(data.pindala_ha, 2)} ha</span></div>
        ${data.mets_pindala_ha ? `<div class="info-row"><span class="label">Metsamaa</span><span class="value">${formatNum(data.mets_pindala_ha, 2)} ha</span></div>` : ''}
        <div class="info-row"><span class="label">Sihtotstarve</span><span class="value">${data.sihtotstarve || '—'}</span></div>
        <div class="info-row"><span class="label">Omandivorm</span><span class="value">${data.omvorm || '—'}</span></div>
        ${data.mk_nimi ? `<div class="info-row"><span class="label">Maakond</span><span class="value">${data.mk_nimi}</span></div>` : ''}
        ${data.ov_nimi ? `<div class="info-row"><span class="label">Omavalitsus</span><span class="value">${data.ov_nimi}</span></div>` : ''}
        ${data.l_aadress ? `<div class="info-row"><span class="label">Aadress</span><span class="value">${data.l_aadress}</span></div>` : ''}
        ${data.maks_hind ? `<div class="info-row"><span class="label">Maksuhind</span><span class="value">${formatEur(data.maks_hind)}</span></div>` : ''}
    `;
}

function renderMets(data) {
    const el = document.getElementById('mets-info');
    if (!data) { el.innerHTML = '<p class="muted">Metsaandmeid pole</p>'; return; }
    const boniteet = BONITEET_LABELS[data.boniteedi_kood] || data.boniteedi_kood;
    let compHtml = '';
    if (data.liikide_koosseis && data.liikide_koosseis.length > 0) {
        compHtml = '<table class="comp-table">' + data.liikide_koosseis.map(s =>
            `<tr><td>${speciesName(s.puuliik_kood || s.puuliik)}</td><td>${s.osakaal}%</td><td class="bar-cell"><span class="comp-bar" style="width:${s.osakaal}%"></span></td></tr>`
        ).join('') + '</table>';
    }
    el.innerHTML = `
        <div class="info-row"><span class="label">Peapuuliik</span><span class="value">${speciesName(data.puuliik_kood || data.puuliik)}</span></div>
        <div class="info-row"><span class="label">Keskmine vanus</span><span class="value">${data.vanus} a</span></div>
        <div class="info-row"><span class="label">Tagavara</span><span class="value">${formatNum(data.tagavara_y_ha)} m³/ha</span></div>
        <div class="info-row"><span class="label">Boniteet</span><span class="value">${boniteet}</span></div>
        <div class="info-row"><span class="label">Pindala</span><span class="value">${formatNum(data.pindala_ha, 2)} ha</span></div>
        ${data.korgus ? `<div class="info-row"><span class="label">Kõrgus</span><span class="value">${formatNum(data.korgus, 1)} m</span></div>` : ''}
        ${compHtml}
    `;
}

function renderVaartus(data) {
    const el = document.getElementById('vaartus-info');
    if (!data) { el.innerHTML = '<p class="muted">Väärtuse andmeid pole</p>'; return; }
    el.innerHTML = `
        <div class="big-number">${formatEur(data.total_value_eur)}</div>
        <div class="info-row"><span class="label">Ühikuhind</span><span class="value">${formatEur(data.value_per_ha)} / ha</span></div>
        <div class="info-row"><span class="label">Seisuhind</span><span class="value">${formatNum(data.price_per_m3, 2)} €/m³</span></div>
        <div class="info-row"><span class="label">Tagavara</span><span class="value">${formatNum(data.tagavara_m3)} m³</span></div>
        <div class="info-row"><span class="label">Palk</span><span class="value">${formatNum(data.log_price, 2)} €/m³</span></div>
        <div class="info-row"><span class="label">Paberipuit</span><span class="value">${formatNum(data.pulp_price, 2)} €/m³</span></div>
    `;
}

function renderSinik(data) {
    const el = document.getElementById('sinik-info');
    if (!data) { el.innerHTML = '<p class="muted">Süsiniku andmeid pole</p>'; return; }
    el.innerHTML = `
        <div class="big-number">${formatNum(data.co2_tons_total, 0)} <span class="unit">tCO₂</span></div>
        <div class="info-row"><span class="label">CO₂ / ha</span><span class="value">${formatNum(data.co2_tons_ha, 1)} t</span></div>
        <div class="info-row"><span class="label">Biomass / ha</span><span class="value">${formatNum(data.total_biomass_tons_ha, 1)} t</span></div>
        <div class="info-row"><span class="label">Potentsiaalne tulu</span><span class="value">${formatEur(data.potential_income_eur)}</span></div>
    `;
}

function renderRiskid(data) {
    const el = document.getElementById('riskid-info');
    if (!data) { el.innerHTML = '<p class="muted">Riskiandmeid pole</p>'; return; }
    let html = '';

    // Raievanus
    if (data.raievanus) {
        const r = data.raievanus;
        html += `<div class="info-row"><span class="label">Raievanus</span>
            <span class="traffic-light ${r.status}"><span class="dot"></span>${r.label} (${Math.round(r.ratio * 100)}%)</span></div>`;
    }

    // Ürask
    if (data.yrask) {
        const y = data.yrask;
        const colors = ['#28a745', '#ffc107', '#fd7e14', '#e63946'];
        html += `<div class="info-row"><span class="label">Üraski risk</span>
            <span style="color:${colors[y.score]};font-weight:600">${y.label}${y.official_zone ? ' ⚠️' : ''}</span></div>`;
    }

    // Terviseindeks
    if (data.terviseindeks != null) {
        const t = data.terviseindeks;
        const barColor = t >= 70 ? '#28a745' : t >= 40 ? '#ffc107' : '#e63946';
        html += `<div class="info-row"><span class="label">Terviseindeks</span><span class="value">${t}/100</span></div>
            <div class="progress-bar"><div class="fill" style="width:${t}%;background:${barColor}"></div></div>`;
    }

    // Karuputk
    if (data.karuputk) {
        html += `<div class="info-row"><span class="label">Karuputk</span><span style="color:var(--danger);font-weight:600">⚠️ Leitud</span></div>`;
    }

    // Lageraieala
    if (data.lageraieala) {
        html += `<div class="info-row"><span class="label">Lageraieala</span><span class="value">${data.lageraieala}</span></div>`;
    }

    el.innerHTML = html || '<p class="muted">Riskiandmeid pole</p>';
}

function renderKitsendused(data) {
    const el = document.getElementById('kitsendused-info');
    if (!data || data.length === 0) { el.innerHTML = '<p class="muted">Kitsendusi ei leitud</p>'; return; }
    let html = '<table><thead><tr><th>Tüüp</th><th>Kirjeldus</th><th>Allikas</th></tr></thead><tbody>';
    data.forEach(k => {
        html += `<tr><td><strong>${k.tyyp}</strong></td><td>${k.kirjeldus}</td><td class="muted">${k.allikas}</td></tr>`;
    });
    html += '</tbody></table>';
    el.innerHTML = html;
}

function renderToetused(data) {
    const el = document.getElementById('toetused-info');
    if (!data || data.length === 0) { el.innerHTML = '<p class="muted">Toetusi ei leitud</p>'; return; }
    let html = '<table><thead><tr><th></th><th>Programm</th><th>Summa</th><th>Asutus</th></tr></thead><tbody>';
    data.forEach(t => {
        const icon = t.sobib ? '✅' : '❌';
        html += `<tr><td>${icon}</td><td><strong>${t.nimi}</strong>${t.taotlusvoor ? `<br><span class="muted">${t.taotlusvoor}</span>` : ''}</td><td>${t.summa}</td><td>${t.asutus}</td></tr>`;
    });
    html += '</tbody></table>';
    el.innerHTML = html;
}

function showLoading() {
    document.getElementById('loading').classList.remove('hidden');
    document.getElementById('dashboard').classList.add('hidden');
    document.getElementById('error-msg').classList.add('hidden');
}

function hideLoading() {
    document.getElementById('loading').classList.add('hidden');
}

function showError(msg) {
    const el = document.getElementById('error-msg');
    el.textContent = msg;
    el.classList.remove('hidden');
    document.getElementById('loading').classList.add('hidden');
    document.getElementById('dashboard').classList.add('hidden');
}

function showDashboard() {
    document.getElementById('dashboard').classList.remove('hidden');
}
