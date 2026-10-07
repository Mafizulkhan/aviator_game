/**
 * Anti-Gravity Admin Console — Client Application Logic
 * Implements authentication, real-time live telemetry, user management,
 * virtual credit adjustments, fairness verification, settings, and audit logs.
 */

const API_BASE = '/api/admin';

// State
let authToken = localStorage.getItem('ag_admin_token') || null;
let currentAdmin = JSON.parse(localStorage.getItem('ag_admin_user') || 'null');
let wsClient = null;
let telemetryTimer = null;

// DOM Elements
const loginView = document.getElementById('login-view');
const dashboardView = document.getElementById('dashboard-view');
const loginForm = document.getElementById('login-form');
const loginError = document.getElementById('login-error');
const logoutBtn = document.getElementById('logout-btn');

const adminNameElem = document.getElementById('current-admin-name');
const adminRoleElem = document.getElementById('current-admin-role');
const maintenanceBadge = document.getElementById('maintenance-badge');

// ── INIT ───────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  setupNavigation();
  setupModals();
  setupEventListeners();

  if (authToken && currentAdmin) {
    showDashboard();
  } else {
    showLogin();
  }
});

// ── AUTHENTICATION ─────────────────────────────────────────────────────────────
loginForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  loginError.classList.add('hidden');

  const username = document.getElementById('username').value.trim();
  const password = document.getElementById('password').value;

  try {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || 'Authentication failed');
    }

    authToken = data.access_token;
    currentAdmin = { username: data.username, role: data.role };

    localStorage.setItem('ag_admin_token', authToken);
    localStorage.setItem('ag_admin_user', JSON.stringify(currentAdmin));

    showDashboard();
  } catch (err) {
    loginError.textContent = err.message;
    loginError.classList.remove('hidden');
  }
});

logoutBtn.addEventListener('click', async () => {
  if (authToken) {
    try {
      await fetchWithAuth(`${API_BASE}/auth/logout`, { method: 'POST' });
    } catch (_) {}
  }
  authToken = null;
  currentAdmin = null;
  localStorage.removeItem('ag_admin_token');
  localStorage.removeItem('ag_admin_user');
  if (telemetryTimer) clearInterval(telemetryTimer);
  showLogin();
});

function showLogin() {
  loginView.classList.remove('hidden');
  dashboardView.classList.add('hidden');
}

function showDashboard() {
  loginView.classList.add('hidden');
  dashboardView.classList.remove('hidden');

  adminNameElem.textContent = currentAdmin.username;
  adminRoleElem.textContent = currentAdmin.role.toUpperCase();

  loadDashboardMetrics();
  loadUsers();
  loadTransactions();
  loadRounds();
  loadSettings();
  loadAuditLogs();
  loadSystemHealth();

  // Start periodic telemetry update
  if (telemetryTimer) clearInterval(telemetryTimer);
  telemetryTimer = setInterval(loadDashboardMetrics, 2000);
}

