// Customers Management
let customersAutoRefresh = null;

async function loadCustomers() {
    const tbody = document.getElementById('customersTable');
    
    try {
        const search = document.getElementById('searchInput')?.value || '';
        const type = document.getElementById('typeFilter')?.value || '';
        
        let url = '/customers';
        const params = [];
        if (search) params.push(`search=${encodeURIComponent(search)}`);
        if (type) params.push(`customer_type=${type}`);
        if (params.length > 0) url += '?' + params.join('&');
        
        console.log('Loading customers from:', url);
        const result = await api.get(url);
        console.log('Customers result:', result);
        
        if (!result || !result.success) {
            tbody.innerHTML = '<tr><td colspan="8" class="text-center text-danger">Lỗi tải dữ liệu. Kiểm tra backend đã chạy chưa.</td></tr>';
            return;
        }
        
        if (!result.data || result.data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" class="text-center">Không có dữ liệu</td></tr>';
            return;
        }
        
        tbody.innerHTML = result.data.map(customer => `
            <tr>
                <td><code>${customer.customer_id}</code></td>
                <td><strong>${customer.name}</strong></td>
                <td>${customer.phone}</td>
                <td>${customer.email || 'N/A'}</td>
                <td><span class="badge bg-${getCustomerTypeBadge(customer.customer_type)}">${getCustomerTypeLabel(customer.customer_type)}</span></td>
                <td>${customer.vehicle_count || 0}</td>
                <td>${formatDate(customer.created_at)}</td>
                <td>
                    <button class="btn btn-sm btn-info" onclick="viewCustomer('${customer.customer_id}')">
                        <i class="bi bi-eye"></i>
                    </button>
                    <button class="btn btn-sm btn-danger" onclick="deleteCustomer('${customer.customer_id}')">
                        <i class="bi bi-trash"></i>
                    </button>
                </td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Error loading customers:', error);
        showToast('Không thể tải danh sách khách hàng', 'danger');
    }
}

function getCustomerTypeBadge(type) {
    const badges = {
        'walk_in': 'secondary',
        'monthly': 'primary',
        'vip': 'warning'
    };
    return badges[type] || 'secondary';
}

function getCustomerTypeLabel(type) {
    const labels = {
        'walk_in': 'Vãng lai',
        'monthly': 'Tháng',
        'vip': 'VIP'
    };
    return labels[type] || type;
}

async function viewCustomer(customerId) {
    try {
        const result = await api.get(`/customers/${customerId}`);
        if (result.success) {
            alert(JSON.stringify(result.data, null, 2));
        }
    } catch (error) {
        showToast('Không thể xem chi tiết', 'danger');
    }
}

async function deleteCustomer(customerId) {
    if (!confirm('Bạn có chắc muốn xóa khách hàng này?')) return;
    
    try {
        const result = await api.delete(`/customers/${customerId}`);
        if (result.success) {
            showToast('Xóa thành công', 'success');
            loadCustomers();
        }
    } catch (error) {
        showToast('Không thể xóa khách hàng', 'danger');
    }
}

function initCustomersPage() {
    loadCustomers();
    if (!customersAutoRefresh) {
        customersAutoRefresh = setInterval(loadCustomers, 10000);
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', initCustomersPage);
