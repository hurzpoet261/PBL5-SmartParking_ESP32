// Customers Management
let customersAutoRefresh = null;
let latestCustomers = [];
let currentCustomerDetail = null;
let customerDetailModal = null;
let customerEditModal = null;
let vehicleEditModal = null;
let returnToDetailAfterCustomerEdit = false;
let returnToDetailAfterVehicleEdit = false;

function escapeHtml(value) {
    return String(value ?? '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#039;');
}

function safeValue(value, fallback = 'N/A') {
    const text = value ?? '';
    return text === '' ? fallback : escapeHtml(text);
}

function nullableText(value) {
    const text = String(value ?? '').trim();
    return text || null;
}

function getCustomerTypeBadge(type) {
    const badges = {
        walk_in: 'secondary',
        daily: 'info',
        monthly: 'primary',
        vip: 'warning'
    };
    return badges[type] || 'secondary';
}

function getCustomerTypeLabel(type) {
    const labels = {
        walk_in: 'Vãng lai',
        daily: 'Ngày',
        monthly: 'Tháng',
        vip: 'VIP'
    };
    return labels[type] || type || 'N/A';
}

function getVehicleTypeLabel(type) {
    const labels = {
        motorbike: 'Xe máy',
        car: 'Ô tô',
        bicycle: 'Xe đạp',
        truck: 'Xe tải'
    };
    return labels[type] || type || 'N/A';
}

function activeBadge(isActive) {
    return isActive === false
        ? '<span class="badge bg-secondary">Ngừng</span>'
        : '<span class="badge bg-success">Hoạt động</span>';
}

function rfidForVehicle(vehicle, cards) {
    const matched = (cards || []).filter(card => card.vehicle_id === vehicle.vehicle_id);
    if (!matched.length) return '<span class="text-muted">Chưa gắn thẻ</span>';
    return matched.map(card => `<code>${escapeHtml(card.card_uid)}</code>`).join('<br>');
}

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

        const result = await api.get(url);

        if (!result || !result.success) {
            tbody.innerHTML = '<tr><td colspan="9" class="text-center text-danger">Lỗi tải dữ liệu. Kiểm tra backend đã chạy chưa.</td></tr>';
            return [];
        }

        latestCustomers = result.data || [];
        if (!latestCustomers.length) {
            tbody.innerHTML = '<tr><td colspan="9" class="text-center">Không có dữ liệu</td></tr>';
            return [];
        }

        tbody.innerHTML = latestCustomers.map(customer => `
            <tr>
                <td><code>${escapeHtml(customer.customer_id)}</code></td>
                <td><strong>${safeValue(customer.name)}</strong></td>
                <td>${safeValue(customer.phone)}</td>
                <td>${safeValue(customer.email)}</td>
                <td><span class="badge bg-${getCustomerTypeBadge(customer.customer_type)}">${escapeHtml(getCustomerTypeLabel(customer.customer_type))}</span></td>
                <td>${customer.vehicle_count || 0}</td>
                <td>${activeBadge(customer.is_active)}</td>
                <td>${formatDate(customer.created_at)}</td>
                <td>
                    <div class="btn-group btn-group-sm">
                        <button class="btn btn-outline-info" title="Xem chi tiết" onclick="viewCustomer('${escapeHtml(customer.customer_id)}')">
                            <i class="bi bi-eye"></i>
                        </button>
                        <button class="btn btn-outline-primary" title="Sửa khách hàng" onclick="openEditCustomer('${escapeHtml(customer.customer_id)}')">
                            <i class="bi bi-pencil-square"></i>
                        </button>
                        <button class="btn btn-outline-danger" title="Xóa khách hàng" onclick="deleteCustomer('${escapeHtml(customer.customer_id)}')">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `).join('');

        return latestCustomers;
    } catch (error) {
        console.error('Error loading customers:', error);
        showToast('Không thể tải danh sách khách hàng', 'danger');
        return [];
    }
}

async function fetchCustomerDetail(customerId) {
    const result = await api.get(`/customers/${encodeURIComponent(customerId)}`);
    if (!result?.success) {
        throw new Error(result?.detail || result?.error || 'Không thể tải chi tiết khách hàng');
    }
    return result.data;
}

