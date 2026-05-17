    // ── WebSocket manager ────────────────────────────────────
    const WS_BASE = 'ws://localhost:8001';
    let ws = null;

    const WebSocketManager = {
    connect(role, userId, onMessage) {
        const url = `${WS_BASE}/ws/${role}/${userId}`;
        ws = new WebSocket(url);

        ws.onopen    = () => console.log(`[WS] Connected as ${role}`);
        ws.onmessage = (e) => onMessage(JSON.parse(e.data));
        ws.onerror   = (e) => console.error('[WS] Error:', e);
        ws.onclose   = ()  => console.log('[WS] Disconnected');
    },

    send(data) {
        if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(data));
        }
    },

    sendLocation(lat, lng, clientId) {
        this.send({ type: 'location', lat, lng, client_id: clientId });
    },

    disconnect() {
        if (ws) { ws.close(); ws = null; }
    }
    };