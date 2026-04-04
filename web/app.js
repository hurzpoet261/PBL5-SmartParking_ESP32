// API Configuration
const API_BASE_URL = 'http://localhost:8000/api/v1';

// Global state
let currentTab = 'sessions';
let customersData = {};
let vehiclesData = {};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    refreshAll();
    // Auto refresh every 5 seconds
    setInterval(refreshAll, 5000);
});

// Refresh all data
async function refreshAll() {
    await Promise.all([
        loadStats(),
        loadSessions(),
        loadCustomers(),
        loadVehicles(),
        loadRFIDCards()
    ]);
}

// Load statistics
async function loadStats() {
    try {
        const response = await fetch(`${API_BASE_URL}/stats`);
        const result = await response.json();
        
        if (result.success) {
            const stats = result.data;
            document.getElementById('totalCustomers').textContent = stats.total_customers || 0;
            document.getElementById('activeSessions').textContent = stats.active_sessions || 0;
            document.getElementById('totalScans').textContent = stats.total_scans || 0;
        }
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// Load sessions
async function loadSessions() {
    try {
        const response = await fetch(`${API_BASE_URL}/sessions?limit=50`);
        const result = await response.json();
        
        if (result.success) {
            const sessions = result.data;
            const tbody = document.getElementById('sessionsTable');
            
            if (sessions.length === 0) {
                tbody.innerHTML = '<tr><td colspan="7" class="text-center">Chưa có dữ liệu</td></tr>';
                return;
            }
            
            tbody.innerHTML = sessions.map(session => `
                <tr>
                    <td><strong>${session.session_id}</strong></td>
                    <td>${session.customer_id}</td>
                    <td>${session.vehicle_id}</td>
                    <td><code>${session.card_uid}</code></td>
                    <td>${formatDateTime(session.entry_time)}</td>
                    <td>${session.distance_cm ? session.distance_cm + ' cm' : 'N/A'}</td>
                    <td><span class="badge ${session.status === 'in_progress' ? 'success' : 'warning'}">${session.status === 'in_progress' ? 'Đang đỗ' : 'Đã ra'}</span></td>
                </tr>
            `).join('');
        }
    } catch (error) {
        console.error('Error loading sessions:', error);
    }
}

// Load customers
async function loadCustomers() {
    try {
        const response = await fetch(`${API_BASE_URL}/customers`);
        const result = await response.json();
        
        if (result.success) {
            const customers = result.data;
            customersData = {};
            customers.forEach(c => customersData[c.customer_id] = c);
            
            // Update total vehicles count
            document.getElementById('totalVehicles').textContent = customers.length;
            
            const tbody = document.getElementById('customersTable');
            
            if (customers.length === 0) {
                tbody.innerHTML = '<tr><td colspan="7" class="text-center">Chưa có khách hàng</td></tr>';
                return;
            }
            
            tbody.innerHTML = customers.map(customer => `
                <tr>
                    <td><strong>${customer.customer_id}</strong></td>
                    <td>${customer.name}</td>
                    <td>${customer.phone || '<em>Chưa có</em>'}</td>
                    <td>${customer.email || '<em>Chưa có</em>'}</td>
                    <td><code>${customer.card_uid || 'N/A'}</code></td>
                    <td>${formatDate(customer.created_at)}</td>
                    <td>
                        <button class="btn btn-primary btn-sm" onclick="editCustomer('${customer.customer_id}')">Sửa</button>
                    </td>
                </tr>
            `).join('');
        }
    } catch (error) {
        console.error('Error loading customers:', error);
    }
}

// Load vehicles
async function loadVehicles() {
    try {
        const response = await fetch(`${API_BASE_URL}/vehicles`);
        const result = await response.json();
        
        if (result.success) {
            const vehicles = result.data;
            vehiclesData = {};
            vehicles.forEach(v => vehiclesData[v.vehicle_id] = v);
            
            const tbody = document.getElementById('vehiclesTable');
            
            if (vehicles.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" class="text-center">Chưa có xe</td></tr>';
                return;
            }
            
            tbody.innerHTML = vehicles.map(vehicle => `
                <tr>
                    <td><strong>${vehicle.vehicle_id}</strong></td>
                    <td><strong>${vehicle.plate_number}</strong></td>
                    <td><span class="badge ${vehicle.vehicle_type === 'car' ? 'warning' : 'success'}">${vehicle.vehicle_type === 'car' ? 'Ô tô' : 'Xe máy'}</span></td>
                    <td>${vehicle.customer_id}</td>
                    <td>${formatDate(vehicle.created_at)}</td>
                    <td>
                        <button class="btn btn-primary btn-sm" onclick="editVehicle('${vehicle.vehicle_id}')">Sửa</button>
                    </td>
                </tr>
            `).join('');
        }
    } catch (error) {
        console.error('Error loading vehicles:', error);
    }
}

// Load RFID cards
async function loadRFIDCards() {
    try {
        const response = await fetch(`${API_BASE_URL}/rfid-cards`);
        const result = await response.json();
        
        if (result.success) {
            const cards = result.data;
            const tbody = document.getElementById('cardsTable');
            
            if (cards.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" class="text-center">Chưa có thẻ</td></tr>';
                return;
            }
            
            tbody.innerHTML = cards.map(card => `
                <tr>
                    <td><code>${card.card_uid}</code></td>
                    <td>${card.customer_id}</td>
                    <td>${card.vehicle_id}</td>
                    <td><span class="badge ${card.status === 'active' ? 'success' : 'danger'}">${card.status === 'active' ? 'Hoạt động' : 'Vô hiệu'}</span></td>
                    <td>${formatDate(card.created_at)}</td>
                </tr>
            `).join('');
        }
    } catch (error) {
        console.error('Error loading RFID cards:', error);
    }
}

// Switch tab
function switchTab(tabName) {
    currentTab = tabName;
    
    // Update tab buttons
    document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
    event.target.classList.add('active');
    
    // Update tab panes
    document.querySelectorAll('.tab-pane').forEach(pane => pane.classList.remove('active'));
    document.getElementById(`${tabName}-tab`).classList.add('active');
}

// Edit customer
function editCustomer(customerId) {
    const customer = customersData[customerId];
    if (!customer) return;
    
    const modal = document.getElementById('editModal');
    document.getElementById('modalTitle').textContent = 'Chỉnh sửa khách hàng';
    document.getElementById('modalBody').innerHTML = `
        <form onsubmit="saveCustomer(event, '${customerId}')">
            <div class="form-group">
                <label>Mã khách hàng</label>
                <input type="text" value="${customer.customer_id}" disabled>
            </div>
            <div class="form-group">
                <label>Tên khách hàng *</label>
                <input type="text" id="customerName" value="${customer.name}" required>
            </div>
            <div class="form-group">
                <label>Số điện thoại</label>
                <input type="tel" id="customerPhone" value="${customer.phone || ''}" placeholder="0912345678">
            </div>
            <div class="form-group">
                <label>Email</label>
                <input type="email" id="customerEmail" value="${customer.email || ''}" placeholder="email@example.com">
            </div>
            <div class="form-actions">
                <button type="button" class="btn" onclick="closeModal()">Hủy</button>
                <button type="submit" class="btn btn-primary">Lưu</button>
            </div>
        </form>
    `;
    modal.classList.add('active');
}

// Save customer
async function saveCustomer(event, customerId) {
    event.preventDefault();
    
    const name = document.getElementById('customerName').value;
    const phone = document.getElementById('customerPhone').value;
    const email = document.getElementById('customerEmail').value;
    
    try {
        const response = await fetch(`${API_BASE_URL}/customers/${customerId}?name=${encodeURIComponent(name)}&phone=${encodeURIComponent(phone)}&email=${encodeURIComponent(email)}`, {
            method: 'PUT'
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert('Cập nhật thành công!');
            closeModal();
            await loadCustomers();
        } else {
            alert('Lỗi: ' + result.message);
        }
    } catch (error) {
        alert('Lỗi kết nối: ' + error.message);
    }
}

// Edit vehicle
function editVehicle(vehicleId) {
    const vehicle = vehiclesData[vehicleId];
    if (!vehicle) return;
    
    const modal = document.getElementById('editModal');
    document.getElementById('modalTitle').textContent = 'Chỉnh sửa xe';
    document.getElementById('modalBody').innerHTML = `
        <form onsubmit="saveVehicle(event, '${vehicleId}')">
            <div class="form-group">
                <label>Mã xe</label>
                <input type="text" value="${vehicle.vehicle_id}" disabled>
            </div>
            <div class="form-group">
                <label>Biển số xe *</label>
                <input type="text" id="vehiclePlate" value="${vehicle.plate_number}" required placeholder="59A1-12345">
            </div>
            <div class="form-group">
                <label>Loại xe *</label>
                <select id="vehicleType" required>
                    <option value="motorbike" ${vehicle.vehicle_type === 'motorbike' ? 'selected' : ''}>Xe máy</option>
                    <option value="car" ${vehicle.vehicle_type === 'car' ? 'selected' : ''}>Ô tô</option>
                </select>
            </div>
            <div class="form-actions">
                <button type="button" class="btn" onclick="closeModal()">Hủy</button>
                <button type="submit" class="btn btn-primary">Lưu</button>
            </div>
        </form>
    `;
    modal.classList.add('active');
}

// Save vehicle
async function saveVehicle(event, vehicleId) {
    event.preventDefault();
    
    const plate = document.getElementById('vehiclePlate').value;
    const type = document.getElementById('vehicleType').value;
    
    try {
        const response = await fetch(`${API_BASE_URL}/vehicles/${vehicleId}?plate_number=${encodeURIComponent(plate)}&vehicle_type=${type}`, {
            method: 'PUT'
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert('Cập nhật thành công!');
            closeModal();
            await loadVehicles();
        } else {
            alert('Lỗi: ' + result.message);
        }
    } catch (error) {
        alert('Lỗi kết nối: ' + error.message);
    }
}

// Close modal
function closeModal() {
    document.getElementById('editModal').classList.remove('active');
}

// Format date
function formatDate(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('vi-VN');
}

// Format datetime
function formatDateTime(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleString('vi-VN');
}
