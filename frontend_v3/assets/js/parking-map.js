// Parking Map Logic

function escapeHtml(value) {
    return String(value ?? '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#039;');
}

function getSlotsFromMapResult(result) {
    if (Array.isArray(result?.data)) return result.data;
    if (result?.map && typeof result.map === 'object') return Object.values(result.map).flat();
    return [];
}

function isValidPoint(point) {
    return Number.isFinite(Number(point?.x)) && Number.isFinite(Number(point?.y));
}

function hasValidPolygon(slot) {
    return Array.isArray(slot?.points) && slot.points.length >= 3 && slot.points.every(isValidPoint);
}

function polygonPointString(points) {
    return points
        .map(point => `${Number(point.x).toFixed(3)},${Number(point.y).toFixed(3)}`)
        .join(' ');
}

function getLayoutBoundary(layout) {
    const boundary = layout?.boundary_points || layout?.boundary || [];
    return hasValidPolygon({ points: boundary }) ? boundary : [];
}

function getLayoutObstacles(layout) {
    const obstacles = layout?.obstacle_points || layout?.obstacles || [];
    if (!Array.isArray(obstacles)) return [];
    return obstacles.filter(points => hasValidPolygon({ points }));
}

function getSlotCenter(slot) {
    if (Number.isFinite(Number(slot.x)) && Number.isFinite(Number(slot.y))) {
        return { x: Number(slot.x), y: Number(slot.y) };
    }

    const points = slot.points || [];
    const total = points.reduce(
        (acc, point) => ({ x: acc.x + Number(point.x), y: acc.y + Number(point.y) }),
        { x: 0, y: 0 }
    );
    return {
        x: total.x / Math.max(points.length, 1),
        y: total.y / Math.max(points.length, 1),
    };
}

function getLayoutBounds(slots, layout = null) {
    const canvasWidth = Number(layout?.canvas_width_px);
    const canvasHeight = Number(layout?.canvas_height_px);
    if (Number.isFinite(canvasWidth) && Number.isFinite(canvasHeight) && canvasWidth > 0 && canvasHeight > 0) {
        return { minX: 0, minY: 0, width: canvasWidth, height: canvasHeight };
    }

    const boundary = getLayoutBoundary(layout);
    const obstacles = getLayoutObstacles(layout);
    const points = [
        ...slots.flatMap(slot => slot.points || []),
        ...boundary,
        ...obstacles.flat(),
    ];
    const xs = points.map(point => Number(point.x)).filter(Number.isFinite);
    const ys = points.map(point => Number(point.y)).filter(Number.isFinite);

    if (!xs.length || !ys.length) {
        return { minX: 0, minY: 0, width: 1000, height: 600 };
    }

    const padding = 32;
    const minX = Math.min(...xs) - padding;
    const minY = Math.min(...ys) - padding;
    const maxX = Math.max(...xs) + padding;
    const maxY = Math.max(...ys) + padding;

    return {
        minX,
        minY,
        width: Math.max(maxX - minX, 100),
        height: Math.max(maxY - minY, 100),
    };
}

function setStatistics(statistics = {}) {
    document.getElementById('availableCount').textContent = statistics.available || 0;
    document.getElementById('occupiedCount').textContent = statistics.occupied || 0;
    document.getElementById('reservedCount').textContent = statistics.reserved || 0;
    document.getElementById('maintenanceCount').textContent = statistics.maintenance || 0;
}

function renderEmptyMap(message) {
    const grid = document.getElementById('parkingGrid');
    grid.className = 'parking-grid';
    grid.innerHTML = `<div class="text-center text-muted py-4">${escapeHtml(message)}</div>`;
}

