// Updated script.js with sequential ID support and improved functionality
// const API_BASE = 'http://localhost:5000/reservations';
const API_BASE = '/reservations';
let editMode = false;
let currentEditId = null;

// DOM Elements
const personalForm = document.getElementById('personalForm');
const bookingForm = document.getElementById('bookingForm');
const submitJsonBtn = document.getElementById('submitJson');
const submitXmlBtn = document.getElementById('submitXml');
const cancelEditBtn = document.getElementById('cancelEdit');
const searchInput = document.getElementById('searchInput');
const searchBtn = document.getElementById('searchBtn');
const refreshBtn = document.getElementById('refreshBtn');
const responseFormat = document.getElementById('responseFormat');
const toggleFormatBtn = document.getElementById('toggleFormat');
const currentFormatSpan = document.getElementById('currentFormat');
const reservationsTable = document.querySelector('#reservationsTable tbody');

// Set min dates for date inputs
const today = new Date().toISOString().split('T')[0];
document.getElementById('checkin_date').min = today;

// Event Listeners
submitJsonBtn.addEventListener('click', () => submitReservation('json'));
submitXmlBtn.addEventListener('click', () => submitReservation('xml'));
cancelEditBtn.addEventListener('click', cancelEdit);
searchBtn.addEventListener('click', loadReservations);
refreshBtn.addEventListener('click', () => {
    searchInput.value = '';
    loadReservations();
});
toggleFormatBtn.addEventListener('click', toggleFormat);

searchInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') loadReservations();
});

// Date validation
document.getElementById('checkin_date').addEventListener('change', function() {
    const checkinDate = this.value;
    const checkoutInput = document.getElementById('checkout_date');
    if (checkinDate) {
        const nextDay = new Date(checkinDate);
        nextDay.setDate(nextDay.getDate() + 1);
        checkoutInput.min = nextDay.toISOString().split('T')[0];
        if (checkoutInput.value && checkoutInput.value < checkinDate) {
            checkoutInput.value = '';
        }
    }
});

// Load reservations on page load
window.addEventListener('load', () => {
    loadReservations();
    console.log('🏝️ Resort Booking System Loaded');
    console.log('🔗 API Endpoints:');
    console.log('- GET    http://localhost:5000/reservations');
    console.log('- POST   http://localhost:5000/reservations');
    console.log('- GET    http://localhost:5000/reservations/{id}');
    console.log('- PUT    http://localhost:5000/reservations/{id}');
    console.log('- DELETE http://localhost:5000/reservations/{id}');
    console.log('💡 Tip: Use /api/reservations for frontend, /reservations for Postman');
});

// Functions
async function loadReservations() {
    try {
        const searchQuery = searchInput.value.trim();
        const format = responseFormat.value;
        
        let url = `${API_BASE}?format=${format}`;
        if (searchQuery) {
            url += `&q=${encodeURIComponent(searchQuery)}`;
        }
        
        const response = await fetch(url);
        
        if (format === 'xml') {
            const xmlText = await response.text();
            // Parse XML response
            const parser = new DOMParser();
            const xmlDoc = parser.parseFromString(xmlText, 'text/xml');
            const reservations = Array.from(xmlDoc.getElementsByTagName('reservation')).map(res => ({
                id: res.getAttribute('id') || getXmlValue(res, 'id'),
                guest_name: getXmlValue(res, 'guest_name'),
                email: getXmlValue(res, 'email'),
                phone: getXmlValue(res, 'phone'),
                street_address: getXmlValue(res, 'street_address'),
                municipality: getXmlValue(res, 'municipality'),
                region: getXmlValue(res, 'region'),
                country: getXmlValue(res, 'country'),
                resort_name: getXmlValue(res, 'resort_name'),
                checkin_date: getXmlValue(res, 'checkin_date'),
                checkout_date: getXmlValue(res, 'checkout_date'),
                guests: parseInt(getXmlValue(res, 'guests') || 1),
                payment_gateway: getXmlValue(res, 'payment_gateway'),
                created_at: getXmlValue(res, 'created_at')
            }));
            renderTable(reservations);
        } else {
            const reservations = await response.json();
            renderTable(reservations);
        }
    } catch (error) {
        console.error('Error loading reservations:', error);
        showMessage('Failed to load reservations. Make sure the backend server is running.', 'error');
    }
}

