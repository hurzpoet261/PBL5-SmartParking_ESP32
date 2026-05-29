// Dashboard Logic
let revenueChart = null;
let occupancyChart = null;

// Initialize dashboard
async function initDashboard() {
    await loadStats();
    await loadCharts();
    await loadActiveSessions();
    
    // Auto refresh every 30 seconds
    setInterval(refreshDashboard, 30000);
}

// Load statistics
async function loadStats() {
    try {
        const stats = await api.get('/stats/dashboard');
        
        if (stats && stats.success && stats.data) {
            document.getElementById('totalCustomers').textContent = stats.data.total_customers || 0;
            document.getElementById('activeSessions').textContent = stats.data.active_sessions || 0;
            document.getElementById('availableSlots').textContent = stats.data.available_slots || 0;
            document.getElementById('todayRevenue').textContent = formatCurrency(stats.data.today_revenue || 0);
            
            // Update occupancy rate
            const total = stats.data.total_slots || 1;
            const occupied = stats.data.occupied_slots || 0;
            const rate = Math.round((occupied / total) * 100);
            document.getElementById('occupancyRate').textContent = rate + '%';
        } else {
            console.error('Stats API returned error:', stats);
            // Set default values
            document.getElementById('totalCustomers').textContent = '0';
            document.getElementById('activeSessions').textContent = '0';
            document.getElementById('availableSlots').textContent = '0';
            document.getElementById('todayRevenue').textContent = '0đ';
            document.getElementById('occupancyRate').textContent = '0%';
        }
    } catch (error) {
        console.error('Error loading stats:', error);
        showToast('Không thể tải thống kê. Kiểm tra backend đã chạy chưa.', 'danger');
    }
}

// Load charts
async function loadCharts() {
    try {
        // Revenue chart - last 7 days
        const revenueData = await api.get('/stats/revenue?days=7');
        
        if (revenueData && revenueData.success && revenueData.data && revenueData.data.chart_data) {
            const labels = revenueData.data.chart_data.map(d => d.date);
            const values = revenueData.data.chart_data.map(d => d.revenue);
            createRevenueChart({ labels, values });
        } else {
            createRevenueChart({ labels: [], values: [] });
        }
        
        // Occupancy chart
        const occupancyData = await api.get('/stats/occupancy');
        if (occupancyData && occupancyData.success && occupancyData.data) {
            createOccupancyChart(occupancyData.data);
        } else {
            createOccupancyChart({ occupied: 0, available: 20 });
        }
    } catch (error) {
        console.error('Error loading charts:', error);
        createRevenueChart({ labels: [], values: [] });
        createOccupancyChart({ occupied: 0, available: 20 });
    }
}

// Create revenue chart
function createRevenueChart(data) {
    const ctx = document.getElementById('revenueChart');
    
    if (revenueChart) {
        revenueChart.destroy();
    }
    
    revenueChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.labels || [],
            datasets: [{
                label: 'Doanh thu (VNĐ)',
                data: data.values || [],
                backgroundColor: 'rgba(79, 70, 229, 0.8)',
                borderColor: 'rgba(79, 70, 229, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return value.toLocaleString('vi-VN') + 'đ';
                        }
                    }
                }
            }
        }
    });
}

// Create occupancy chart
function createOccupancyChart(data) {
    const ctx = document.getElementById('occupancyChart');
    
    if (occupancyChart) {
        occupancyChart.destroy();
    }
    
    occupancyChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Đang đỗ', 'Trống'],
            datasets: [{
                data: [data.occupied || 0, data.available || 0],
                backgroundColor: ['#EF4444', '#10B981'],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
}

// Load active sessions
async function loadActiveSessions() {
    try {
        const sessions = await api.get('/sessions?status=active');
        const tbody = document.getElementById('activeSessionsTable');
        
        if (!sessions || !sessions.success || !sessions.data || sessions.data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">Không có xe đang đỗ</td></tr>';
            return;
        }
        
        tbody.innerHTML = sessions.data.map(session => `
            <tr>
                <td><code>${session.session_id || 'N/A'}</code></td>
                <td>${session.customer_name || 'N/A'}</td>
                <td><strong>${session.plate_number || 'N/A'}</strong></td>
                <td><span class="badge bg-info">${session.slot_number || session.slot_id || 'N/A'}</span></td>
                <td>${formatDateTime(session.entry_time || session.check_in_time)}</td>
                <td>${calculateDuration(session.entry_time || session.check_in_time)}</td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Error loading sessions:', error);
        const tbody = document.getElementById('activeSessionsTable');
        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-danger">Lỗi tải dữ liệu. Kiểm tra backend.</td></tr>';
    }
}

// Refresh dashboard
async function refreshDashboard() {
    await loadStats();
    await loadActiveSessions();
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', initDashboard);
