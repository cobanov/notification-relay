async function ensureAuthenticated() {
    try {
        const res = await fetch('/auth/me');
        if (!res.ok) {
            window.location.href = '/dashboard';
            return false;
        }
        return true;
    } catch {
        window.location.href = '/dashboard';
        return false;
    }
}

function redirectIfUnauthorized(res) {
    if (res.status === 401 || res.status === 403) {
        window.location.href = '/dashboard';
        return true;
    }
    return false;
}

function formatTime(isoString) {
    const date = new Date(isoString);
    const now = new Date();
    const diff = now - date;
    
    if (diff < 60000) return 'now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h`;
    if (diff < 604800000) return `${Math.floor(diff / 86400000)}d`;
    
    return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

async function loadStats() {
    try {
        const res = await fetch('/notifications/stats');
        if (redirectIfUnauthorized(res)) return;
        const data = await res.json();
        
        document.getElementById('totalNotifications').textContent = data.total.toLocaleString();
        document.getElementById('uniqueApps').textContent = data.by_app.length;
        document.getElementById('lastUpdated').textContent = new Date().toLocaleTimeString();
        
        const chart = document.getElementById('appChart');
        if (!data.by_app.length) {
            chart.innerHTML = '<div class="empty">No data</div>';
            return;
        }
        
        const max = Math.max(...data.by_app.map(a => a.count));
        chart.innerHTML = data.by_app.slice(0, 6).map(app => `
            <div class="bar">
                <span class="bar-label">${app.app_name || 'Unknown'}</span>
                <div class="bar-fill" style="width: ${(app.count / max) * 100}%">${app.count}</div>
            </div>
        `).join('');
    } catch (e) {
        console.error('Failed to load stats:', e);
    }
}

async function loadApps() {
    try {
        const res = await fetch('/notifications/apps');
        if (redirectIfUnauthorized(res)) return;
        const data = await res.json();
        const select = document.getElementById('filterApp');
        
        data.apps.forEach(app => {
            const opt = document.createElement('option');
            opt.value = app;
            opt.textContent = app;
            select.appendChild(opt);
        });
    } catch (e) {
        console.error('Failed to load apps:', e);
    }
}

async function loadNotifications() {
    const app = document.getElementById('filterApp').value;
    const limit = document.getElementById('limitSelect').value;
    
    const params = new URLSearchParams({ limit });
    if (app) params.append('app_name', app);
    
    try {
        const res = await fetch(`/notifications?${params}`);
        if (redirectIfUnauthorized(res)) return;
        const data = await res.json();
        const tbody = document.getElementById('notificationsTable');
        
        if (!data.length) {
            tbody.innerHTML = '<tr><td colspan="4" class="empty">No notifications</td></tr>';
            return;
        }
        
        tbody.innerHTML = data.map(n => `
            <tr>
                <td><span class="app-tag">${n.app_name || '-'}</span></td>
                <td>${n.title || '-'}</td>
                <td>${(n.text || '-').substring(0, 60)}${n.text?.length > 60 ? '...' : ''}</td>
                <td class="time" title="${new Date(n.created_at).toLocaleString()}">${formatTime(n.created_at)}</td>
            </tr>
        `).join('');
    } catch (e) {
        console.error('Failed to load notifications:', e);
    }
}

function refresh() {
    loadStats();
    loadNotifications();
}

function showMessage(type) {
    const el = document.getElementById(type === 'success' ? 'successMessage' : 'errorMessage');
    el.style.display = 'block';
    setTimeout(() => el.style.display = 'none', 2000);
}

document.getElementById('addForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    try {
        const res = await fetch('/notifications', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                app_name: document.getElementById('appName').value,
                title: document.getElementById('title').value,
                text: document.getElementById('text').value,
            })
        });
        
        if (res.ok) {
            showMessage('success');
            e.target.reset();
            refresh();
        } else {
            if (redirectIfUnauthorized(res)) return;
            showMessage('error');
        }
    } catch {
        showMessage('error');
    }
});

document.getElementById('filterApp').addEventListener('change', loadNotifications);
document.getElementById('limitSelect').addEventListener('change', loadNotifications);

document.getElementById('logoutBtn').addEventListener('click', async () => {
    try {
        await fetch('/auth/logout', { method: 'POST' });
    } finally {
        window.location.href = '/dashboard';
    }
});

(async () => {
    const ok = await ensureAuthenticated();
    if (!ok) return;

    loadStats();
    loadApps();
    loadNotifications();
    setInterval(refresh, 30000);
})();