function getXmlValue(element, tagName) {
    const tag = element.getElementsByTagName(tagName)[0];
    return tag ? tag.textContent : '';
}

function renderTable(reservations) {
    reservationsTable.innerHTML = '';
    
    if (reservations.length === 0) {
        reservationsTable.innerHTML = `
            <tr>
                <td colspan="8" style="text-align: center; padding: 40px; color: #666;">
                    📭 No reservations found. Create your first reservation above!
                </td>
            </tr>
        `;
        return;
    }
    
    // Sort by ID (numeric, newest first)
    reservations.sort((a, b) => {
        const idA = parseInt(a.id) || 0;
        const idB = parseInt(b.id) || 0;
        return idB - idA; // Descending (newest first)
    });
    
    reservations.forEach(reservation => {
        const row = document.createElement('tr');
        const id = reservation.id;
        const shortId = typeof id === 'string' && id.length > 8 ? `#${id.substring(0, 8)}...` : `#${id}`;
        
        row.innerHTML = `
            <td><strong style="font-size: 1.1em; color: #2c3e50;">#${id}</strong></td>
            <td>${escapeHtml(reservation.guest_name || '')}</td>
            <td>${escapeHtml(reservation.email || '')}</td>
            <td>${escapeHtml(reservation.resort_name || '')}</td>
            <td>${formatDate(reservation.checkin_date) || ''}</td>
            <td>${formatDate(reservation.checkout_date) || ''}</td>
            <td><span class="guest-count">${reservation.guests || 1}</span></td>
            <td>
                <button class="action-btn view" onclick="viewReservation('${id}')" title="View Details">👁 View</button>
                <button class="action-btn edit" onclick="editReservation('${id}')" title="Edit">✏ Edit</button>
                <button class="action-btn delete" onclick="deleteReservation('${id}')" title="Delete">🗑 Delete</button>
            </td>
        `;
        reservationsTable.appendChild(row);
    });
}

function formatDate(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric' 
    });
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

async function submitReservation(format) {
    // Validate forms
    if (!validateForms()) return;
    
    const formData = getFormData();
    
    try {
        let url = API_BASE;
        let options = {
            method: editMode ? 'PUT' : 'POST',
            headers: {},
            body: ''
        };
        
        if (format === 'xml') {
            options.headers['Content-Type'] = 'application/xml';
            options.body = `<?xml version="1.0" encoding="UTF-8"?>
<reservation>
    <guest_name>${escapeXml(formData.guest_name)}</guest_name>
    <email>${escapeXml(formData.email)}</email>
    <phone>${escapeXml(formData.phone || '')}</phone>
    <street_address>${escapeXml(formData.street_address || '')}</street_address>
    <municipality>${escapeXml(formData.municipality || '')}</municipality>
    <region>${escapeXml(formData.region || '')}</region>
    <country>${escapeXml(formData.country || '')}</country>
    <resort_name>${escapeXml(formData.resort_name)}</resort_name>
    <checkin_date>${escapeXml(formData.checkin_date)}</checkin_date>
    <checkout_date>${escapeXml(formData.checkout_date)}</checkout_date>
    <guests>${escapeXml(formData.guests.toString())}</guests>
    <payment_gateway>${escapeXml(formData.payment_gateway || '')}</payment_gateway>
</reservation>`;
            if (editMode) {
                url = `${API_BASE}/${currentEditId}?format=xml`;
            } else {
                url = `${API_BASE}?format=xml`;
            }
        } else {
            options.headers['Content-Type'] = 'application/json';
            options.body = JSON.stringify(formData);
            if (editMode) {
                url = `${API_BASE}/${currentEditId}`;
            }
        }
        
        const response = await fetch(url, options);
        
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`HTTP ${response.status}: ${errorText}`);
        }
        
        const successMessage = editMode 
            ? `✅ Reservation #${currentEditId} updated successfully!` 
            : `✅ Reservation created successfully!`;
        
        showMessage(successMessage, 'success');
        
        resetForms();
        loadReservations();
        
    } catch (error) {
        console.error('Error submitting reservation:', error);
        showMessage(`❌ Failed to ${editMode ? 'update' : 'create'} reservation: ${error.message}`, 'error');
    }
}

