let currentData = null;

document.addEventListener('DOMContentLoaded', () => {
    initMap();
    document.getElementById('kataster-input').focus();

    document.getElementById('search-btn').addEventListener('click', doSearch);
    document.getElementById('kataster-input').addEventListener('keydown', e => {
        if (e.key === 'Enter') doSearch();
    });

    document.getElementById('eudr-btn').addEventListener('click', () => {
        const nr = document.getElementById('kataster-input').value.trim();
        if (nr) exportEUDR(nr).catch(err => showError(err.message));
    });

    // Layer toggles
    document.getElementById('layer-kitsendused').addEventListener('change', e => toggleOverlayLayer('kitsendused', e.target.checked));
    document.getElementById('layer-yrask').addEventListener('change', e => toggleOverlayLayer('yrask', e.target.checked));
    document.getElementById('layer-lageraie').addEventListener('change', e => toggleOverlayLayer('lageraie', e.target.checked));
    document.getElementById('layer-karuputk').addEventListener('change', e => toggleOverlayLayer('karuputk', e.target.checked));
    document.getElementById('layer-oksjonid').addEventListener('change', e => toggleOverlayLayer('oksjonid', e.target.checked));
});

async function doSearch() {
    const nr = document.getElementById('kataster-input').value.trim();
    if (!nr) { showError('Sisesta katastri number.'); return; }

    // Disable button during search
    const btn = document.getElementById('search-btn');
    btn.disabled = true;
    btn.querySelector('.btn-text').textContent = 'Laadin...';

    showLoading();

    try {
        const data = await searchParcel(nr);
        currentData = data;

        // Kataster
        if (data.kataster) renderKataster(data.kataster);

        // Map - show parcel first
        if (data.kataster && data.kataster.geometry) {
            showParcel(data.kataster.geometry);
        }

        // Mets
        renderMets(data.mets);

        // Väärtus
        renderVaartus(data.vaartus);

        // Süsinik
        renderSinik(data.sinik);

        // Riskid
        renderRiskid(data.riskid);

        // Kitsendused
        renderKitsendused(data.kitsendused);

        // Toetused
        renderToetused(data.toetused);

        // Charts
        if (data.mets && data.mets.liikide_koosseis) {
            renderCompositionChart(data.mets.liikide_koosseis);
        }
        if (data.vaartus) {
            renderValueChart(data.vaartus);
        }

        // Overlay layers
        if (data.kitsendused) {
            toggleOverlayLayer('kitsendused', document.getElementById('layer-kitsendused').checked);
        }

        hideLoading();
        showDashboard();

        // Fix Leaflet map size after dashboard becomes visible
        setTimeout(() => {
            map.invalidateSize();
            if (data.kataster && data.kataster.geometry) {
                fitToParcel(data.kataster.geometry);
            }
        }, 150);
    } catch (err) {
        hideLoading();
        showError(err.message);
    } finally {
        btn.disabled = false;
        btn.querySelector('.btn-text').textContent = 'Analüüsi';
    }
}