function renderLegacyGrid(slots, warning = '') {
    const grid = document.getElementById('parkingGrid');
    grid.className = 'parking-grid';
    const warningHtml = warning
        ? `<div class="legacy-map-warning">${escapeHtml(warning)}</div>`
        : '';

    grid.innerHTML = `
        ${warningHtml}
        ${slots.map(slot => `
            <div class="parking-slot ${escapeHtml(slot.status)}" data-slot-id="${escapeHtml(slot.slot_id)}">
                <div><i class="bi bi-car-front-fill"></i></div>
                <div>${escapeHtml(slot.slot_number || slot.slot_id)}</div>
                ${slot.is_fixed_slot ? '<div class="slot-fixed-marker"><i class="bi bi-pin-angle-fill"></i></div>' : ''}
            </div>
        `).join('')}
    `;

    grid.querySelectorAll('.parking-slot[data-slot-id]').forEach(slotElement => {
        slotElement.addEventListener('click', () => showSlotDetails(slotElement.dataset.slotId));
    });
}

function renderPolygonLayout(slots, layout = null) {
    const grid = document.getElementById('parkingGrid');
    const bounds = getLayoutBounds(slots, layout);
    const labelSize = Math.max(Math.min(bounds.width / 45, 13), 7);
    const boundary = getLayoutBoundary(layout);
    const obstacles = getLayoutObstacles(layout);
    const hasMetadata = boundary.length > 0 || obstacles.length > 0;

    grid.className = 'parking-layout-host';
    grid.innerHTML = `
        <div class="parking-layout-toolbar">
            <div>
                <strong>Layout thực tế</strong>
                <span class="text-muted small">
                    ${hasMetadata
                        ? 'Hiển thị ranh giới, vật cản và slot đã xác nhận từ Thiết kế bãi đỗ'
                        : 'Hiển thị slot theo tọa độ đã xác nhận từ Thiết kế bãi đỗ'}
                </span>
            </div>
            <span class="badge bg-primary">${slots.length} slot</span>
        </div>
        <div class="parking-layout-scroll">
            <svg class="parking-layout-svg"
                 viewBox="${bounds.minX} ${bounds.minY} ${bounds.width} ${bounds.height}"
                 role="img"
                 aria-label="Sơ đồ bãi đỗ theo layout thực tế">
                ${boundary.length ? `<polygon class="layout-boundary" points="${polygonPointString(boundary)}"></polygon>` : ''}
                ${obstacles.map((points, index) => `
                    <polygon class="layout-obstacle"
                             data-obstacle-index="${index + 1}"
                             points="${polygonPointString(points)}"></polygon>
                `).join('')}
                ${slots.map(slot => {
                    const center = getSlotCenter(slot);
                    return `
                        <g class="layout-slot ${escapeHtml(slot.status)}"
                           data-fixed-slot="${slot.is_fixed_slot ? 'true' : 'false'}"
                           data-slot-id="${escapeHtml(slot.slot_id)}"
                           tabindex="0"
                           role="button"
                           aria-label="Slot ${escapeHtml(slot.slot_number || slot.slot_id)}${slot.is_fixed_slot ? ' fixed' : ''}">
                            <polygon points="${polygonPointString(slot.points)}"></polygon>
                            <text class="layout-slot-label"
                                  x="${center.x}"
                                  y="${center.y}"
                                  font-size="${labelSize}">
                                ${escapeHtml(slot.slot_number || slot.slot_id)}
                            </text>
                            ${slot.is_fixed_slot ? `
                                <text class="layout-slot-fixed-label"
                                      x="${center.x}"
                                      y="${center.y + labelSize + 5}"
                                      font-size="${Math.max(labelSize - 2, 7)}">
                                    FIX
                                </text>
                            ` : ''}
                        </g>
                    `;
                }).join('')}
            </svg>
        </div>
    `;

    grid.querySelectorAll('.layout-slot[data-slot-id]').forEach(slotElement => {
        slotElement.addEventListener('click', () => showSlotDetails(slotElement.dataset.slotId));
        slotElement.addEventListener('keydown', event => {
            if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                showSlotDetails(slotElement.dataset.slotId);
            }
        });
    });
}