function escapeXml(unsafe) {
    if (!unsafe) return '';
    return unsafe.toString()
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&apos;');
}

function getFormData() {
    return {
        guest_name: document.getElementById('guest_name').value.trim(),
        email: document.getElementById('email').value.trim(),
        phone: document.getElementById('phone').value.trim(),
        street_address: document.getElementById('street_address').value.trim(),
        municipality: document.getElementById('municipality').value.trim(),
        region: document.getElementById('region').value.trim(),
        country: document.getElementById('country').value.trim(),
        resort_name: document.getElementById('resort_name').value,
        checkin_date: document.getElementById('checkin_date').value,
        checkout_date: document.getElementById('checkout_date').value,
        guests: parseInt(document.getElementById('guests').value) || 1,
        payment_gateway: document.getElementById('payment_gateway').value
    };
}

function validateForms() {
    const requiredFields = ['guest_name', 'email', 'resort_name', 'checkin_date', 'checkout_date', 'guests'];
    
    for (const fieldId of requiredFields) {
        const field = document.getElementById(fieldId);
        if (!field.value.trim()) {
            const fieldName = fieldId.replace('_', ' ');
            showMessage(`❌ Please fill in: ${fieldName}`, 'error');
            field.focus();
            field.style.borderColor = '#e74c3c';
            setTimeout(() => field.style.borderColor = '', 2000);
            return false;
        }
    }
    
    // Email validation
    const email = document.getElementById('email').value;
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
        showMessage('❌ Please enter a valid email address', 'error');
        document.getElementById('email').focus();
        return false;
    }
    
    // Date validation
    const checkin = document.getElementById('checkin_date').value;
    const checkout = document.getElementById('checkout_date').value;
    
    if (checkin && checkout) {
        const checkinDate = new Date(checkin);
        const checkoutDate = new Date(checkout);
        
        if (checkoutDate <= checkinDate) {
            showMessage('❌ Check-out date must be after check-in date', 'error');
            document.getElementById('checkout_date').focus();
            return false;
        }
        
        // Optional: Check if check-in is at least tomorrow
        const tomorrow = new Date();
        tomorrow.setDate(tomorrow.getDate() + 1);
        tomorrow.setHours(0, 0, 0, 0);
        
        if (checkinDate < tomorrow) {
            showMessage('⚠️ Check-in date should be at least tomorrow', 'warning');
        }
    }
    
    // Phone validation (optional but nice to have)
    const phone = document.getElementById('phone').value;
    if (phone && !/^09\d{9}$/.test(phone)) {
        showMessage('⚠️ Phone should be 11 digits starting with 09 (e.g., 09171234567)', 'warning');
    }
    
    return true;
}

function resetForms() {
    personalForm.reset();
    bookingForm.reset();
    editMode = false;
    currentEditId = null;
    cancelEditBtn.style.display = 'none';
    submitJsonBtn.textContent = '📤 Submit as JSON';
    submitXmlBtn.textContent = '📄 Submit as XML';
    document.getElementById('checkin_date').min = today;
    document.getElementById('country').value = 'Philippines'; // Default value
}

function cancelEdit() {
    resetForms();
    showMessage('🔄 Edit cancelled', 'info');
}

