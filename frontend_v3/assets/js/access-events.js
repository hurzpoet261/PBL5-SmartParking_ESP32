const BACKEND_ROOT = API_BASE_URL.replace(/\/api\/v1$/, '');

let accessEventsTimer = null;
let autoRefreshEnabled = true;
let currentCapture = null;
window.latestCaptures = [];
window.captureByFileId = {};
window.capturesByBatchId = {};

function escapeHtml(value) {
    return String(value ?? '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#039;');
}

function apiImageUrl(path) {
    if (!path) return '';
    return path.startsWith('http') ? path : `${BACKEND_ROOT}${path}`;
}

function fileIdFromCapture(capture) {
    return String(capture?.gridfs_file_id || capture?.file_id || '');
}

function imageUrls(capture) {
    const fileId = fileIdFromCapture(capture);
    return {
        original: apiImageUrl(capture.view_url || `/api/v1/access-events/images/${fileId}`),
        preprocess: `${API_BASE_URL}/access-events/debug/images/${fileId}/preprocess`,
        quality: `${API_BASE_URL}/access-events/debug/images/${fileId}/quality`
    };
}

function imageIdFromEvent(event) {
    const ids = Array.isArray(event?.image_ids) ? event.image_ids : [];
    return ids.length ? String(ids[0]) : '';
}

function rebuildCaptureIndexes(captures) {
    window.captureByFileId = {};
    window.capturesByBatchId = {};

    for (const capture of captures || []) {
        const fileId = fileIdFromCapture(capture);
        const batchId = capture.capture_batch_id || '';
        if (fileId) {
            window.captureByFileId[fileId] = capture;
        }
        if (batchId) {
            if (!window.capturesByBatchId[batchId]) {
                window.capturesByBatchId[batchId] = [];
            }
            window.capturesByBatchId[batchId].push(capture);
        }
    }
}

function captureFromEvent(event) {
    const eventCaptures = Array.isArray(event?.capture_images) ? event.capture_images : [];
    if (eventCaptures.length) {
        return eventCaptures.find(item => item.selected_for_ocr) || eventCaptures[0];
    }

    const imageId = imageIdFromEvent(event);
    if (imageId && window.captureByFileId[imageId]) {
        return window.captureByFileId[imageId];
    }

    const batchCaptures = window.capturesByBatchId[event.capture_batch_id] || [];
    if (batchCaptures.length) {
        return batchCaptures.find(item => item.selected_for_ocr) || batchCaptures[0];
    }

    if (imageId) {
        return {
            gridfs_file_id: imageId,
            view_url: `/api/v1/access-events/images/${imageId}`,
            filename: `${event.capture_batch_id || imageId}.jpg`,
            capture_batch_id: event.capture_batch_id,
            card_uid: event.card_uid,
            ocr_plate: event.ocr_plate,
            ocr_confidence: event.ocr_confidence,
            decision: event.decision,
            reason: event.reason,
        };
    }

    return null;
}

function eventImageHtml(event) {
    const capture = captureFromEvent(event);
    if (!capture) {
        return '<span class="text-muted">-</span>';
    }

    const fileId = fileIdFromCapture(capture);
    const urls = imageUrls(capture);
    const batchId = event.capture_batch_id || capture.capture_batch_id || '';
    const label = escapeHtml(batchId || capture.filename || 'capture');
    return `
        <button class="event-thumb" title="${label}" onclick="openCaptureByFileId('${escapeHtml(fileId)}', '${escapeHtml(batchId)}')">
            <img src="${urls.original}" alt="${label}" loading="lazy">
        </button>
    `;
}

function decisionBadge(decision) {
    if (decision === 'accepted') return 'success';
    if (decision === 'rejected') return 'danger';
    return 'secondary';
}

function actionBadge(action) {
    if (action === 'entry') return 'primary';
    if (action === 'exit') return 'warning';
    return 'secondary';
}

function gateStateSummary(event) {
    if (!event?.gate_open_sent) return 'NO';
    if (event.gate_ack_status === 'acked') return 'SENT / ACK';
    if (event.gate_ack_status === 'failed') return 'SENT / FAIL';
    return 'SENT / WAIT';
}

