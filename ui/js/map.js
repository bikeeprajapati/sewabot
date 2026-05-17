    // ── Map initialization ───────────────────────────────────
    let map, clientMarker, workerMarkers = [], polylines = [];

    const KTM = [27.7172, 85.3240];

    function initMap(containerId = 'map') {
    map = L.map(containerId, { zoomControl: false })
            .setView(KTM, 14);

    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '© OpenStreetMap © CartoDB',
        maxZoom: 19
    }).addTo(map);

    L.control.zoom({ position: 'bottomright' }).addTo(map);
    return map;
    }

    function addClientPin(lat, lng) {
    if (clientMarker) map.removeLayer(clientMarker);

    const icon = L.divIcon({
        html: `<div style="width:14px;height:14px;border-radius:50%;
                    background:var(--danger);border:3px solid white;
                    box-shadow:0 0 12px rgba(255,71,87,0.8);"></div>`,
        iconSize: [14,14], iconAnchor: [7,7], className: ''
    });

    clientMarker = L.marker([lat, lng], { icon, draggable: true })
        .addTo(map)
        .bindPopup('<b>📍 You are here</b><br>Drag to move');

    return clientMarker;
    }

    function addWorkerPins(workers) {
    clearWorkerPins();
    const colors  = ['#00d4aa', '#0099ff', '#a855f7'];
    const medals  = ['1', '2', '3'];
    const clientPos = clientMarker?.getLatLng();

    workers.forEach((w, i) => {
        const icon = L.divIcon({
        html: `<div style="background:${colors[i]};color:#000;border-radius:50%;
                    width:34px;height:34px;display:flex;align-items:center;
                    justify-content:center;font-size:14px;font-weight:800;
                    border:2px solid white;box-shadow:0 0 12px ${colors[i]}80;
                    font-family:'Syne',sans-serif;">${medals[i]}</div>`,
        iconSize: [34,34], iconAnchor: [17,17], className: ''
        });

        const m = L.marker([w.lat, w.lng], { icon })
        .addTo(map)
        .bindPopup(`
            <div style="font-family:'DM Sans',sans-serif;min-width:160px;">
            <b>${w.name}</b><br>
            <span style="color:#888;font-size:12px;">${w.skill_tags?.join(', ')}</span><br>
            ⭐ ${w.rating} · ${w.distance_km} km<br>
            <span style="color:#00d4aa;font-weight:600;">Rs. ${w.hourly_rate}/hr</span>
            </div>
        `);
        workerMarkers.push(m);

        if (clientPos) {
        const line = L.polyline(
            [[clientPos.lat, clientPos.lng], [w.lat, w.lng]],
            { color: colors[i], weight: 2, opacity: 0.6, dashArray: '6' }
        ).addTo(map);
        polylines.push(line);
        }
    });

    // Fit map
    if (clientPos) {
        const bounds = [[clientPos.lat, clientPos.lng],
                        ...workers.map(w => [w.lat, w.lng])];
        map.fitBounds(bounds, { padding: [40,40] });
    }
    }

    function clearWorkerPins() {
    workerMarkers.forEach(m => map.removeLayer(m));
    polylines.forEach(p => map.removeLayer(p));
    workerMarkers = [];
    polylines = [];
    }

    function updateWorkerPin(workerId, lat, lng) {
    // Update existing pin position for live tracking
    const pin = workerMarkers.find(m => m.options.workerId === workerId);
    if (pin) pin.setLatLng([lat, lng]);
    }

    function getClientLocation() {
    return {
        lat: clientMarker ? clientMarker.getLatLng().lat : KTM[0],
        lng: clientMarker ? clientMarker.getLatLng().lng : KTM[1]
    };
    }