async function viewReservation(id) {
    try {
        const format = responseFormat.value;
        const response = await fetch(`${API_BASE}/${id}?format=${format}`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        let details;
        if (format === 'xml') {
            const xmlText = await response.text();
            // Format XML for display
            const formattedXml = formatXmlForDisplay(xmlText);
            details = formattedXml;
        } else {
            const data = await response.json();
            details = JSON.stringify(data, null, 2);
        }
        
        document.getElementById('modalDetails').textContent = details;
        document.getElementById('viewModal').style.display = 'block';
        
        // Add syntax highlighting
        if (format === 'json') {
            document.getElementById('modalDetails').innerHTML = syntaxHighlight(JSON.stringify(data, null, 2));
        }
        
    } catch (error) {
        console.error('Error viewing reservation:', error);
        showMessage(`❌ Failed to load reservation #${id}`, 'error');
    }
}

function formatXmlForDisplay(xml) {
    // Simple XML formatting for display
    let formatted = '';
    let indent = '';
    const tabs = '\t';
    
    xml.split(/>\s*</).forEach(element => {
        if (element.match(/^\/\w/)) {
            indent = indent.substring(tabs.length);
        }
        
        formatted += indent + '<' + element + '>\r\n';
        
        if (element.match(/^<?\w[^>]*[^\/]$/)) {
            indent += tabs;
        }
    });
    
    return formatted.substring(1, formatted.length - 3);
}

function syntaxHighlight(json) {
    json = json.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    return json.replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, 
    function (match) {
        let cls = 'number';
        if (/^"/.test(match)) {
            if (/:$/.test(match)) {
                cls = 'key';
            } else {
                cls = 'string';
            }
        } else if (/true|false/.test(match)) {
            cls = 'boolean';
        } else if (/null/.test(match)) {
            cls = 'null';
        }
        return '<span class="' + cls + '">' + match + '</span>';
    });
}

async function editReservation(id) {
    try {
        const response = await fetch(`${API_BASE}/${id}`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const reservation = await response.json();
        
        // Fill form with reservation data
        document.getElementById('guest_name').value = reservation.guest_name || '';
        document.getElementById('email').value = reservation.email || '';
        document.getElementById('phone').value = reservation.phone || '';
        document.getElementById('street_address').value = reservation.street_address || '';
        document.getElementById('municipality').value = reservation.municipality || '';
        document.getElementById('region').value = reservation.region || '';
        document.getElementById('country').value = reservation.country || '';
        document.getElementById('resort_name').value = reservation.resort_name || '';
        document.getElementById('checkin_date').value = reservation.checkin_date || '';
        document.getElementById('checkout_date').value = reservation.checkout_date || '';
        document.getElementById('guests').value = reservation.guests || 1;
        document.getElementById('payment_gateway').value = reservation.payment_gateway || '';
        
        // Set edit mode
        editMode = true;
        currentEditId = id;
        cancelEditBtn.style.display = 'inline-block';
        submitJsonBtn.textContent = `💾 Update #${id} as JSON`;
        submitXmlBtn.textContent = `📄 Update #${id} as XML`;
        
        // Scroll to form
        document.querySelector('.two-column').scrollIntoView({ behavior: 'smooth' });
        
        showMessage(`✏️ Editing reservation #${id}. Make your changes and click Update.`, 'info');
        
    } catch (error) {
        console.error('Error loading reservation for edit:', error);
        showMessage(`❌ Failed to load reservation #${id} for editing`, 'error');
    }
}

async function deleteReservation(id) {
    if (!confirm(`Are you sure you want to delete reservation #${id}?\nThis action cannot be undone.`)) return;
    
    try {
        const response = await fetch(`${API_BASE}/${id}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            showMessage(`✅ Reservation #${id} deleted successfully`, 'success');
            loadReservations();
        } else {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP ${response.status}`);
        }
    } catch (error) {
        console.error('Error deleting reservation:', error);
        showMessage(`❌ Failed to delete reservation #${id}: ${error.message}`, 'error');
    }
}

function toggleFormat() {
    const currentFormat = currentFormatSpan.textContent;
    const newFormat = currentFormat === 'JSON' ? 'XML' : 'JSON';
    
    currentFormatSpan.textContent = newFormat;
    toggleFormatBtn.textContent = `Switch to ${currentFormat}`;
    
    showMessage(`🔄 Submission format changed to ${newFormat}`, 'info');
}

function showMessage(message, type) {
    // Remove existing messages
    const existingMessages = document.querySelectorAll('.status');
    existingMessages.forEach(msg => msg.remove());
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `status ${type}`;
    messageDiv.innerHTML = message;
    
    // Add icon based on type
    const icons = {
        'success': '✅',
        'error': '❌',
        'warning': '⚠️',
        'info': 'ℹ️'
    };
    
    if (icons[type]) {
        messageDiv.innerHTML = `${icons[type]} ${message}`;
    }
    
    // Insert after header
    const header = document.querySelector('header');
    header.parentNode.insertBefore(messageDiv, header.nextSibling);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (messageDiv.parentNode) {
            messageDiv.remove();
        }
    }, 5000);
}

