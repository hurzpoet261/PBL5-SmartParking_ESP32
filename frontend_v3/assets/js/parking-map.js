// Parking Map Logic

async function loadParkingMap() {
    try {
        console.log('Loading parking map...');
        const result = await api.get('/slots/map');
        console.log('Parking map result:', result);
        
        if (!result || !result.success) {
            showToast('Không thể tải map chỗ đỗ. Kiểm tra backend đã chạy chưa.', 'danger');
            // Set default values
            document.getElementById('availableCount').textContent = '0';
            document.getElementById('occupiedCount').textContent = '0';
            document.getElementById('reservedCount').textContent = '0';
            document.getElementById('maintenanceCount').textContent = '0';
            return;
        }
        
        // Sửa lại điều kiện kiểm tra biến map và total_slots
        if (!result.map || result.total_slots === 0) {
            showToast('Chưa có chỗ đỗ nào. Vui lòng khởi tạo dữ liệu.', 'warning');
            return;
        }
        
        // Rút trích tất cả các ô đỗ xe từ các hàng (row) gộp thành 1 mảng
        const slots = Object.values(result.map).flat();
        const grid = document.getElementById('parkingGrid');
        
        // Count by status
        const counts = {
            available: 0,
            occupied: 0,
            reserved: 0,
            maintenance: 0
        };
        
        slots.forEach(slot => {
            counts[slot.status] = (counts[slot.status] || 0) + 1;
        });
        
        // Update counts
        document.getElementById('availableCount').textContent = counts.available || 0;
        document.getElementById('occupiedCount').textContent = counts.occupied || 0;
        document.getElementById('reservedCount').textContent = counts.reserved || 0;
        document.getElementById('maintenanceCount').textContent = counts.maintenance || 0;
        
        // Render grid
        grid.innerHTML = slots.map(slot => `
            <div class="parking-slot ${slot.status}" onclick="showSlotDetails('${slot.slot_id}')">
                <div><i class="bi bi-car-front-fill"></i></div>
                <div>${slot.slot_number}</div>
            </div>
        `).join('');
        
    } catch (error) {
        console.error('Error loading parking map:', error);
        showToast('Lỗi tải map chỗ đỗ', 'danger');
    }
}

async function showSlotDetails(slotId) {
    try {
        const result = await api.get(`/slots/${slotId}`);
        
        if (!result.success) {
            showToast('Không thể tải chi tiết', 'danger');
            return;
        }
        
        const slot = result.data;
        const detailsDiv = document.getElementById('slotDetails');
        
        let html = `
            <div class="mb-3">
                <strong>Số chỗ:</strong> ${slot.slot_number}<br>
                <strong>Trạng thái:</strong> <span class="badge bg-${getStatusBadge(slot.status)}">${getStatusLabel(slot.status)}</span>
            </div>
        `;
        
        if (slot.status === 'occupied' && slot.current_session) {
            html += `
                <hr>
                <h6>Thông tin xe đang đỗ:</h6>
                <div>
                    <strong>Biển số:</strong> ${slot.current_session.plate_number}<br>
                    <strong>Khách hàng:</strong> ${slot.current_session.customer_name}<br>
                    <strong>Thời gian vào:</strong> ${formatDateTime(slot.current_session.check_in_time)}<br>
                    <strong>Thời gian đỗ:</strong> ${calculateDuration(slot.current_session.check_in_time)}
                </div>
            `;
        }
        
        detailsDiv.innerHTML = html;
        
        const modal = new bootstrap.Modal(document.getElementById('slotModal'));
        modal.show();
        
    } catch (error) {
        console.error('Error loading slot details:', error);
        showToast('Lỗi tải chi tiết', 'danger');
    }
}

function getStatusBadge(status) {
    const badges = {
        'available': 'success',
        'occupied': 'danger',
        'reserved': 'warning',
        'maintenance': 'secondary'
    };
    return badges[status] || 'secondary';
}

function getStatusLabel(status) {
    const labels = {
        'available': 'Trống',
        'occupied': 'Đang đỗ',
        'reserved': 'Đặt trước',
        'maintenance': 'Bảo trì'
    };
    return labels[status] || status;
}

// Initialize
document.addEventListener('DOMContentLoaded', loadParkingMap);

// Auto refresh every 10 seconds
setInterval(loadParkingMap, 10000);