// ── API HELPER ─────────────────────────────────────────────────────────────────
async function fetchWithAuth(url, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {})
  };
  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`;
  }

  const res = await fetch(url, { ...options, headers });
  if (res.status === 401) {
    logoutBtn.click();
    throw new Error('Session expired. Please log in again.');
  }
  return res;
}

// ── NAVIGATION TABS ────────────────────────────────────────────────────────────
function setupNavigation() {
  const tabs = document.querySelectorAll('.nav-tab');
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));

      tab.classList.add('active');
      const targetPane = document.getElementById(tab.dataset.tab);
      if (targetPane) targetPane.classList.add('active');

      // Refresh specific tab data on click
      if (tab.dataset.tab === 'tab-users') loadUsers();
      if (tab.dataset.tab === 'tab-credits') loadTransactions();
      if (tab.dataset.tab === 'tab-rounds') loadRounds();
      if (tab.dataset.tab === 'tab-settings') loadSettings();
      if (tab.dataset.tab === 'tab-audit') loadAuditLogs();
      if (tab.dataset.tab === 'tab-health') loadSystemHealth();
    });
  });
}

// ── 1. DASHBOARD OVERVIEW ─────────────────────────────────────────────────────
async function loadDashboardMetrics() {
  try {
    const res = await fetchWithAuth(`${API_BASE}/dashboard`);
    if (!res.ok) return;
    const data = await res.json();

    document.getElementById('dash-multiplier').textContent = `${data.current_multiplier.toFixed(2)}x`;
    document.getElementById('dash-round-number').textContent = data.current_round_number || 'N/A';
    document.getElementById('dash-round-status').textContent = (data.current_status || 'IDLE').toUpperCase();
    document.getElementById('dash-active-players').textContent = data.players_in_round;

    document.getElementById('dash-circulation').textContent = Number(data.credits_in_circulation).toLocaleString();
    document.getElementById('dash-total-users').textContent = data.total_users;
    document.getElementById('dash-games-today').textContent = data.games_today;
    document.getElementById('dash-cashout-rate').textContent = `${(data.cashout_rate * 100).toFixed(1)}%`;

    document.getElementById('dash-ws-count').textContent = `${data.ws_connections} Online`;
    document.getElementById('dash-db-status').textContent = data.db_health.toUpperCase();

    if (data.maintenance_mode) {
      maintenanceBadge.classList.remove('hidden');
    } else {
      maintenanceBadge.classList.add('hidden');
    }
  } catch (err) {
    console.error('Failed to load dashboard metrics:', err);
  }
}

// ── 2. USERS ──────────────────────────────────────────────────────────────────
async function loadUsers() {
  const search = document.getElementById('user-search-input').value.trim();
  const role = document.getElementById('user-role-filter').value;
  const status = document.getElementById('user-status-filter').value;

  const params = new URLSearchParams();
  if (search) params.append('search', search);
  if (role) params.append('role', role);
  if (status) params.append('status_filter', status);

  try {
    const res = await fetchWithAuth(`${API_BASE}/users?${params.toString()}`);
    if (!res.ok) return;
    const users = await res.json();

    const tbody = document.getElementById('users-tbody');
    tbody.innerHTML = '';

    users.forEach(u => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${u.id}</td>
        <td><strong>${escapeHtml(u.username)}</strong></td>
        <td>${escapeHtml(u.email || '-')}</td>
        <td><span class="badge badge-ops">${u.role}</span></td>
        <td><span class="badge ${u.status === 'active' ? 'badge-success' : 'badge-warning'}">${u.status}</span></td>
        <td>${Number(u.balance).toLocaleString()}</td>
        <td>${new Date(u.created_at).toLocaleDateString()}</td>
        <td>
          <button class="btn btn-secondary btn-sm" onclick="viewUserDetail(${u.id})">Inspect</button>
          <button class="btn btn-secondary btn-sm" onclick="toggleUserStatus(${u.id}, '${u.status}')">
            ${u.status === 'active' ? 'Ban' : 'Unban'}
          </button>
        </td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error('Failed to load users:', err);
  }
}

window.viewUserDetail = async function(userId) {
  try {
    const res = await fetchWithAuth(`${API_BASE}/users/${userId}`);
    if (!res.ok) return;
    const u = await res.json();

    document.getElementById('modal-user-title').textContent = `User: ${u.username} (ID: ${u.id})`;
    document.getElementById('modal-user-content').innerHTML = `
      <div style="display:flex; flex-direction:column; gap:10px; margin-top:14px;">
        <div><strong>Role:</strong> <span class="badge badge-ops">${u.role}</span></div>
        <div><strong>Status:</strong> <span class="badge ${u.status === 'active' ? 'badge-success' : 'badge-warning'}">${u.status}</span></div>
        <div><strong>Balance:</strong> ${Number(u.balance).toLocaleString()} credits</div>
        <div><strong>Games Played:</strong> ${u.games_played}</div>
        <div><strong>Total Wagered:</strong> ${Number(u.total_wagered).toLocaleString()} credits</div>
        <div><strong>Total Won:</strong> ${Number(u.total_won).toLocaleString()} credits</div>
        <div><strong>Created At:</strong> ${new Date(u.created_at).toLocaleString()}</div>
        <div><strong>Last Login:</strong> ${u.last_login_at ? new Date(u.last_login_at).toLocaleString() : 'Never'}</div>
      </div>
    `;
    document.getElementById('user-detail-modal').classList.remove('hidden');
  } catch (err) {
    alert('Failed to load user details: ' + err.message);
  }
};

window.toggleUserStatus = async function(userId, currentStatus) {
  const newStatus = currentStatus === 'active' ? 'banned' : 'active';
  const reason = prompt(`Reason for setting status to ${newStatus}:`, 'Administrative action');
  if (!reason) return;

  try {
    const res = await fetchWithAuth(`${API_BASE}/users/${userId}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status: newStatus, reason })
    });
    if (!res.ok) throw new Error((await res.json()).detail || 'Failed');
    loadUsers();
  } catch (err) {
    alert('Failed to update user status: ' + err.message);
  }
};