function renderCustomerSummary(customer) {
    const activePackage = customer.current_package
        ? `<span class="badge bg-primary">${safeValue(customer.current_package.package_type)}</span>`
        : '<span class="text-muted">Không có</span>';

    document.getElementById('customerDetailTitle').textContent = `${customer.name || 'Khách hàng'} (${customer.customer_id})`;
    document.getElementById('customerSummary').innerHTML = `
        <div class="col-md-4">
            <div class="border rounded p-3 h-100">
                <div class="small text-muted">Khách hàng</div>
                <div class="fw-semibold">${safeValue(customer.name)}</div>
                <div><code>${escapeHtml(customer.customer_id)}</code></div>
            </div>
        </div>
        <div class="col-md-4">
            <div class="border rounded p-3 h-100">
                <div class="small text-muted">Liên hệ</div>
                <div>${safeValue(customer.phone)}</div>
                <div>${safeValue(customer.email)}</div>
            </div>
        </div>
        <div class="col-md-4">
            <div class="border rounded p-3 h-100">
                <div class="small text-muted">Phân loại</div>
                <div><span class="badge bg-${getCustomerTypeBadge(customer.customer_type)}">${escapeHtml(getCustomerTypeLabel(customer.customer_type))}</span> ${activeBadge(customer.is_active)}</div>
                <div class="mt-1">Gói hiện tại: ${activePackage}</div>
            </div>
        </div>
        <div class="col-md-4">
            <div class="border rounded p-3 h-100">
                <div class="small text-muted">Định danh</div>
                <div>CCCD: ${safeValue(customer.id_card)}</div>
                <div>Địa chỉ: ${safeValue(customer.address)}</div>
            </div>
        </div>
        <div class="col-md-4">
            <div class="border rounded p-3 h-100">
                <div class="small text-muted">Lượt gửi xe</div>
                <div>Tổng lượt: <strong>${customer.total_sessions || 0}</strong></div>
                <div>Đang gửi: <strong>${customer.active_sessions || 0}</strong></div>
            </div>
        </div>
        <div class="col-md-4">
            <div class="border rounded p-3 h-100">
                <div class="small text-muted">Thanh toán</div>
                <div>Tổng phí: <strong>${formatCurrency(customer.total_spent || 0)}</strong></div>
                <div>Ghi chú: ${safeValue(customer.notes, '-')}</div>
            </div>
        </div>
    `;
}

function renderCustomerVehicles(customer) {
    const tbody = document.getElementById('customerVehiclesTable');
    const vehicles = customer.vehicles || [];
    const cards = customer.rfid_cards || [];

    if (!vehicles.length) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">Khách hàng chưa đăng ký xe</td></tr>';
        return;
    }

    tbody.innerHTML = vehicles.map(vehicle => `
        <tr>
            <td><code>${escapeHtml(vehicle.vehicle_id)}</code></td>
            <td><strong>${safeValue(vehicle.plate_number)}</strong></td>
            <td><span class="badge bg-info">${escapeHtml(getVehicleTypeLabel(vehicle.vehicle_type))}</span></td>
            <td>${rfidForVehicle(vehicle, cards)}</td>
            <td>${activeBadge(vehicle.is_active)}</td>
            <td>${formatDate(vehicle.updated_at || vehicle.created_at)}</td>
            <td>
                <button class="btn btn-outline-primary btn-sm" onclick="openEditVehicle('${escapeHtml(vehicle.vehicle_id)}')">
                    <i class="bi bi-pencil-square"></i> Sửa
                </button>
            </td>
        </tr>
    `).join('');
}

async function viewCustomer(customerId) {
    try {
        currentCustomerDetail = await fetchCustomerDetail(customerId);
        renderCustomerSummary(currentCustomerDetail);
        renderCustomerVehicles(currentCustomerDetail);
        document.getElementById('editCurrentCustomerBtn').onclick = () => openEditCustomer(customerId);
        customerDetailModal.show();
    } catch (error) {
        console.error('Error loading customer detail:', error);
        showToast('Không thể xem chi tiết khách hàng', 'danger');
    }
}

async function openEditCustomer(customerId) {
    try {
        const customer = currentCustomerDetail?.customer_id === customerId
            ? currentCustomerDetail
            : await fetchCustomerDetail(customerId);

        currentCustomerDetail = customer;
        returnToDetailAfterCustomerEdit = document.getElementById('customerDetailModal').classList.contains('show');
        document.getElementById('editCustomerId').value = customer.customer_id;
        document.getElementById('editCustomerName').value = customer.name || '';
        document.getElementById('editCustomerPhone').value = customer.phone || '';
        document.getElementById('editCustomerEmail').value = customer.email || '';
        document.getElementById('editCustomerIdCard').value = customer.id_card || '';
        document.getElementById('editCustomerType').value = customer.customer_type || 'walk_in';
        document.getElementById('editCustomerActive').value = String(customer.is_active !== false);
        document.getElementById('editCustomerAddress').value = customer.address || '';
        document.getElementById('editCustomerNotes').value = customer.notes || '';
        if (returnToDetailAfterCustomerEdit) {
            customerDetailModal.hide();
            setTimeout(() => customerEditModal.show(), 150);
        } else {
            customerEditModal.show();
        }
    } catch (error) {
        console.error('Error opening customer edit:', error);
        showToast('Không thể mở form sửa khách hàng', 'danger');
    }
}

