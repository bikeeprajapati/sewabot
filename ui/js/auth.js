    // ── Tab switching ────────────────────────────────────────
    function switchTab(tab) {
    document.querySelectorAll('.auth-tab').forEach(t => t.classList.remove('active'));
    document.querySelector(`[data-tab="${tab}"]`).classList.add('active');
    document.getElementById('login-form').classList.toggle('hidden', tab !== 'login');
    document.getElementById('register-form').classList.toggle('hidden', tab !== 'register');
    }

    // ── Role toggle ──────────────────────────────────────────
    let selectedRole = 'client';

    function selectRole(role) {
    selectedRole = role;
    document.querySelectorAll('.role-btn').forEach(b => b.classList.remove('active'));
    document.querySelector(`[data-role="${role}"]`).classList.add('active');
    document.getElementById('worker-extra').classList.toggle('hidden', role !== 'worker');
    }

    // ── Validation ───────────────────────────────────────────
    function showError(fieldId, message) {
    const field = document.getElementById(fieldId);
    const error = document.getElementById(`${fieldId}-error`);
    if (field) field.classList.add('error');
    if (error) { error.textContent = message; error.style.display = 'block'; }
    }

    function clearErrors() {
    document.querySelectorAll('.input').forEach(i => i.classList.remove('error'));
    document.querySelectorAll('.form-error').forEach(e => {
        e.textContent = '';
        e.style.display = 'none';
    });
    }

    function validateLogin(email, password) {
    let valid = true;
    if (!email) { showError('login-email', 'Email is required'); valid = false; }
    if (!password) { showError('login-password', 'Password is required'); valid = false; }
    return valid;
    }

    function validateRegister(data) {
    let valid = true;
    if (!data.full_name.trim()) { showError('reg-name', 'Full name is required'); valid = false; }
    if (!data.email) { showError('reg-email', 'Email is required'); valid = false; }
    if (!data.password || data.password.length < 8) {
        showError('reg-password', 'Password must be at least 8 characters'); valid = false;
    }
    if (!/\d/.test(data.password)) {
        showError('reg-password', 'Password must contain at least one number'); valid = false;
    }
    if (data.password !== data.confirm_password) {
        showError('reg-confirm', 'Passwords do not match'); valid = false;
    }
    return valid;
    }

    // ── Login ────────────────────────────────────────────────
    async function handleLogin(e) {
    e.preventDefault();
    clearErrors();

    const email    = document.getElementById('login-email').value.trim();
    const password = document.getElementById('login-password').value;

    if (!validateLogin(email, password)) return;

    const btn = document.getElementById('login-btn');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Signing in...';

    try {
        const data = await AuthAPI.login(email, password);
        Auth.save(data);
        showToast(`Welcome back, ${data.full_name}!`);
        setTimeout(() => redirectByRole(), 800);
    } catch (err) {
        showError('login-password', err.message);
        showToast(err.message, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = 'Sign In';
    }
    }

    // ── Register ─────────────────────────────────────────────
    async function handleRegister(e) {
    e.preventDefault();
    clearErrors();

    const data = {
        full_name:        document.getElementById('reg-name').value.trim(),
        email:            document.getElementById('reg-email').value.trim(),
        password:         document.getElementById('reg-password').value,
        confirm_password: document.getElementById('reg-confirm').value,
        role:             selectedRole,
        phone:            document.getElementById('reg-phone').value.trim() || null
    };

    if (!validateRegister(data)) return;

    const btn = document.getElementById('register-btn');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Creating account...';

    try {
        delete data.confirm_password;
        await AuthAPI.register(data);
        showToast('Account created! Please sign in.');
        setTimeout(() => switchTab('login'), 1000);
    } catch (err) {
        showError('reg-email', err.message);
        showToast(err.message, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = 'Create Account';
    }
    }

    // ── Logout ───────────────────────────────────────────────
    function logout() {
    Auth.clear();
    redirectTo('/ui/pages/auth.html');
    }

    // ── Init ─────────────────────────────────────────────────
    document.addEventListener('DOMContentLoaded', () => {
    // If already logged in redirect
    if (Auth.isLoggedIn()) { redirectByRole(); return; }

    document.getElementById('login-form')
        ?.addEventListener('submit', handleLogin);
    document.getElementById('register-form')
        ?.addEventListener('submit', handleRegister);
    });