function gateStatusHtml(event) {
    if (!event?.gate_open_sent) {
        return '<span class="badge bg-secondary">Chua gui</span>';
    }

    const commandId = event.gate_command_id ? String(event.gate_command_id) : '';
    const shortCommandId = commandId ? commandId.slice(-8) : '';
    const commandHtml = shortCommandId
        ? `<div><code title="${escapeHtml(commandId)}">${escapeHtml(shortCommandId)}</code></div>`
        : '';

    let ackBadge = '<span class="badge bg-warning text-dark">Cho ACK</span>';
    if (event.gate_ack_status === 'acked') {
        ackBadge = '<span class="badge bg-success">Barrier mo</span>';
    } else if (event.gate_ack_status === 'failed') {
        ackBadge = '<span class="badge bg-danger">ACK loi</span>';
    } else if (event.gate_ack_status === 'received') {
        ackBadge = '<span class="badge bg-info text-dark">ACK</span>';
    }

    return `
        <div class="d-flex flex-column gap-1">
            <span class="badge bg-primary">Da gui</span>
            ${ackBadge}
            ${commandHtml}
        </div>
    `;
}

async function loadEvents() {
    const limit = document.getElementById('eventLimit')?.value || '20';
    const tbody = document.getElementById('eventsTable');
    const result = await api.get(`/access-events/events?limit=${limit}`);

    if (!result?.success) {
        tbody.innerHTML = '<tr><td colspan="10" class="text-center text-danger">Không tải được access events</td></tr>';
        return [];
    }

    const events = result.events || [];
    document.getElementById('eventCount').textContent = events.length;
    document.getElementById('reviewCount').textContent = events.filter(item => item.review_required).length;

    const latest = events[0];
    if (latest) {
        document.getElementById('lastGateState').textContent = gateStateSummary(latest);
    }

    if (!events.length) {
        tbody.innerHTML = '<tr><td colspan="10" class="text-center text-muted">Chưa có event</td></tr>';
        return events;
    }

    tbody.innerHTML = events.map(event => `
        <tr>
            <td>${formatDateTime(event.created_at)}</td>
            <td>${eventImageHtml(event)}</td>
            <td><code>${escapeHtml(event.card_uid || 'N/A')}</code></td>
            <td><span class="badge bg-${actionBadge(event.event_type)}">${escapeHtml(event.event_type || 'N/A')}</span></td>
            <td><span class="badge bg-${decisionBadge(event.decision)}">${escapeHtml(event.decision || 'N/A')}</span></td>
            <td>
                <div><strong>${escapeHtml(event.ocr_plate || '-')}</strong></div>
                <small class="text-muted">expected: ${escapeHtml(event.expected_plate || '-')}</small>
            </td>
            <td><code>${escapeHtml(event.session_id || '-')}</code></td>
            <td>${escapeHtml(event.reason || event.review_reason || '-')}</td>
            <td>${gateStatusHtml(event)}</td>
            <td>${event.review_required ? '<span class="badge bg-warning">Review</span>' : '<span class="badge bg-success">OK</span>'}</td>
        </tr>
    `).join('');

    return events;
}

async function loadCaptures() {
    const limit = document.getElementById('captureLimit')?.value || '12';
    const grid = document.getElementById('capturesGrid');
    const result = await api.get(`/access-events/captures?limit=${limit}`);

    if (!result?.success) {
        grid.innerHTML = '<div class="text-danger">Không tải được capture images</div>';
        return [];
    }

    const captures = result.captures || [];
    document.getElementById('captureCount').textContent = captures.length;

    if (!captures.length) {
        grid.innerHTML = '<div class="text-muted">Chưa có ảnh capture</div>';
        return captures;
    }

    grid.innerHTML = captures.map((capture, index) => {
        const urls = imageUrls(capture);
        const blur = capture.blur_score ?? 'N/A';
        const selected = capture.selected_for_ocr ? '<span class="badge bg-primary">OCR</span>' : '';
        const decision = capture.decision ? `<span class="badge bg-${decisionBadge(capture.decision)}">${escapeHtml(capture.decision)}</span>` : '';

        return `
            <div class="capture-card">
                <button class="capture-thumb" onclick="openCaptureModal(${index})">
                    <img src="${urls.original}" alt="${escapeHtml(capture.filename || 'capture')}">
                </button>
                <div class="capture-meta">
                    <div class="d-flex justify-content-between gap-2">
                        <code>${escapeHtml(capture.card_uid || 'N/A')}</code>
                        <span>F${escapeHtml(capture.frame_no || '-')}</span>
                    </div>
                    <div class="small text-muted">${formatDateTime(capture.captured_at)}</div>
                    <div class="small">blur: <strong>${escapeHtml(blur)}</strong> ${selected} ${decision}</div>
                    <div class="btn-group btn-group-sm mt-2 w-100">
                        <button class="btn btn-outline-secondary" onclick="openCaptureModal(${index}, 'original')">Gốc</button>
                        <button class="btn btn-outline-secondary" onclick="openCaptureModal(${index}, 'preprocess')">Prep</button>
                    </div>
                </div>
            </div>
        `;
    }).join('');

    window.latestCaptures = captures;
    rebuildCaptureIndexes(captures);
    return captures;
}