// ── 3. VIRTUAL CREDITS & TRANSACTIONS ──────────────────────────────────────────
async function loadTransactions() {
  try {
    const res = await fetchWithAuth(`${API_BASE}/transactions?limit=50`);
    if (!res.ok) return;
    const txs = await res.json();

    const tbody = document.getElementById('transactions-tbody');
    tbody.innerHTML = '';

    txs.forEach(tx => {
      const tr = document.createElement('tr');
      const isPositive = tx.amount > 0;
      tr.innerHTML = `
        <td>${tx.id}</td>
        <td><strong>${escapeHtml(tx.username)}</strong></td>
        <td><span class="badge badge-ops">${tx.type}</span></td>
        <td class="${isPositive ? 'text-green' : 'text-crash'}">${isPositive ? '+' : ''}${tx.amount}</td>
        <td>${tx.balance_before}</td>
        <td>${tx.balance_after}</td>
        <td>${new Date(tx.created_at).toLocaleString()}</td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error('Failed to load transactions:', err);
  }
}

// ── 4. ROUNDS ─────────────────────────────────────────────────────────────────
async function loadRounds() {
  const status = document.getElementById('round-status-filter').value;
  const params = status ? `?status=${status}` : '';

  try {
    const res = await fetchWithAuth(`${API_BASE}/rounds${params}`);
    if (!res.ok) return;
    const rounds = await res.json();

    const tbody = document.getElementById('rounds-tbody');
    tbody.innerHTML = '';

    rounds.forEach(r => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>#${r.round_number}</td>
        <td><span class="badge ${r.status === 'crashed' ? 'badge-warning' : 'badge-info'}">${r.status}</span></td>
        <td><strong class="text-multiplier">${r.crash_multiplier ? r.crash_multiplier.toFixed(2) + 'x' : '-'}</strong></td>
        <td><code class="crypto-code" style="font-size:0.7rem;">${r.server_seed_hash.substring(0, 16)}...</code></td>
        <td>${r.total_bets}</td>
        <td>${r.total_wagered}</td>
        <td>${r.total_payout}</td>
        <td>
          <button class="btn btn-secondary btn-sm" onclick="auditFairness(${r.id})">Verify Proof</button>
        </td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error('Failed to load rounds:', err);
  }
}

window.auditFairness = function(roundId) {
  document.querySelector('[data-tab="tab-fairness"]').click();
  document.getElementById('fair-round-id').value = roundId;
  document.getElementById('run-verify-btn').click();
};

// ── 5. GAME SETTINGS ──────────────────────────────────────────────────────────
async function loadSettings() {
  try {
    const res = await fetchWithAuth(`${API_BASE}/settings`);
    if (!res.ok) return;
    const s = await res.json();

    document.getElementById('set-min-bet').value = s.minimum_bet;
    document.getElementById('set-max-bet').value = s.maximum_bet;
    document.getElementById('set-start-bal').value = s.starting_balance;
    document.getElementById('set-window').value = s.betting_window_ms;
    document.getElementById('set-house-edge').value = s.house_edge;
    document.getElementById('set-maintenance').checked = s.maintenance_mode;
  } catch (err) {
    console.error('Failed to load settings:', err);
  }
}

document.getElementById('game-settings-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const statusMsg = document.getElementById('settings-status-msg');
  statusMsg.textContent = 'Saving...';

  const payload = {
    minimum_bet: parseInt(document.getElementById('set-min-bet').value),
    maximum_bet: parseInt(document.getElementById('set-max-bet').value),
    starting_balance: parseInt(document.getElementById('set-start-bal').value),
    betting_window_ms: parseInt(document.getElementById('set-window').value),
    house_edge: parseFloat(document.getElementById('set-house-edge').value),
    maintenance_mode: document.getElementById('set-maintenance').checked,
  };

  try {
    const res = await fetchWithAuth(`${API_BASE}/settings`, {
      method: 'PATCH',
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Save failed');

    statusMsg.textContent = 'Settings updated and audited successfully!';
    setTimeout(() => { statusMsg.textContent = ''; }, 3000);
    loadDashboardMetrics();
  } catch (err) {
    statusMsg.textContent = 'Error: ' + err.message;
  }
});

// ── 6. FAIRNESS VERIFIER ──────────────────────────────────────────────────────
document.getElementById('run-verify-btn').addEventListener('click', async () => {
  const roundId = document.getElementById('fair-round-id').value;
  if (!roundId) return;

  const resultPanel = document.getElementById('fairness-result-panel');
  try {
    const res = await fetchWithAuth(`${API_BASE}/fairness/${roundId}/verify`, { method: 'POST' });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Verification failed');

    resultPanel.classList.remove('hidden');
    document.getElementById('fair-round-title').textContent = `Round #${data.round_number} Proof`;
    document.getElementById('fair-seed-hash').textContent = data.server_seed_hash;
    document.getElementById('fair-revealed-seed').textContent = data.server_seed;
    document.getElementById('fair-crash-mult').textContent = `${data.crash_multiplier.toFixed(2)}x`;
    document.getElementById('fair-message').textContent = data.message;
  } catch (err) {
    alert('Verification error: ' + err.message);
  }
});

// ── 7. AUDIT LOGS ─────────────────────────────────────────────────────────────
async function loadAuditLogs() {
  try {
    const res = await fetchWithAuth(`${API_BASE}/audit-logs?limit=50`);
    if (!res.ok) return;
    const logs = await res.json();

    const tbody = document.getElementById('audit-tbody');
    tbody.innerHTML = '';

    logs.forEach(l => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>#${l.id}</td>
        <td>${new Date(l.created_at).toLocaleString()}</td>
        <td><strong>${escapeHtml(l.admin_username || 'System')}</strong></td>
        <td><span class="badge badge-ops">${l.action}</span></td>
        <td>${l.target_type || '-'}</td>
        <td>${l.target_id || '-'}</td>
        <td>${l.ip_address || '-'}</td>
        <td><small>${escapeHtml(l.details || '-')}</small></td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error('Failed to load audit logs:', err);
  }
}

// ── 8. SYSTEM HEALTH ──────────────────────────────────────────────────────────
async function loadSystemHealth() {
  try {
    const res = await fetchWithAuth(`${API_BASE}/system/health`);
    if (!res.ok) return;
    const h = await res.json();

    document.getElementById('health-api-status').textContent = h.api_status.toUpperCase();
    document.getElementById('health-uptime').textContent = `${h.uptime_seconds}s`;
    document.getElementById('health-db-status').textContent = h.db_status.toUpperCase();
    document.getElementById('health-loop-status').textContent = h.game_loop_status.toUpperCase();
    document.getElementById('health-ws-conns').textContent = h.active_connections;
  } catch (err) {
    console.error('Failed to load health:', err);
  }
}

// ── MODAL LISTENERS ────────────────────────────────────────────────────────────
function setupModals() {
  const creditModal = document.getElementById('credit-modal');
  const openCreditBtn = document.getElementById('open-credit-modal-btn');
  const cancelCreditBtn = document.getElementById('cancel-credit-modal');
  const creditForm = document.getElementById('credit-adjust-form');

  if (openCreditBtn) openCreditBtn.onclick = () => creditModal.classList.remove('hidden');
  if (cancelCreditBtn) cancelCreditBtn.onclick = () => creditModal.classList.add('hidden');

  creditForm.onsubmit = async (e) => {
    e.preventDefault();
    const userId = parseInt(document.getElementById('adj-user-id').value);
    const amount = parseInt(document.getElementById('adj-amount').value);
    const reason = document.getElementById('adj-reason').value.trim();

    try {
      const res = await fetchWithAuth(`${API_BASE}/wallet-adjustments`, {
        method: 'POST',
        body: JSON.stringify({ user_id: userId, amount, reason })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Adjustment failed');

      alert(`Adjustment successful! New balance: ${data.balance_after}`);
      creditModal.classList.add('hidden');
      creditForm.reset();
      loadTransactions();
      loadUsers();
    } catch (err) {
      alert('Error: ' + err.message);
    }
  };

  const userModal = document.getElementById('user-detail-modal');
  const closeUserBtn = document.getElementById('close-user-modal');
  if (closeUserBtn) closeUserBtn.onclick = () => userModal.classList.add('hidden');
}

function setupEventListeners() {
  document.getElementById('refresh-dashboard-btn').onclick = loadDashboardMetrics;
  document.getElementById('search-users-btn').onclick = loadUsers;
  document.getElementById('filter-rounds-btn').onclick = loadRounds;
  document.getElementById('refresh-audit-btn').onclick = loadAuditLogs;
  document.getElementById('refresh-health-btn').onclick = loadSystemHealth;
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str).replace(/[&<>"']/g, function(m) {
    return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' }[m];
  });
}
