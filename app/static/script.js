const API_KEY = 'your-secret-api-key-change-this';

async function loadStats() {
    try {
        const res = await fetch('/notifications/stats');
        const data = await res.json();
        
        document.getElementById('totalNotifications').textContent = data.total.toLocaleString();
        document.getElementById('uniqueApps').textContent = data.by_app.length;
        document.getElementById('lastUpdated').textContent = `Updated ${new Date().toLocaleTimeString()}`;
        
        const chart = document.getElementById('appChart');
        if (!data.by_app.length) {
            chart.innerHTML = '<div class="empty">No data</div>';
            return;
        }
        
        const max = Math.max(...data.by_app.map(a => a.count));
        chart.innerHTML = data.by_app.slice(0, 8).map(app => `
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
                <td>${(n.text || '-').substring(0, 80)}${n.text?.length > 80 ? '...' : ''}</td>
                <td class="time">${new Date(n.created_at).toLocaleString()}</td>
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
    setTimeout(() => el.style.display = 'none', 3000);
}

document.getElementById('addForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    try {
        const res = await fetch('/notifications', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-API-Key': API_KEY },
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
            showMessage('error');
        }
    } catch {
        showMessage('error');
    }
});

document.getElementById('filterApp').addEventListener('change', loadNotifications);
document.getElementById('limitSelect').addEventListener('change', loadNotifications);

loadStats();
loadApps();
loadNotifications();

setInterval(refresh, 30000);