async function submitCustomerEdit(event) {
    event.preventDefault();

    const customerId = document.getElementById('editCustomerId').value;
    const payload = {
        name: document.getElementById('editCustomerName').value.trim(),
        phone: nullableText(document.getElementById('editCustomerPhone').value),
        email: nullableText(document.getElementById('editCustomerEmail').value),
        id_card: nullableText(document.getElementById('editCustomerIdCard').value),
        customer_type: document.getElementById('editCustomerType').value,
        is_active: document.getElementById('editCustomerActive').value === 'true',
        address: nullableText(document.getElementById('editCustomerAddress').value),
        notes: nullableText(document.getElementById('editCustomerNotes').value)
    };

    if (!payload.name) {
        showToast('Họ tên khách hàng là bắt buộc', 'warning');
        return;
    }

    const result = await api.put(`/customers/${encodeURIComponent(customerId)}`, payload);
    if (!result?.success) {
        showToast(result?.detail || result?.error || 'Không thể lưu khách hàng', 'danger');
        return;
    }

    currentCustomerDetail = await fetchCustomerDetail(customerId);
    renderCustomerSummary(currentCustomerDetail);
    renderCustomerVehicles(currentCustomerDetail);
    showToast('Đã cập nhật khách hàng', 'success');
    customerEditModal.hide();
    await loadCustomers();
}

function vehicleById(vehicleId) {
    return (currentCustomerDetail?.vehicles || []).find(vehicle => vehicle.vehicle_id === vehicleId);
}

function openEditVehicle(vehicleId) {
    const vehicle = vehicleById(vehicleId);
    if (!vehicle) {
        showToast('Không tìm thấy xe cần sửa', 'danger');
        return;
    }

    document.getElementById('editVehicleId').value = vehicle.vehicle_id;
    document.getElementById('editVehiclePlate').value = vehicle.plate_number || '';
    document.getElementById('editVehicleType').value = ['motorbike', 'car'].includes(vehicle.vehicle_type)
        ? vehicle.vehicle_type
        : 'motorbike';
    document.getElementById('editVehicleActive').value = String(vehicle.is_active !== false);
    returnToDetailAfterVehicleEdit = document.getElementById('customerDetailModal').classList.contains('show');
    if (returnToDetailAfterVehicleEdit) {
        customerDetailModal.hide();
        setTimeout(() => vehicleEditModal.show(), 150);
    } else {
        vehicleEditModal.show();
    }
}

async function submitVehicleEdit(event) {
    event.preventDefault();

    const vehicleId = document.getElementById('editVehicleId').value;
    const payload = {
        plate_number: document.getElementById('editVehiclePlate').value.trim().toUpperCase(),
        vehicle_type: document.getElementById('editVehicleType').value,
        is_active: document.getElementById('editVehicleActive').value === 'true'
    };

    if (!payload.plate_number) {
        showToast('Biển số xe là bắt buộc', 'warning');
        return;
    }

    const result = await api.put(`/vehicles/${encodeURIComponent(vehicleId)}`, payload);
    if (!result?.success) {
        showToast(result?.detail || result?.error || 'Không thể lưu xe', 'danger');
        return;
    }

    showToast('Đã cập nhật xe', 'success');

    if (currentCustomerDetail?.customer_id) {
        currentCustomerDetail = await fetchCustomerDetail(currentCustomerDetail.customer_id);
        renderCustomerSummary(currentCustomerDetail);
        renderCustomerVehicles(currentCustomerDetail);
    }
    vehicleEditModal.hide();
    await loadCustomers();
}

async function deleteCustomer(customerId) {
    if (!confirm('Bạn có chắc muốn xóa khách hàng này? Thao tác này cũng xóa xe, thẻ và dữ liệu liên quan nếu khách không có phiên gửi xe đang hoạt động.')) return;

    try {
        const result = await api.delete(`/customers/${encodeURIComponent(customerId)}`);
        if (result.success) {
            showToast('Xóa thành công', 'success');
            await loadCustomers();
        } else {
            showToast(result.detail || result.error || 'Không thể xóa khách hàng', 'danger');
        }
    } catch (error) {
        console.error('Error deleting customer:', error);
        showToast('Không thể xóa khách hàng', 'danger');
    }
}

function bindCustomerModals() {
    const detailModalEl = document.getElementById('customerDetailModal');
    const customerEditModalEl = document.getElementById('customerEditModal');
    const vehicleEditModalEl = document.getElementById('vehicleEditModal');

    customerDetailModal = new bootstrap.Modal(detailModalEl);
    customerEditModal = new bootstrap.Modal(customerEditModalEl);
    vehicleEditModal = new bootstrap.Modal(vehicleEditModalEl);

    customerEditModalEl.addEventListener('hidden.bs.modal', () => {
        if (returnToDetailAfterCustomerEdit) {
            returnToDetailAfterCustomerEdit = false;
            customerDetailModal.show();
        }
    });

    vehicleEditModalEl.addEventListener('hidden.bs.modal', () => {
        if (returnToDetailAfterVehicleEdit) {
            returnToDetailAfterVehicleEdit = false;
            customerDetailModal.show();
        }
    });

    document.getElementById('customerEditForm').addEventListener('submit', submitCustomerEdit);
    document.getElementById('vehicleEditForm').addEventListener('submit', submitVehicleEdit);
}

function initCustomersPage() {
    bindCustomerModals();
    loadCustomers();
    if (!customersAutoRefresh) {
        customersAutoRefresh = setInterval(() => {
            const modalOpen = document.querySelector('.modal.show');
            if (!modalOpen) loadCustomers();
        }, 10000);
    }
}

document.addEventListener('DOMContentLoaded', initCustomersPage);
