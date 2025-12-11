const API_BASE = 'http://localhost:5000/api/reservations';
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
    console.log('Resort Booking System Loaded');
    console.log('API Endpoints:');
    console.log('- GET    /api/reservations');
    console.log('- POST   /api/reservations');
    console.log('- GET    /api/reservations/:id');
    console.log('- PUT    /api/reservations/:id');
    console.log('- DELETE /api/reservations/:id');
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
            // Parse XML response (simplified)
            const parser = new DOMParser();
            const xmlDoc = parser.parseFromString(xmlText, 'text/xml');
            const reservations = Array.from(xmlDoc.getElementsByTagName('reservation')).map(res => ({
                id: res.getAttribute('id'),
                guest_name: getXmlValue(res, 'guest_name'),
                email: getXmlValue(res, 'email'),
                phone: getXmlValue(res, 'phone'),
                resort_name: getXmlValue(res, 'resort'),
                checkin_date: getXmlValue(res, 'checkin'),
                checkout_date: getXmlValue(res, 'checkout'),
                guests: parseInt(getXmlValue(res, 'guests') || 1),
                payment_gateway: getXmlValue(res, 'payment')
            }));
            renderTable(reservations);
        } else {
            const reservations = await response.json();
            renderTable(reservations);
        }
    } catch (error) {
        console.error('Error loading reservations:', error);
        showMessage('Failed to load reservations', 'error');
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
                <td colspan="8" style="text-align: center; padding: 40px;">
                    📭 No reservations found
                </td>
            </tr>
        `;
        return;
    }
    
    reservations.forEach(reservation => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td><code>${reservation.id.substring(0, 8)}...</code></td>
            <td>${escapeHtml(reservation.guest_name || '')}</td>
            <td>${escapeHtml(reservation.email || '')}</td>
            <td>${escapeHtml(reservation.resort_name || '')}</td>
            <td>${reservation.checkin_date || ''}</td>
            <td>${reservation.checkout_date || ''}</td>
            <td>${reservation.guests || 1}</td>
            <td>
                <button class="action-btn view" onclick="viewReservation('${reservation.id}')">👁 View</button>
                <button class="action-btn edit" onclick="editReservation('${reservation.id}')">✏ Edit</button>
                <button class="action-btn delete" onclick="deleteReservation('${reservation.id}')">🗑 Delete</button>
            </td>
        `;
        reservationsTable.appendChild(row);
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
            options.body = `
                <reservation>
                    <guest_name>${formData.guest_name}</guest_name>
                    <email>${formData.email}</email>
                    <phone>${formData.phone || ''}</phone>
                    <street_address>${formData.street_address || ''}</street_address>
                    <municipality>${formData.municipality || ''}</municipality>
                    <region>${formData.region || ''}</region>
                    <country>${formData.country || ''}</country>
                    <resort_name>${formData.resort_name}</resort_name>
                    <checkin_date>${formData.checkin_date}</checkin_date>
                    <checkout_date>${formData.checkout_date}</checkout_date>
                    <guests>${formData.guests}</guests>
                    <payment_gateway>${formData.payment_gateway || ''}</payment_gateway>
                </reservation>
            `;
            url += '?format=xml';
        } else {
            options.headers['Content-Type'] = 'application/json';
            options.body = JSON.stringify(formData);
        }
        
        if (editMode) {
            url = `${API_BASE}/${currentEditId}`;
            if (format === 'xml') url += '?format=xml';
        }
        
        const response = await fetch(url, options);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        showMessage(
            editMode ? 'Reservation updated successfully!' : 'Reservation created successfully!',
            'success'
        );
        
        resetForms();
        loadReservations();
        
    } catch (error) {
        console.error('Error submitting reservation:', error);
        showMessage(`Failed to ${editMode ? 'update' : 'create'} reservation`, 'error');
    }
}

function getFormData() {
    return {
        guest_name: document.getElementById('guest_name').value,
        email: document.getElementById('email').value,
        phone: document.getElementById('phone').value,
        street_address: document.getElementById('street_address').value,
        municipality: document.getElementById('municipality').value,
        region: document.getElementById('region').value,
        country: document.getElementById('country').value,
        resort_name: document.getElementById('resort_name').value,
        checkin_date: document.getElementById('checkin_date').value,
        checkout_date: document.getElementById('checkout_date').value,
        guests: parseInt(document.getElementById('guests').value),
        payment_gateway: document.getElementById('payment_gateway').value
    };
}

function validateForms() {
    const requiredFields = ['guest_name', 'email', 'resort_name', 'checkin_date', 'checkout_date', 'guests'];
    
    for (const fieldId of requiredFields) {
        const field = document.getElementById(fieldId);
        if (!field.value.trim()) {
            showMessage(`Please fill in all required fields: ${fieldId.replace('_', ' ')}`, 'error');
            field.focus();
            return false;
        }
    }
    
    const checkin = document.getElementById('checkin_date').value;
    const checkout = document.getElementById('checkout_date').value;
    
    if (checkin && checkout && new Date(checkout) <= new Date(checkin)) {
        showMessage('Check-out date must be after check-in date', 'error');
        return false;
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
}

function cancelEdit() {
    resetForms();
    showMessage('Edit cancelled', 'info');
}

async function viewReservation(id) {
    try {
        const format = responseFormat.value;
        const response = await fetch(`${API_BASE}/${id}?format=${format}`);
        
        let details;
        if (format === 'xml') {
            const xmlText = await response.text();
            details = xmlText;
        } else {
            const data = await response.json();
            details = JSON.stringify(data, null, 2);
        }
        
        document.getElementById('modalDetails').textContent = details;
        document.getElementById('viewModal').style.display = 'block';
        
    } catch (error) {
        console.error('Error viewing reservation:', error);
        showMessage('Failed to load reservation details', 'error');
    }
}

async function editReservation(id) {
    try {
        const response = await fetch(`${API_BASE}/${id}`);
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
        submitJsonBtn.textContent = '💾 Update as JSON';
        submitXmlBtn.textContent = '📄 Update as XML';
        
        showMessage('Editing reservation. Make your changes and click Update.', 'info');
        
    } catch (error) {
        console.error('Error loading reservation for edit:', error);
        showMessage('Failed to load reservation for editing', 'error');
    }
}

async function deleteReservation(id) {
    if (!confirm('Are you sure you want to delete this reservation?')) return;
    
    try {
        const response = await fetch(`${API_BASE}/${id}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            showMessage('Reservation deleted successfully', 'success');
            loadReservations();
        } else {
            throw new Error(`HTTP ${response.status}`);
        }
    } catch (error) {
        console.error('Error deleting reservation:', error);
        showMessage('Failed to delete reservation', 'error');
    }
}

function toggleFormat() {
    const currentFormat = currentFormatSpan.textContent;
    const newFormat = currentFormat === 'JSON' ? 'XML' : 'JSON';
    
    currentFormatSpan.textContent = newFormat;
    toggleFormatBtn.textContent = `Switch to ${currentFormat}`;
    
    showMessage(`Submission format changed to ${newFormat}`, 'info');
}

function showMessage(message, type) {
    // Remove existing messages
    const existingMessages = document.querySelectorAll('.status');
    existingMessages.forEach(msg => msg.remove());
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `status ${type}`;
    messageDiv.textContent = message;
    
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
                resort_name: 'Test Resort',
                checkin_date: '2024-12-25',
                checkout_date: '2024-12-28',
                guests: 2
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

// editReservation