function openCaptureModal(index, mode = 'original') {
    const captures = window.latestCaptures || [];
    currentCapture = captures[index];
    if (!currentCapture) return;

    document.getElementById('imageModalTitle').textContent = currentCapture.filename || 'Capture image';
    document.getElementById('modalMetadata').textContent = JSON.stringify(currentCapture, null, 2);
    showModalImage(mode);

    const modal = new bootstrap.Modal(document.getElementById('imageModal'));
    modal.show();
}

function openCaptureByFileId(fileId, batchId = '', mode = 'original') {
    let capture = window.captureByFileId[fileId];
    if (!capture && batchId && window.capturesByBatchId[batchId]?.length) {
        capture = window.capturesByBatchId[batchId].find(item => fileIdFromCapture(item) === fileId)
            || window.capturesByBatchId[batchId][0];
    }
    if (!capture && fileId) {
        capture = {
            gridfs_file_id: fileId,
            view_url: `/api/v1/access-events/images/${fileId}`,
            filename: fileId,
            capture_batch_id: batchId,
        };
    }
    if (!capture) return;

    currentCapture = capture;
    document.getElementById('imageModalTitle').textContent = capture.filename || 'Capture image';
    document.getElementById('modalMetadata').textContent = JSON.stringify(capture, null, 2);
    showModalImage(mode);

    const modal = new bootstrap.Modal(document.getElementById('imageModal'));
    modal.show();
}

function showModalImage(mode) {
    if (!currentCapture) return;
    const urls = imageUrls(currentCapture);
    const src = urls[mode] || urls.original;
    document.getElementById('modalImage').src = `${src}${src.includes('?') ? '&' : '?'}t=${Date.now()}`;
}

async function refreshAccessEvents() {
    const backendOk = await checkBackend();
    const status = document.getElementById('backendStatus');
    status.className = `badge bg-${backendOk ? 'success' : 'danger'}`;
    status.textContent = backendOk ? 'Backend OK' : 'Backend lỗi';

    await loadCaptures();
    await loadEvents();
}

function toggleAutoRefresh() {
    autoRefreshEnabled = !autoRefreshEnabled;
    const button = document.getElementById('toggleAutoRefreshBtn');
    button.innerHTML = autoRefreshEnabled ? '<i class="bi bi-pause-fill"></i>' : '<i class="bi bi-play-fill"></i>';
}

async function resetActiveSession() {
    const uid = document.getElementById('resetCardUid').value.trim();
    const resultBox = document.getElementById('devToolResult');
    if (!uid) {
        showToast('Nhập UID cần reset', 'warning');
        return;
    }

    const result = await api.post(`/access-events/dev/reset-active-session/${encodeURIComponent(uid)}`, {});
    resultBox.textContent = JSON.stringify(result);
    await refreshAccessEvents();
}

async function cleanupStaleSessions(dryRun = false) {
    const days = document.getElementById('cleanupDays').value || 7;
    const resultBox = document.getElementById('devToolResult');
    const result = await api.post(`/access-events/dev/cleanup-active-sessions?older_than_days=${days}&dry_run=${dryRun}`, {});
    resultBox.textContent = JSON.stringify(result);
    await refreshAccessEvents();
}

document.addEventListener('DOMContentLoaded', async () => {
    await refreshAccessEvents();
    accessEventsTimer = setInterval(() => {
        if (autoRefreshEnabled) {
            refreshAccessEvents();
        }
    }, 5000);
});
