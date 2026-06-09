// Revenue Chart Logic

let dailyChart = null;
let packageChart = null;

async function initRevenuePage() {
    setDefaultExportDates();
    await loadRevenueSummary();
    await loadRevenueCharts();
    await loadRecentTransactions();
}

function dateInputValue(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

function setDefaultExportDates() {
    const startInput = document.getElementById('exportStartDate');
    const endInput = document.getElementById('exportEndDate');
    if (!startInput || !endInput) return;

    const now = new Date();
    const start = new Date(now.getFullYear(), now.getMonth(), 1);
    startInput.value = dateInputValue(start);
    endInput.value = dateInputValue(now);
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
        console.log('Loading daily revenue chart...');
        const dailyData = await api.get('/stats/revenue?days=30');
        console.log('Daily revenue data:', dailyData);

        if (dailyData && dailyData.success && dailyData.data && dailyData.data.chart_data) {
            const labels = dailyData.data.chart_data.map(item => item.date);
            const values = dailyData.data.chart_data.map(item => item.revenue);
            createDailyRevenueChart({ labels, values });
        } else {
            createDailyRevenueChart({ labels: [], values: [] });
        }

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
    if (!ctx) return;

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
                        callback(value) {
                            return Number(value || 0).toLocaleString('vi-VN') + 'đ';
                        }
                    }
                }
            }
        }
    });
}

function createPackageRevenueChart(data) {
    const ctx = document.getElementById('packageRevenueChart');
    if (!ctx) return;

    if (packageChart) {
        packageChart.destroy();
    }

    packageChart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: data.labels || ['Theo lượt', 'Theo ngày', 'Theo tháng'],
            datasets: [{
                data: data.values || [0, 0, 0],
                backgroundColor: ['#4F46E5', '#10B981', '#F59E0B', '#64748B'],
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
                <td><code>${escapeHtml(tx.transaction_id || tx.record_id || 'N/A')}</code></td>
                <td>${escapeHtml(tx.customer_name || 'N/A')}</td>
                <td><span class="badge bg-info">${escapeHtml(getTransactionTypeLabel(tx.transaction_type))}</span></td>
                <td><strong>${formatCurrency(tx.amount)}</strong></td>
                <td>${formatDateTime(tx.created_at)}</td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Error loading transactions:', error);
        tbody.innerHTML = '<tr><td colspan="5" class="text-center text-danger">Không thể tải giao dịch gần đây</td></tr>';
    }
}

function escapeHtml(value) {
    return String(value ?? '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#039;');
}

function getTransactionTypeLabel(type) {
    const labels = {
        parking_fee: 'Phí gửi xe',
        package_purchase: 'Mua gói',
        package_renewal: 'Gia hạn gói'
    };
    return labels[type] || type || 'N/A';
}

function getFilenameFromDisposition(disposition, fallback) {
    if (!disposition) return fallback;
    const utf8Match = disposition.match(/filename\*=UTF-8''([^;]+)/i);
    if (utf8Match) return decodeURIComponent(utf8Match[1]);
    const plainMatch = disposition.match(/filename="?([^"]+)"?/i);
    return plainMatch ? plainMatch[1] : fallback;
}

function buildExportParams(format) {
    const startDate = document.getElementById('exportStartDate')?.value || '';
    const endDate = document.getElementById('exportEndDate')?.value || '';
    const revenueType = document.getElementById('exportRevenueType')?.value || 'all';

    if (startDate && endDate && startDate > endDate) {
        throw new Error('Ngày bắt đầu không được lớn hơn ngày kết thúc');
    }

    const params = new URLSearchParams();
    params.set('format', format);
    params.set('revenue_type', revenueType);
    if (startDate) params.set('start_date', startDate);
    if (endDate) params.set('end_date', endDate);
    return params;
}

async function exportRevenue(format) {
    const csvBtn = document.getElementById('exportCsvBtn');
    const excelBtn = document.getElementById('exportExcelBtn');
    const clickedBtn = format === 'csv' ? csvBtn : excelBtn;
    const originalText = clickedBtn?.innerHTML;

    try {
        const params = buildExportParams(format);
        if (clickedBtn) {
            clickedBtn.disabled = true;
            clickedBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
        }

        const response = await fetch(`${API_BASE_URL}/stats/revenue-export?${params.toString()}`);
        if (!response.ok) {
            let message = 'Không thể xuất báo cáo doanh thu';
            try {
                const errorData = await response.json();
                message = errorData.detail || errorData.error || message;
            } catch (_) {}
            throw new Error(message);
        }

        const blob = await response.blob();
        if (!blob.size) {
            throw new Error('File xuất rỗng');
        }

        const fallback = format === 'csv'
            ? 'smart_parking_revenue.csv'
            : 'smart_parking_revenue.xls';
        const filename = getFilenameFromDisposition(response.headers.get('Content-Disposition'), fallback);
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(link.href);
        showToast('Đã xuất báo cáo doanh thu', 'success');
    } catch (error) {
        console.error('Error exporting revenue:', error);
        showToast(error.message || 'Không thể xuất báo cáo doanh thu', 'danger');
    } finally {
        if (clickedBtn) {
            clickedBtn.disabled = false;
            clickedBtn.innerHTML = originalText;
        }
    }
}

document.addEventListener('DOMContentLoaded', initRevenuePage);
