let map;
let parcelLayer = null;
const overlayLayers = {};

function initMap() {
    map = L.map('map', {
        zoomControl: true,
        attributionControl: true,
    }).setView([58.5, 25.0], 7);

    const kaart = L.tileLayer('https://tiles.maaamet.ee/tm/tms/1.0.0/kaart@GMC/{z}/{x}/{y}.png', {
        tms: true,
        zoomReverse: true,
        maxZoom: 14,
        attribution: '&copy; <a href="https://www.maaamet.ee/">Maa-amet</a>',
    });

    const foto = L.tileLayer('https://tiles.maaamet.ee/tm/tms/1.0.0/foto@GMC/{z}/{x}/{y}.png', {
        tms: true,
        zoomReverse: true,
        maxZoom: 14,
        attribution: '&copy; <a href="https://www.maaamet.ee/">Maa-amet</a>',
    });

    kaart.addTo(map);

    L.control.layers({
        'Kaart': kaart,
        'Ortofoto': foto,
    }, null, { position: 'bottomleft' }).addTo(map);

    // Center button
    var CenterControl = L.Control.extend({
        options: { position: 'bottomleft' },
        onAdd: function() {
            var btn = L.DomUtil.create('div', 'leaflet-control-zoom leaflet-bar leaflet-control center-control');
            btn.innerHTML = '<a href="#" title="Tsentreeri kaart" role="button" aria-label="Center map"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M12 2v4m0 12v4M2 12h4m12 0h4"/></svg></a>';
            L.DomEvent.disableClickPropagation(btn);
            btn.firstChild.addEventListener('click', function(e) {
                e.preventDefault();
                if (parcelLayer) {
                    map.fitBounds(parcelLayer.getBounds(), { padding: [40, 40], maxZoom: 15 });
                } else {
                    map.flyTo([58.5, 25.0], 7, { duration: 1.2 });
                }
            });
            return btn;
        }
    });
    new CenterControl().addTo(map);
}

function showParcel(geometry) {
    if (parcelLayer) map.removeLayer(parcelLayer);
    parcelLayer = L.geoJSON(geometry, {
        style: {
            color: '#2d5016',
            weight: 3,
            opacity: 0.9,
            fillColor: '#4a7c28',
            fillOpacity: 0.15,
            dashArray: null,
        },
    }).addTo(map);
}

function fitToParcel(geometry) {
    if (parcelLayer) {
        map.fitBounds(parcelLayer.getBounds(), { padding: [40, 40], maxZoom: 15 });
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
            return L.marker([coords[1], coords[0]], {
                icon: L.divIcon({
                    className: 'custom-marker',
                    html: `<div style="background:${color};width:12px;height:12px;border-radius:50%;border:2px solid white;box-shadow:0 2px 6px rgba(0,0,0,0.3);"></div>`,
                    iconSize: [12, 12],
                    iconAnchor: [6, 6],
                }),
            }).bindPopup(`<b>${label}</b><br>${props.starting_price ? props.starting_price + ' €' : ''}`);
        }).filter(Boolean);
        overlayLayers[name] = L.layerGroup(markers).addTo(map);
    } else {
        overlayLayers[name] = L.geoJSON({ type: 'FeatureCollection', features }, {
            style: {
                color: color,
                weight: 2,
                opacity: 0.7,
                fillColor: color,
                fillOpacity: 0.15,
            },
        }).addTo(map);
    }
}

function removeOverlayLayer(name) {
    if (overlayLayers[name]) {
        map.removeLayer(overlayLayers[name]);
        delete overlayLayers[name];
    }
}

function toggleOverlayLayer(name, visible) {
    if (visible) {
        const colors = {
            kitsendused: '#e63946',
            yrask: '#fd7e14',
            lageraie: '#6c757d',
            karuputk: '#d63384',
            oksjonid: '#0d6efd',
        };
        if (currentData) {
            let features = [];
            if (name === 'kitsendused' && currentData.kitsendused) {
                features = currentData.kitsendused_raw || [];
            } else if (currentData.kitsendused_raw) {
                // Use raw overlay data if available
            }
            // For now, just show/hide the layer
            if (overlayLayers[name]) {
                map.addLayer(overlayLayers[name]);
            }
        }
    } else {
        removeOverlayLayer(name);
    }
}