function renderParkingMap(result) {
    const slots = getSlotsFromMapResult(result);
    const layout = result.layout || null;
    const statistics = result.statistics || {};
    setStatistics(statistics);

    if (!slots.length) {
        renderEmptyMap('Chưa có chỗ đỗ nào. Vui lòng khởi tạo hoặc lưu layout từ Thiết kế bãi đỗ.');
        return;
    }

    const slotsWithPolygon = slots.filter(hasValidPolygon);
    if (slotsWithPolygon.length === slots.length) {
        renderPolygonLayout(slots, layout);
        return;
    }

    const missingCount = slots.length - slotsWithPolygon.length;
    const warning = slotsWithPolygon.length > 0
        ? `Có ${missingCount} slot thiếu tọa độ polygon, đang dùng grid cũ để tránh mất dữ liệu vận hành.`
        : '';
    renderLegacyGrid(slots, warning);
}

async function loadParkingMap() {
    try {
        console.log('Loading parking map...');
        const result = await api.get('/slots/map');
        console.log('Parking map result:', result);

        if (!result || !result.success) {
            showToast('Không thể tải map chỗ đỗ. Kiểm tra backend đã chạy chưa.', 'danger');
            setStatistics();
            renderEmptyMap('Không thể tải dữ liệu map chỗ đỗ.');
            return;
        }

        renderParkingMap(result);
    } catch (error) {
        console.error('Error loading parking map:', error);
        showToast('Lỗi tải map chỗ đỗ', 'danger');
    }
}

async function showSlotDetails(slotId) {
    try {
        const result = await api.get(`/slots/${encodeURIComponent(slotId)}`);

        if (!result.success) {
            showToast('Không thể tải chi tiết', 'danger');
            return;
        }

        const slot = result.data;
        const detailsDiv = document.getElementById('slotDetails');

        let html = `
            <div class="mb-3">
                <strong>Số chỗ:</strong> ${escapeHtml(slot.slot_number || slot.slot_id)}<br>
                <strong>Trạng thái:</strong> <span class="badge bg-${getStatusBadge(slot.status)}">${getStatusLabel(slot.status)}</span>
            </div>
        `;

        if (slot.status === 'occupied' && slot.current_session) {
            html += `
                <hr>
                <h6>Thông tin xe đang đỗ:</h6>
                <div>
                    <strong>Biển số:</strong> ${escapeHtml(slot.current_session.plate_number)}<br>
                    <strong>Khách hàng:</strong> ${escapeHtml(slot.current_session.customer_name)}<br>
                    <strong>Thời gian vào:</strong> ${formatDateTime(slot.current_session.check_in_time)}<br>
                    <strong>Thời gian đỗ:</strong> ${calculateDuration(slot.current_session.check_in_time)}
                </div>
            `;
        }

        if (slot.is_fixed_slot) {
            html += `
                <hr>
                <h6>Chỗ cố định:</h6>
                <div>
                    <strong>Biển số được giữ:</strong> ${escapeHtml(slot.reserved_plate_number || 'N/A')}<br>
                    <strong>Khách hàng:</strong> ${escapeHtml(slot.reserved_customer_name || 'N/A')}<br>
                    <strong>SĐT:</strong> ${escapeHtml(slot.reserved_customer_phone || 'N/A')}<br>
                    <strong>Mã xe:</strong> ${escapeHtml(slot.reserved_vehicle_id || 'N/A')}
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
        available: 'success',
        occupied: 'danger',
        reserved: 'warning',
        maintenance: 'secondary',
    };
    return badges[status] || 'secondary';
}

function getStatusLabel(status) {
    const labels = {
        available: 'Trống',
        occupied: 'Đang đỗ',
        reserved: 'Đặt trước',
        maintenance: 'Bảo trì',
    };
    return labels[status] || status;
}

document.addEventListener('DOMContentLoaded', loadParkingMap);
setInterval(loadParkingMap, 10000);
