const API_BASE = '/api';

async function searchParcel(katasterNr) {
    const res = await fetch(`${API_BASE}/search/${encodeURIComponent(katasterNr)}`);
    if (!res.ok) {
        const text = await res.text().catch(() => '');
        throw new Error(res.status === 404 ? 'Katastri numbrit ei leitud.' : `Serveri viga: ${res.status}`);
    }
    return res.json();
}

async function exportEUDR(katasterNr) {
    const res = await fetch(`${API_BASE}/export/eudr/${encodeURIComponent(katasterNr)}`);
    if (!res.ok) throw new Error(`EUDR eksport ebaõnnestus: ${res.status}`);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `eudr_${katasterNr.replace(/:/g, '_')}.geojson`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}
