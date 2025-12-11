# backend/app.py - Fixed and working version
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import json
import os
from datetime import datetime
from jsonschema import validate, ValidationError
import uuid

app = Flask(__name__, static_folder='../frontend', static_url_path='')
CORS(app)

# File paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, 'reservations.json')
SCHEMA_FILE = os.path.join(BASE_DIR, 'reservation_schema.json')

# Ensure data file exists
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'w') as f:
        json.dump([], f, indent=2)

# Load schema
with open(SCHEMA_FILE, 'r') as f:
    RESERVATION_SCHEMA = json.load(f)

def read_reservations():
    """Read all reservations from JSON file"""
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except:
        return []

def save_reservations(data):
    """Save reservations to JSON file"""
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def validate_reservation(data):
    """Validate reservation against schema"""
    try:
        validate(instance=data, schema=RESERVATION_SCHEMA)
        return True, None
    except ValidationError as e:
        return False, str(e)

def convert_to_xml(data_list):
    """Convert reservation list to XML format"""
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<reservations>'
    for item in data_list:
        xml += f'\n  <reservation id="{item.get("id", "")}">'
        xml += f'\n    <guest_name>{item.get("guest_name", "")}</guest_name>'
        xml += f'\n    <email>{item.get("email", "")}</email>'
        xml += f'\n    <phone>{item.get("phone", "")}</phone>'
        xml += f'\n    <resort>{item.get("resort_name", "")}</resort>'
        xml += f'\n    <checkin>{item.get("checkin_date", "")}</checkin>'
        xml += f'\n    <checkout>{item.get("checkout_date", "")}</checkout>'
        xml += f'\n    <guests>{item.get("guests", 1)}</guests>'
        xml += f'\n    <payment>{item.get("payment_gateway", "")}</payment>'
        xml += '\n  </reservation>'
    xml += '\n</reservations>'
    return xml

@app.route('/')
def serve_frontend():
    """Serve the main frontend page"""
    return send_from_directory(app.static_folder, 'index.html')

# RESTful API Endpoints
@app.route('/api/reservations', methods=['GET'])
def get_all_reservations():
    """GET /resource - Fetch all reservations"""
    format_type = request.args.get('format', 'json')
    search_query = request.args.get('q', '')
    
    reservations = read_reservations()
    
    # Apply search filter
    if search_query:
        query = search_query.lower()
        filtered = []
        for res in reservations:
            if (query in res.get('guest_name', '').lower() or 
                query in res.get('email', '').lower() or
                query in res.get('resort_name', '').lower()):
                filtered.append(res)
        reservations = filtered
    
    if format_type == 'xml':
        xml_data = convert_to_xml(reservations)
        return xml_data, 200, {'Content-Type': 'application/xml'}
    
    return jsonify(reservations), 200

@app.route('/api/reservations', methods=['POST'])
def create_reservation():
    """POST /resource - Create new reservation"""
    format_type = request.args.get('format', 'json')
    
    if request.headers.get('Content-Type') == 'application/xml':
        # Parse XML
        xml_data = request.data.decode('utf-8')
        # Simple XML parsing (for demo - in production use proper XML parser)
        try:
            # Extract data from simple XML format
            data = {
                'guest_name': extract_xml_value(xml_data, 'guest_name'),
                'email': extract_xml_value(xml_data, 'email'),
                'phone': extract_xml_value(xml_data, 'phone'),
                'resort_name': extract_xml_value(xml_data, 'resort_name'),
                'checkin_date': extract_xml_value(xml_data, 'checkin_date'),
                'checkout_date': extract_xml_value(xml_data, 'checkout_date'),
                'guests': int(extract_xml_value(xml_data, 'guests') or 1),
                'payment_gateway': extract_xml_value(xml_data, 'payment_gateway')
            }
        except:
            return jsonify({'error': 'Invalid XML format'}), 400
    else:
        # Parse JSON
        data = request.get_json()
    
    # Generate ID and timestamps
    data['id'] = str(uuid.uuid4())
    data['created_at'] = datetime.now().isoformat()
    data['updated_at'] = datetime.now().isoformat()
    
    # Validate
    is_valid, error = validate_reservation(data)
    if not is_valid:
        return jsonify({'error': error}), 400
    
    # Save
    reservations = read_reservations()
    reservations.append(data)
    save_reservations(reservations)
    
    if format_type == 'xml':
        xml_data = convert_to_xml([data])
        return xml_data, 201, {'Content-Type': 'application/xml'}
    
    return jsonify(data), 201

