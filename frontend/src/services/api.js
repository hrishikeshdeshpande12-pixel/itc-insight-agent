const API_BASE = '';

export function getAuthToken() {
  return localStorage.getItem('itc_auth_token') || null;
}

export function setAuthToken(token) {
  if (token) {
    localStorage.setItem('itc_auth_token', token);
  } else {
    localStorage.removeItem('itc_auth_token');
  }
}

export function getStoredUser() {
  try {
    const raw = localStorage.getItem('itc_auth_user');
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function setStoredUser(user) {
  if (user) {
    localStorage.setItem('itc_auth_user', JSON.stringify(user));
  } else {
    localStorage.removeItem('itc_auth_user');
  }
}

function getAuthHeaders() {
  const token = getAuthToken();
  const headers = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

export async function fetchHealth() {
  try {
    const res = await fetch(`${API_BASE}/health`);
    if (!res.ok) throw new Error(`Health check failed: ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error('API health check error:', err);
    return { status: 'offline', vector_store_ready: false, documents_indexed: 0, total_chunks: 0 };
  }
}

export async function loginApi(email, password) {
  const res = await fetch(`${API_BASE}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Sign in failed');
  setAuthToken(data.token);
  setStoredUser(data.user);
  return data;
}

export async function registerApi(email, password, displayName) {
  const res = await fetch(`${API_BASE}/api/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, display_name: displayName }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Registration failed');
  setAuthToken(data.token);
  setStoredUser(data.user);
  return data;
}

export async function fetchCurrentUserApi() {
  const token = getAuthToken();
  if (!token) return null;
  const res = await fetch(`${API_BASE}/api/auth/me`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    setAuthToken(null);
    setStoredUser(null);
    return null;
  }
  const data = await res.json();
  return data.user;
}

export async function fetchSessionsApi() {
  const res = await fetch(`${API_BASE}/api/sessions`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    return [];
  }
  const data = await res.json();
  return data.sessions || [];
}

export async function fetchSessionMessagesApi(sessionId) {
  const res = await fetch(`${API_BASE}/api/sessions/${sessionId}`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) return [];
  const data = await res.json();
  return data.messages || [];
}

export async function deleteSessionApi(sessionId) {
  const res = await fetch(`${API_BASE}/api/sessions/${sessionId}`, {
    method: 'DELETE',
    headers: getAuthHeaders(),
  });
  return res.ok;
}

export async function sendChatMessage(question, sessionId = null) {
  const user = getStoredUser();
  const res = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({
      question,
      session_id: sessionId,
      user_id: user ? user.id : 'guest',
    }),
  });

  if (!res.ok) {
    if (res.status === 401) {
      setAuthToken(null);
      setStoredUser(null);
    }
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Request failed with status ${res.status}`);
  }

  return await res.json();
}

// ==========================================
// Administrator Governance & Approval APIs
// ==========================================

export async function fetchAdminUsersApi() {
  const res = await fetch(`${API_BASE}/api/admin/users`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Could not fetch users list');
  }
  const data = await res.json();
  return data.users || [];
}

export async function approveUserApi(userId) {
  const res = await fetch(`${API_BASE}/api/admin/users/${userId}/approve`, {
    method: 'POST',
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Could not approve user account');
  }
  return await res.json();
}

export async function rejectUserApi(userId) {
  const res = await fetch(`${API_BASE}/api/admin/users/${userId}/reject`, {
    method: 'POST',
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Could not decline user account');
  }
  return await res.json();
}

export async function deleteUserApi(userId) {
  const res = await fetch(`${API_BASE}/api/admin/users/${userId}`, {
    method: 'DELETE',
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Could not delete user account');
  }
  return await res.json();
}

export async function fetchAdminStatsApi() {
  const res = await fetch(`${API_BASE}/api/admin/stats`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    return { total_users: 0, pending_approvals: 0, approved_users: 0, rejected_users: 0 };
  }
  return await res.json();
}

export async function fetchAdminNotificationsApi() {
  const res = await fetch(`${API_BASE}/api/admin/notifications`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    return [];
  }
  const data = await res.json();
  return data.notifications || [];
}
