// API Configuration
const API_BASE_URL = 'http://localhost:8000/api/v1';

// API Helper
const api = {
    async get(endpoint) {
        try {
            console.log(`API GET: ${API_BASE_URL}${endpoint}`);
            const response = await fetch(`${API_BASE_URL}${endpoint}`);
            const data = await response.json();
            console.log(`API Response:`, data);
            return data;
        } catch (error) {
            console.error('API GET Error:', error);
            return { success: false, error: error.message };
        }
    },
    
    async post(endpoint, data) {
        try {
            console.log(`API POST: ${API_BASE_URL}${endpoint}`, data);
            const response = await fetch(`${API_BASE_URL}${endpoint}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            const result = await response.json();
            console.log(`API Response:`, result);
            return result;
        } catch (error) {
            console.error('API POST Error:', error);
            return { success: false, error: error.message };
        }
    },
    
    async put(endpoint, data) {
        try {
            console.log(`API PUT: ${API_BASE_URL}${endpoint}`, data);
            const response = await fetch(`${API_BASE_URL}${endpoint}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            const result = await response.json();
            console.log(`API Response:`, result);
            return result;
        } catch (error) {
            console.error('API PUT Error:', error);
            return { success: false, error: error.message };
        }
    },
    
    async delete(endpoint) {
        try {
            console.log(`API DELETE: ${API_BASE_URL}${endpoint}`);
            const response = await fetch(`${API_BASE_URL}${endpoint}`, {
                method: 'DELETE'
            });
            const result = await response.json();
            console.log(`API Response:`, result);
            return result;
        } catch (error) {
            console.error('API DELETE Error:', error);
            return { success: false, error: error.message };
        }
    }
};

// Format currency
function formatCurrency(amount) {
    if (!amount) return '0đ';
    return new Intl.NumberFormat('vi-VN', {
        style: 'currency',
        currency: 'VND'
    }).format(amount);
}

// Format date
function formatDate(dateString) {
    if (!dateString) return 'N/A';
    try {
        return new Date(dateString).toLocaleDateString('vi-VN');
    } catch {
        return 'N/A';
    }
}

// Format datetime
function formatDateTime(dateString) {
    if (!dateString) return 'N/A';
    try {
        return new Date(dateString).toLocaleString('vi-VN');
    } catch {
        return 'N/A';
    }
}

// Calculate duration
function calculateDuration(startTime) {
    if (!startTime) return '0h 0m';
    try {
        const start = new Date(startTime);
        const now = new Date();
        const diff = now - start;
        const hours = Math.floor(diff / 3600000);
        const minutes = Math.floor((diff % 3600000) / 60000);
        return `${hours}h ${minutes}m`;
    } catch {
        return '0h 0m';
    }
}

// Show toast notification
function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `alert alert-${type} position-fixed top-0 end-0 m-3`;
    toast.style.zIndex = '9999';
    toast.style.minWidth = '300px';
    toast.textContent = message;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.remove();
    }, 3000);
}

// Check backend connection
async function checkBackend() {
    try {
        const response = await fetch('http://localhost:8000/health');
        const data = await response.json();
        return data.status === 'healthy';
    } catch {
        return false;
    }
}

// Show backend error
function showBackendError() {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'alert alert-danger position-fixed top-50 start-50 translate-middle';
    errorDiv.style.zIndex = '10000';
    errorDiv.style.minWidth = '400px';
    errorDiv.innerHTML = `
        <h5><i class="bi bi-exclamation-triangle"></i> Không kết nối được Backend</h5>
        <p>Vui lòng kiểm tra:</p>
        <ol>
            <li>Backend đã chạy chưa: <code>python -m app.main</code></li>
            <li>Backend chạy tại: <code>http://localhost:8000</code></li>
        </ol>
        <button class="btn btn-primary btn-sm" onclick="location.reload()">Thử lại</button>
    `;
    document.body.appendChild(errorDiv);
}

// Initialize - check backend on page load
document.addEventListener('DOMContentLoaded', async () => {
    const isBackendRunning = await checkBackend();
    if (!isBackendRunning) {
        showBackendError();
    }
});