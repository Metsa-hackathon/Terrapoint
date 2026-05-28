let map;
let parcelLayer = null;
const overlayLayers = {};

function initMap() {
    map = L.map('map', { zoomControl: true }).setView([58.5, 25.0], 7);

    const kaart = L.tileLayer('https://tiles.maaamet.ee/tm/tms/1.0.0/kaart@GMC/{z}/{x}/{y}.png', {
        tms: true,
        zoomReverse: true,
        maxZoom: 14,
        attribution: '&copy; Maa-amet',
    });

    const foto = L.tileLayer('https://tiles.maaamet.ee/tm/tms/1.0.0/foto@GMC/{z}/{x}/{y}.png', {
        tms: true,
        zoomReverse: true,
        maxZoom: 14,
        attribution: '&copy; Maa-amet',
    });

    kaart.addTo(map);

    L.control.layers({
        'Kaart': kaart,
        'Ortofoto': foto,
    }).addTo(map);
}

function showParcel(geometry) {
    if (parcelLayer) map.removeLayer(parcelLayer);
    parcelLayer = L.geoJSON(geometry, {
        style: { color: '#2d5016', weight: 3, fillColor: '#4a7c28', fillOpacity: 0.25 },
    }).addTo(map);
}

function fitToParcel(geometry) {
    if (parcelLayer) {
        map.fitBounds(parcelLayer.getBounds(), { padding: [30, 30] });
    }
}

function addOverlayLayer(name, features, color, isMarker) {
    removeOverlayLayer(name);
    if (!features || features.length === 0) return;

    if (isMarker) {
        const markers = features.map(f => {
            const coords = f.geometry && f.geometry.coordinates;
            if (!coords) return null;
            const props = f.properties || {};
            const label = props.purpose || props.nimi || 'Oksjon';
            return L.marker([coords[1], coords[0]]).bindPopup(`<b>${label}</b><br>${props.starting_price ? props.starting_price + ' €' : ''}`);
        }).filter(Boolean);
        overlayLayers[name] = L.layerGroup(markers).addTo(map);
    } else {
        overlayLayers[name] = L.geoJSON({ type: 'FeatureCollection', features }, {
            style: { color: color, weight: 2, fillColor: color, fillOpacity: 0.2 },
        }).addTo(map);
    }
}

function removeOverlayLayer(name) {
    if (overlayLayers[name]) {
        map.removeLayer(overlayLayers[name]);
        delete overlayLayers[name];
    }
}

function toggleOverlayLayer(name, enabled) {
    if (enabled && overlayLayers[name]) {
        overlayLayers[name].addTo(map);
    } else if (!enabled && overlayLayers[name]) {
        map.removeLayer(overlayLayers[name]);
    }
}