// Modal close functionality
document.querySelector('.close').addEventListener('click', () => {
    document.getElementById('viewModal').style.display = 'none';
});

window.onclick = (event) => {
    const modal = document.getElementById('viewModal');
    if (event.target === modal) {
        modal.style.display = 'none';
    }
};

// API testing functions
async function testEndpoint(method) {
    try {
        let url = API_BASE;
        let options = { method };
        
        if (method === 'POST') {
            options.headers = { 'Content-Type': 'application/json' };
            options.body = JSON.stringify({
                guest_name: 'Test User',
                email: 'test@example.com',
                phone: '09171234567',
                street_address: '123 Test Street',
                municipality: 'Quezon City',
                region: 'NCR',
                country: 'Philippines',
                resort_name: 'Test Resort',
                checkin_date: '2024-12-25',
                checkout_date: '2024-12-28',
                guests: 2,
                payment_gateway: 'GCash'
            });
        }
        
        const response = await fetch(url, options);
        const result = await response.json();
        
        alert(`${method} request successful!\nStatus: ${response.status}\nResponse: ${JSON.stringify(result, null, 2)}`);
        
        if (method === 'GET') {
            loadReservations();
        }
    } catch (error) {
        alert(`Test failed: ${error.message}`);
    }
}

// Add some CSS for syntax highlighting
const style = document.createElement('style');
style.textContent = `
    .status {
        padding: 12px 20px;
        border-radius: 8px;
        margin: 15px 0;
        text-align: center;
        font-weight: 500;
        animation: fadeIn 0.3s ease-in;
    }
    
    .status.success {
        background: #d4edda;
        color: #155724;
        border: 2px solid #c3e6cb;
    }
    
    .status.error {
        background: #f8d7da;
        color: #721c24;
        border: 2px solid #f5c6cb;
    }
    
    .status.warning {
        background: #fff3cd;
        color: #856404;
        border: 2px solid #ffeaa7;
    }
    
    .status.info {
        background: #d1ecf1;
        color: #0c5460;
        border: 2px solid #bee5eb;
    }
    
    .guest-count {
        display: inline-block;
        background: #3498db;
        color: white;
        width: 24px;
        height: 24px;
        border-radius: 50%;
        text-align: center;
        line-height: 24px;
        font-weight: bold;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(-10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    #modalDetails {
        background: #f8f9fa;
        padding: 20px;
        border-radius: 8px;
        font-family: 'Courier New', monospace;
        font-size: 14px;
        white-space: pre-wrap;
        word-wrap: break-word;
        max-height: 400px;
        overflow-y: auto;
    }
    
    .string { color: green; }
    .number { color: blue; }
    .boolean { color: purple; }
    .null { color: gray; }
    .key { color: #d14; font-weight: bold; }
`;
document.head.appendChild(style);