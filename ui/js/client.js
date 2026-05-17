    // ── Client page logic ────────────────────────────────────
    let currentWorkers = [];
    let activeJobId    = null;
    let bookedWorker   = null;

    document.addEventListener('DOMContentLoaded', () => {
    if (!requireAuth()) return;
    if (Auth.getRole() !== 'client') { redirectTo('/ui/pages/worker.html'); return; }

    // Show user name
    const user = Auth.getUser();
    if (user) {
        document.getElementById('user-name').textContent = user.full_name;
    }

    // Init map
    initMap('map');
    const pin = addClientPin(27.7172, 85.3240);

    // Update coords when pin dragged
    pin.on('dragend', e => {
        const pos = e.target.getLatLng();
        updateCoordInputs(pos.lat, pos.lng);
    });

    // Click map to move pin
    map.on('click', e => {
        pin.setLatLng(e.latlng);
        updateCoordInputs(e.latlng.lat, e.latlng.lng);
        showToast('📍 Location updated');
    });

    // Char counter
    document.getElementById('job-desc')
        ?.addEventListener('input', updateCharCount);
    });

    // ── Coord inputs ─────────────────────────────────────────
    function updateCoordInputs(lat, lng) {
    document.getElementById('lat-input').value = lat.toFixed(4);
    document.getElementById('lng-input').value = lng.toFixed(4);
    document.getElementById('location-display').textContent =
        `${lat.toFixed(4)}°N, ${lng.toFixed(4)}°E`;
    }

    function onCoordChange() {
    const lat = parseFloat(document.getElementById('lat-input').value);
    const lng = parseFloat(document.getElementById('lng-input').value);
    if (!isNaN(lat) && !isNaN(lng)) {
        addClientPin(lat, lng);
        map.panTo([lat, lng]);
    }
    }

    // ── GPS ──────────────────────────────────────────────────
    function detectGPS() {
    if (!navigator.geolocation) { showToast('GPS not available', 'error'); return; }
    showToast('📡 Detecting GPS...');
    navigator.geolocation.getCurrentPosition(
        pos => {
        const { latitude: lat, longitude: lng } = pos.coords;
        updateCoordInputs(lat, lng);
        addClientPin(lat, lng);
        map.setView([lat, lng], 15);
        showToast('✅ GPS location found!');
        },
        () => showToast('GPS failed — using default location', 'error')
    );
    }

    // ── Quick chips ──────────────────────────────────────────
    function setChip(text) {
    const ta = document.getElementById('job-desc');
    ta.value = text;
    updateCharCount();
    ta.focus();
    }

    function updateCharCount() {
    const ta  = document.getElementById('job-desc');
    const cc  = document.getElementById('char-count');
    const len = ta.value.length;
    cc.textContent = `${len}/300`;
    cc.className   = 'char-count' + (len > 270 ? ' over' : len > 220 ? ' warn' : '');
    }

    // ── Validation ───────────────────────────────────────────
    function validateJobForm(desc, lat, lng) {
    if (!desc.trim()) return 'Please describe your problem.';
    if (desc.length < 5) return 'Description too short — add more detail.';
    if (desc.length > 300) return 'Description too long — max 300 characters.';
    if (isNaN(lat) || isNaN(lng)) return 'Invalid coordinates.';
    if (lat < 26 || lat > 30 || lng < 80 || lng > 90)
        return 'Location appears outside Nepal — check coordinates.';
    return null;
    }

    // ── Find workers ─────────────────────────────────────────
    async function findWorkers() {
    const desc = document.getElementById('job-desc').value.trim();
    const lat  = parseFloat(document.getElementById('lat-input').value);
    const lng  = parseFloat(document.getElementById('lng-input').value);
    const vm   = document.getElementById('validation-msg');
    const btn  = document.getElementById('find-btn');

    const error = validateJobForm(desc, lat, lng);
    if (error) {
        vm.textContent = `⚠️ ${error}`;
        vm.className   = 'validation error';
        return;
    }

    vm.className = 'validation hidden';
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Finding workers...';
    clearWorkerPins();

    try {
        const data = await JobsAPI.match(desc, lat, lng);
        currentWorkers = data.workers;
        renderResults(data.job, data.workers, lat, lng);
        addWorkerPins(data.workers);
    } catch (err) {
        vm.textContent = `❌ ${err.message}`;
        vm.className   = 'validation error';
        showToast(err.message, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '🔍 Find Workers';
    }
    }

    // ── Render results ────────────────────────────────────────
    function renderResults(job, workers, lat, lng) {
    const area    = document.getElementById('results-area');
    const medals  = ['🥇','🥈','🥉'];
    const maxScore = workers[0]?.score || 1;

    const urgencyClass = { high:'badge-high', medium:'badge-medium', low:'badge-low' };

    area.innerHTML = `
        <div class="job-pills">
        <span class="badge badge-skill">🔧 ${job.skill_category.replace('_',' ').toUpperCase()}</span>
        <span class="badge ${urgencyClass[job.urgency] || 'badge-low'}">⚡ ${job.urgency.toUpperCase()}</span>
        ${job.location_hint ? `<span class="badge badge-skill">📍 ${job.location_hint}</span>` : ''}
        </div>
        <p class="text-sm muted mb-12">${workers.length} workers found nearby</p>

        ${workers.map((w, i) => `
        <div class="worker-card ${i===0?'top':''}" onclick="highlightWorker(${i})">
            ${i===0 ? '<div class="top-badge">TOP PICK</div>' : ''}

            <div class="card-header">
            <div>
                <div class="worker-name">${medals[i]} ${w.name}</div>
                <div class="worker-bio">${w.bio}</div>
            </div>
            <div class="rating-badge">⭐ ${w.rating}</div>
            </div>

            <div class="card-stats">
            <div class="stat">
                <span class="val">${w.distance_km} km</span>
                <span class="lbl">Distance</span>
            </div>
            <div class="stat">
                <span class="val">Rs.${w.hourly_rate}</span>
                <span class="lbl">Per hour</span>
            </div>
            <div class="stat">
                <span class="val">${w.total_reviews}</span>
                <span class="lbl">Reviews</span>
            </div>
            </div>

            <div class="skill-tags">
            ${w.skill_tags.map(t => `<span class="skill-tag">${t}</span>`).join('')}
            </div>

            <div class="score-bar-wrap">
            <div class="score-bar-label">
                <span>Match score</span>
                <span class="accent">${Math.round(w.score*100)}%</span>
            </div>
            <div class="score-bar">
                <div class="score-bar-fill" style="width:${Math.round((w.score/maxScore)*100)}%"></div>
            </div>
            </div>

            <button class="btn ${i===0?'btn-primary':'btn-secondary'} btn-full"
                    id="book-${w.id}"
                    onclick="event.stopPropagation(); bookWorker('${w.id}','${w.name}')">
            ${i===0 ? '📞 Book Now' : `Book ${w.name}`}
            </button>
        </div>
        `).join('')}

        <button class="btn btn-secondary btn-full mt-12"
                onclick="resetSearch()">↩ New Search</button>
    `;
    }

    function highlightWorker(i) {
    if (workerMarkers[i]) workerMarkers[i].openPopup();
    }

    function bookWorker(id, name) {
    if (bookedWorker) return;
    bookedWorker = id;
    const btn = document.getElementById(`book-${id}`);
    if (btn) {
        btn.textContent = '✅ Booked!';
        btn.className   = 'btn btn-full';
        btn.style.background = 'rgba(0,212,170,0.15)';
        btn.style.color      = 'var(--accent)';
        btn.style.border     = '1px solid var(--accent)';
    }
    showToast(`✅ ${name} is on the way!`);
    }

    function resetSearch() {
    bookedWorker   = null;
    currentWorkers = [];
    clearWorkerPins();
    document.getElementById('results-area').innerHTML = `
        <div class="empty-state">
        <div class="icon">🗺️</div>
        <p>Describe your problem and we'll find the best worker near you.</p>
        </div>
    `;
    document.getElementById('job-desc').value = '';
    document.getElementById('char-count').textContent = '0/300';
    document.getElementById('validation-msg').className = 'validation hidden';
    map.setView(KTM, 14);
    }

    // Enter to search
    document.addEventListener('keydown', e => {
    if (e.ctrlKey && e.key === 'Enter') findWorkers();
    });