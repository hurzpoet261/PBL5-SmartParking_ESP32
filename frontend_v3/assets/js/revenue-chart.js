// Revenue Chart Logic

let dailyChart = null;
let packageChart = null;

async function initRevenuePage() {
    await loadRevenueSummary();
    await loadRevenueCharts();
    await loadRecentTransactions();
}

async function loadRevenueSummary() {
    try {
        console.log('Loading revenue summary...');
        const result = await api.get('/stats/revenue-summary');
        console.log('Revenue summary result:', result);
        
        if (result && result.success && result.data) {
            document.getElementById('todayRevenue').textContent = formatCurrency(result.data.today || 0);
            document.getElementById('weekRevenue').textContent = formatCurrency(result.data.week || 0);
            document.getElementById('monthRevenue').textContent = formatCurrency(result.data.month || 0);
            document.getElementById('totalRevenue').textContent = formatCurrency(result.data.total || 0);
        } else {
            // Set default values
            document.getElementById('todayRevenue').textContent = '0đ';
            document.getElementById('weekRevenue').textContent = '0đ';
            document.getElementById('monthRevenue').textContent = '0đ';
            document.getElementById('totalRevenue').textContent = '0đ';
            showToast('Không thể tải dữ liệu doanh thu. Kiểm tra backend.', 'warning');
        }
    } catch (error) {
        console.error('Error loading revenue summary:', error);
        showToast('Lỗi tải dữ liệu doanh thu', 'danger');
    }
}

async function loadRevenueCharts() {
    try {
        // Daily revenue chart
        console.log('Loading daily revenue chart...');
        const dailyData = await api.get('/stats/revenue?days=30');
        console.log('Daily revenue data:', dailyData);
        
        if (dailyData && dailyData.success && dailyData.data && dailyData.data.chart_data) {
            const labels = dailyData.data.chart_data.map(d => d.date);
            const values = dailyData.data.chart_data.map(d => d.revenue);
            createDailyRevenueChart({ labels, values });
        } else {
            createDailyRevenueChart({ labels: [], values: [] });
        }
        
        // Package revenue chart
        console.log('Loading package revenue chart...');
        const packageData = await api.get('/stats/revenue-by-package');
        console.log('Package revenue data:', packageData);
        
        if (packageData && packageData.success && packageData.data) {
            createPackageRevenueChart(packageData.data);
        } else {
            createPackageRevenueChart({ labels: ['Theo lượt', 'Theo ngày', 'Theo tháng'], values: [0, 0, 0] });
        }
    } catch (error) {
        console.error('Error loading charts:', error);
        createDailyRevenueChart({ labels: [], values: [] });
        createPackageRevenueChart({ labels: ['Theo lượt', 'Theo ngày', 'Theo tháng'], values: [0, 0, 0] });
    }
}

function createDailyRevenueChart(data) {
    const ctx = document.getElementById('dailyRevenueChart');
    
    if (dailyChart) {
        dailyChart.destroy();
    }
    
    dailyChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.labels || [],
            datasets: [{
                label: 'Doanh thu (VNĐ)',
                data: data.values || [],
                borderColor: '#4F46E5',
                backgroundColor: 'rgba(79, 70, 229, 0.1)',
                tension: 0.4,
                fill: true
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

function createPackageRevenueChart(data) {
    const ctx = document.getElementById('packageRevenueChart');
    
    if (packageChart) {
        packageChart.destroy();
    }
    
    packageChart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: data.labels || ['Theo lượt', 'Theo ngày', 'Theo tháng'],
            datasets: [{
                data: data.values || [0, 0, 0],
                backgroundColor: ['#4F46E5', '#10B981', '#F59E0B'],
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

async function loadRecentTransactions() {
    const tbody = document.getElementById('transactionsTable');
    
    try {
        console.log('Loading recent transactions...');
        const result = await api.get('/stats/recent-transactions?limit=10');
        console.log('Transactions result:', result);
        
        if (!result || !result.success) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-center text-danger">Lỗi tải dữ liệu. Kiểm tra backend.</td></tr>';
            return;
        }
        
        if (!result.data || result.data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-center">Không có giao dịch</td></tr>';
            return;
        }
        
        tbody.innerHTML = result.data.map(tx => `
            <tr>
                <td><code>${tx.transaction_id}</code></td>
                <td>${tx.customer_name || 'N/A'}</td>
                <td><span class="badge bg-info">${getTransactionTypeLabel(tx.transaction_type)}</span></td>
                <td><strong>${formatCurrency(tx.amount)}</strong></td>
                <td>${formatDateTime(tx.created_at)}</td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Error loading transactions:', error);
    }
}

function getTransactionTypeLabel(type) {
    const labels = {
        'parking_fee': 'Phí đỗ xe',
        'package_purchase': 'Mua gói',
        'package_renewal': 'Gia hạn gói'
    };
    return labels[type] || type;
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', initRevenuePage);
