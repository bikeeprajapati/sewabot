    // ── Worker dashboard logic ───────────────────────────────
    document.addEventListener('DOMContentLoaded', () => {
    if (!requireAuth()) return;
    if (Auth.getRole() !== 'worker') { redirectTo('/ui/pages/client.html'); return; }

    const user = Auth.getUser();
    if (user) document.getElementById('worker-name').textContent = user.full_name;

    // Init worker map
    initMap('worker-map');
    addClientPin(27.7172, 85.3240);

    renderMockJobs();
    });

    // ── Availability toggle ───────────────────────────────────
    function toggleAvailability(cb) {
    const label = document.getElementById('availability-label');
    label.textContent = cb.checked ? '🟢 Available for jobs' : '🔴 Offline';
    showToast(cb.checked ? '🟢 You are now online' : '🔴 You are now offline');
    }

    // ── Mock jobs ─────────────────────────────────────────────
    const mockJobs = [
    { id:'j1', client:'Hari Prasad',  desc:'Kitchen pipe leaking badly',       urgency:'high',   location:'Thamel',    distance:'1.2 km', rate:500 },
    { id:'j2', client:'Sunita KC',    desc:'Bathroom drain completely blocked', urgency:'medium', location:'Baneshwor', distance:'3.4 km', rate:500 },
    { id:'j3', client:'Ramesh Shah',  desc:'Water pump not working',           urgency:'low',    location:'Lalitpur',  distance:'5.1 km', rate:500 },
    ];

    function renderMockJobs() {
    const list = document.getElementById('job-list');
    if (!list) return;

    list.innerHTML = mockJobs.map(job => `
        <div class="incoming-job" id="job-${job.id}">
        <div class="job-meta">
            <span class="client-name">${job.client}</span>
            <span class="badge badge-${job.urgency}">${
            job.urgency === 'high' ? '🔴' : job.urgency === 'medium' ? '🟡' : '🟢'
            } ${job.urgency}</span>
        </div>
        <div class="job-desc">${job.desc}</div>
        <div class="job-footer">
            <span>📍 ${job.location} · ${job.distance}</span>
            <span>Rs. ${job.rate}/hr</span>
        </div>
        <div class="action-btns">
            <button class="accept-btn" onclick="acceptJob('${job.id}', '${job.client}')">✅ Accept</button>
            <button class="decline-btn" onclick="declineJob('${job.id}')">❌ Decline</button>
        </div>
        </div>
    `).join('');
    }

    function acceptJob(jobId, clientName) {
    const card = document.getElementById(`job-${jobId}`);
    if (!card) return;
    card.classList.add('accepted');
    card.querySelector('.accept-btn').textContent  = '✅ Accepted';
    card.querySelector('.accept-btn').disabled     = true;
    card.querySelector('.decline-btn').disabled    = true;
    showToast(`✅ Accepted job from ${clientName}`);
    }

    function declineJob(jobId) {
    const card = document.getElementById(`job-${jobId}`);
    if (!card) return;
    card.classList.add('declined');
    showToast('Job declined');
    }

    function logout() {
    Auth.clear();
    redirectTo('/ui/pages/auth.html');
    }