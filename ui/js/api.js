    // ── API Configuration ────────────────────────────────────
    const API_BASE = 'http://localhost:8001';

    // ── Token management ─────────────────────────────────────
    const Auth = {
    getAccessToken:  () => localStorage.getItem('access_token'),
    getRefreshToken: () => localStorage.getItem('refresh_token'),
    getUser:         () => JSON.parse(localStorage.getItem('user') || 'null'),
    getRole:         () => localStorage.getItem('role'),

    save(data) {
        localStorage.setItem('access_token',  data.access_token);
        localStorage.setItem('refresh_token', data.refresh_token);
        localStorage.setItem('role',          data.role);
        localStorage.setItem('user',          JSON.stringify({
        full_name: data.full_name,
        role:      data.role
        }));
    },

    clear() {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('role');
        localStorage.removeItem('user');
    },

    isLoggedIn() { return !!this.getAccessToken(); }
    };

    // ── Base fetch wrapper ────────────────────────────────────
    async function apiFetch(endpoint, options = {}) {
    const token = Auth.getAccessToken();
    const headers = {
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
        ...(options.headers || {})
    };

    const response = await fetch(`${API_BASE}${endpoint}`, {
        ...options,
        headers
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
    }

    // ── Auth API ─────────────────────────────────────────────
    const AuthAPI = {
    async register(data) {
        return apiFetch('/auth/register', {
        method: 'POST',
        body: JSON.stringify(data)
        });
    },

    async login(email, password) {
        return apiFetch('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password })
        });
    },

    async refresh() {
        const refresh_token = Auth.getRefreshToken();
        return apiFetch('/auth/refresh', {
        method: 'POST',
        body: JSON.stringify({ refresh_token })
        });
    }
    };

    // ── Jobs API ─────────────────────────────────────────────
    const JobsAPI = {
    async match(description, client_lat, client_lng) {
        return apiFetch('/match', {
        method: 'POST',
        body: JSON.stringify({ description, client_lat, client_lng })
        });
    },

    async getWorkers() {
        return apiFetch('/workers');
    }
    };

    // ── Payments API ─────────────────────────────────────────
    const PaymentsAPI = {
    async initiate(job_id, client_id) {
        return apiFetch('/payments/initiate', {
        method: 'POST',
        body: JSON.stringify({ job_id, client_id })
        });
    },

    async status(job_id) {
        return apiFetch(`/payments/status/${job_id}`);
    }
    };

    // ── Toast notification ───────────────────────────────────
    function showToast(message, type = 'success') {
    let toast = document.getElementById('toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'toast';
        toast.className = 'toast';
        document.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.className = `toast ${type === 'error' ? 'error' : ''} show`;
    setTimeout(() => toast.classList.remove('show'), 3000);
    }

    // ── Redirect helpers ─────────────────────────────────────
    function redirectTo(page) {
    window.location.href = page;
    }

    function requireAuth() {
    if (!Auth.isLoggedIn()) {
        redirectTo('/ui/pages/auth.html');
        return false;
    }
    return true;
    }

    function redirectByRole() {
    const role = Auth.getRole();
    if (role === 'worker') {
        redirectTo('/ui/pages/worker.html');
    } else {
        redirectTo('/ui/pages/client.html');
    }
    }