def extract_xml_value(xml, tag):
    """Extract value from simple XML format"""
    start = xml.find(f'<{tag}>')
    if start == -1:
        return ''
    end = xml.find(f'</{tag}>')
    return xml[start + len(tag) + 2:end]

@app.route('/api/reservations/<reservation_id>', methods=['GET'])
def get_reservation(reservation_id):
    """GET /resource/{id} - Get specific reservation"""
    format_type = request.args.get('format', 'json')
    
    reservations = read_reservations()
    reservation = next((r for r in reservations if r.get('id') == reservation_id), None)
    
    if not reservation:
        return jsonify({'error': 'Reservation not found'}), 404
    
    if format_type == 'xml':
        xml_data = convert_to_xml([reservation])
        return xml_data, 200, {'Content-Type': 'application/xml'}
    
    return jsonify(reservation), 200

@app.route('/api/reservations/<reservation_id>', methods=['PUT'])
def update_reservation(reservation_id):
    """PUT /resource/{id} - Update reservation"""
    format_type = request.args.get('format', 'json')
    
    reservations = read_reservations()
    index = next((i for i, r in enumerate(reservations) if r.get('id') == reservation_id), None)
    
    if index is None:
        return jsonify({'error': 'Reservation not found'}), 404
    
    if request.headers.get('Content-Type') == 'application/xml':
        xml_data = request.data.decode('utf-8')
        data = {
            'guest_name': extract_xml_value(xml_data, 'guest_name'),
            'email': extract_xml_value(xml_data, 'email'),
            'phone': extract_xml_value(xml_data, 'phone'),
            'resort_name': extract_xml_value(xml_data, 'resort_name'),
            'checkin_date': extract_xml_value(xml_data, 'checkin_date'),
            'checkout_date': extract_xml_value(xml_data, 'checkout_date'),
            'guests': int(extract_xml_value(xml_data, 'guests') or 1),
            'payment_gateway': extract_xml_value(xml_data, 'payment_gateway')
        }
    else:
        data = request.get_json()
    
    # Keep existing ID and timestamps
    data['id'] = reservation_id
    data['created_at'] = reservations[index]['created_at']
    data['updated_at'] = datetime.now().isoformat()
    
    # Validate
    is_valid, error = validate_reservation(data)
    if not is_valid:
        return jsonify({'error': error}), 400
    
    # Update
    reservations[index] = data
    save_reservations(reservations)
    
    if format_type == 'xml':
        xml_data = convert_to_xml([data])
        return xml_data, 200, {'Content-Type': 'application/xml'}
    
    return jsonify(data), 200

@app.route('/api/reservations/<reservation_id>', methods=['DELETE'])
def delete_reservation(reservation_id):
    """DELETE /resource/{id} - Delete reservation"""
    format_type = request.args.get('format', 'json')
    
    reservations = read_reservations()
    new_reservations = [r for r in reservations if r.get('id') != reservation_id]
    
    if len(new_reservations) == len(reservations):
        return jsonify({'error': 'Reservation not found'}), 404
    
    save_reservations(new_reservations)
    
    if format_type == 'xml':
        xml_response = f'''<?xml version="1.0" encoding="UTF-8"?>
<response>
  <message>Reservation {reservation_id} deleted successfully</message>
  <status>success</status>
</response>'''
        return xml_response, 200, {'Content-Type': 'application/xml'}
    
    return jsonify({'message': f'Reservation {reservation_id} deleted successfully'}), 200

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'endpoints': {
            'GET /api/reservations': 'List all reservations',
            'POST /api/reservations': 'Create reservation',
            'GET /api/reservations/{id}': 'Get specific reservation',
            'PUT /api/reservations/{id}': 'Update reservation',
            'DELETE /api/reservations/{id}': 'Delete reservation'
        },
        'supported_formats': ['json', 'xml']
    })

if __name__ == '__main__':
    print("Resort Booking API Server Starting...")
    print("Frontend: http://localhost:5000")
    print("API Base: http://localhost:5000/api/reservations")
    print("Test with: curl http://localhost:5000/api/reservations?format=xml")
    print("Press Ctrl+C to stop\n")
    app.run(debug=True, port=5000)