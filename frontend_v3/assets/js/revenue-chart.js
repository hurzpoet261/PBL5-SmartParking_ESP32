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
        const result = await api.get('/stats/revenue-summary');
        
        if (result.success && result.data) {
            document.getElementById('todayRevenue').textContent = formatCurrency(result.data.today || 0);
            document.getElementById('weekRevenue').textContent = formatCurrency(result.data.week || 0);
            document.getElementById('monthRevenue').textContent = formatCurrency(result.data.month || 0);
            document.getElementById('totalRevenue').textContent = formatCurrency(result.data.total || 0);
        }
    } catch (error) {
        console.error('Error loading revenue summary:', error);
    }
}

async function loadRevenueCharts() {
    try {
        // Daily revenue chart
        const dailyData = await api.get('/stats/revenue?days=30');
        if (dailyData.success) {
            createDailyRevenueChart(dailyData.data);
        }
        
        // Package revenue chart
        const packageData = await api.get('/stats/revenue-by-package');
        if (packageData.success) {
            createPackageRevenueChart(packageData.data);
        }
    } catch (error) {
        console.error('Error loading charts:', error);
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
    try {
        const result = await api.get('/stats/recent-transactions?limit=10');
        const tbody = document.getElementById('transactionsTable');
        
        if (!result.success || !result.data || result.data.length === 0) {
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
