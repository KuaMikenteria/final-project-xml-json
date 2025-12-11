# backend/app.py - UPDATED FOR RAILWAY DEPLOYMENT
from flask import Flask, request, jsonify, send_from_directory, Response
from flask_cors import CORS
import json
import os
from datetime import datetime
from jsonschema import validate, ValidationError
import xml.etree.ElementTree as ET
from xml.dom import minidom

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

# Load schema - with better error handling
try:
    with open(SCHEMA_FILE, 'r') as f:
        RESERVATION_SCHEMA = json.load(f)
    print("✅ Schema loaded successfully")
except FileNotFoundError:
    print("⚠️ Schema file not found, creating default schema...")
    # Create a simple default schema
    RESERVATION_SCHEMA = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "Resort Reservation",
        "type": "object",
        "properties": {
            "id": {"type": ["string", "number"]},
            "guest_name": {"type": "string", "minLength": 1},
            "email": {"type": "string", "format": "email"},
            "phone": {"type": "string"},
            "street_address": {"type": "string"},
            "municipality": {"type": "string"},
            "region": {"type": "string"},
            "country": {"type": "string"},
            "resort_name": {"type": "string"},
            "checkin_date": {"type": "string"},
            "checkout_date": {"type": "string"},
            "guests": {"type": "integer", "minimum": 1},
            "payment_gateway": {"type": "string"},
            "created_at": {"type": "string"},
            "updated_at": {"type": "string"}
        },
        "required": [
            "guest_name", 
            "email", 
            "resort_name", 
            "checkin_date", 
            "checkout_date", 
            "guests"
        ]
    }
    with open(SCHEMA_FILE, 'w') as f:
        json.dump(RESERVATION_SCHEMA, f, indent=2)
except json.JSONDecodeError as e:
    print(f"❌ Error parsing schema file: {e}")
    exit(1)

def read_reservations():
    """Read all reservations from JSON file with error handling"""
    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
        
        # Ensure it's a list
        if not isinstance(data, list):
            print(f"⚠️ Data is not a list, converting. Type: {type(data)}")
            if isinstance(data, dict):
                data = [data]
            else:
                data = []
        
        # Ensure each item is a dict
        valid_reservations = []
        for item in data:
            if isinstance(item, dict):
                valid_reservations.append(item)
            else:
                print(f"⚠️ Skipping non-dict item: {type(item)}")
        
        return valid_reservations
    except json.JSONDecodeError:
        print("❌ JSON decode error, returning empty list")
        return []
    except Exception as e:
        print(f"❌ Error reading reservations: {e}")
        return []

def save_reservations(data):
    """Save reservations to JSON file"""
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"❌ Error saving reservations: {e}")

def get_next_id():
    """Get the next sequential ID with robust error handling"""
    try:
        reservations = read_reservations()
        
        if not reservations:
            return 1
        
        max_id = 0
        for res in reservations:
            if isinstance(res, dict):
                res_id = res.get('id')
                if res_id is not None:
                    try:
                        id_int = int(res_id)
                        if id_int > max_id:
                            max_id = id_int
                    except (ValueError, TypeError):
                        print(f"⚠️ Could not convert ID '{res_id}' to integer")
                        continue
        
        return max_id + 1
    except Exception as e:
        print(f"❌ Error in get_next_id(): {e}")
        return 1

def validate_reservation(data):
    """Validate reservation against schema"""
    try:
        # Prepare data for validation
        validation_data = data.copy()
        
        # Ensure id is string for schema validation
        if 'id' in validation_data:
            validation_data['id'] = str(validation_data['id'])
        
        # Ensure guests is integer
        if 'guests' in validation_data:
            try:
                validation_data['guests'] = int(validation_data['guests'])
            except (ValueError, TypeError):
                validation_data['guests'] = 1
        
        # Validate against schema
        validate(instance=validation_data, schema=RESERVATION_SCHEMA)
        return True, None
    except ValidationError as e:
        error_message = str(e)
        # Simplify error message
        if "is not of type" in error_message:
            error_message = f"Schema validation failed: {e.message}"
        return False, error_message
    except Exception as e:
        return False, f"Validation error: {str(e)}"

def dict_to_xml(data_dict, root_name="reservation"):
    """Convert dictionary to XML Element"""
    root = ET.Element(root_name)
    
    for key, value in data_dict.items():
        if value is None:
            continue
            
        if isinstance(value, dict):
            # Handle nested objects
            child = ET.SubElement(root, key)
            for sub_key, sub_value in value.items():
                if sub_value is not None:
                    sub_child = ET.SubElement(child, sub_key)
                    sub_child.text = str(sub_value)
        elif isinstance(value, list):
            # Handle lists
            child = ET.SubElement(root, key)
            for item in value:
                if isinstance(item, dict):
                    item_element = ET.SubElement(child, "item")
                    for item_key, item_value in item.items():
                        sub_child = ET.SubElement(item_element, item_key)
                        sub_child.text = str(item_value)
                else:
                    item_element = ET.SubElement(child, "item")
                    item_element.text = str(item)
        else:
            # Handle simple values
            child = ET.SubElement(root, key)
            child.text = str(value)
    
    return root

def prettify_xml(element):
    """Return a pretty-printed XML string"""
    rough_string = ET.tostring(element, encoding='unicode', method='xml')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")

def json_to_xml(data):
    """Convert JSON data to XML format"""
    if isinstance(data, list):
        # Multiple reservations
        root = ET.Element("reservations")
        for item in data:
            reservation = dict_to_xml(item, "reservation")
            root.append(reservation)
    else:
        # Single reservation
        root = dict_to_xml(data, "reservation")
    
    return prettify_xml(root)

def parse_xml_request(xml_string):
    """Parse XML request to dictionary"""
    try:
        root = ET.fromstring(xml_string)
        data = {}
        
        for child in root:
            if child.text is not None:
                data[child.tag] = child.text.strip()
            elif len(child) > 0:
                # Nested element
                data[child.tag] = {}
                for subchild in child:
                    if subchild.text is not None:
                        data[child.tag][subchild.tag] = subchild.text.strip()
        
        # Convert guests to integer if present
        if 'guests' in data:
            try:
                data['guests'] = int(data['guests'])
            except (ValueError, TypeError):
                data['guests'] = 1
        
        return data
    except Exception as e:
        print(f"XML parsing error: {e}")
        return {}

# Serve static files for frontend
@app.route('/')
def serve_frontend():
    """Serve the main frontend page"""
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve_static_files(path):
    """Serve CSS, JS, and other static files"""
    if path.endswith('.css'):
        mimetype = 'text/css'
    elif path.endswith('.js'):
        mimetype = 'application/javascript'
    else:
        mimetype = None
    
    try:
        return send_from_directory(app.static_folder, path, mimetype=mimetype)
    except:
        return send_from_directory(app.static_folder, 'index.html')

# ============ API ENDPOINTS ============

@app.route('/api/reservations', methods=['GET'])
@app.route('/reservations', methods=['GET'])
def get_all_reservations():
    """GET - Fetch all reservations"""
    format_type = request.args.get('format', 'json').lower()
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
        # Convert to XML
        xml_data = json_to_xml(reservations)
        return Response(xml_data, mimetype='application/xml')
    
    return jsonify(reservations), 200

@app.route('/api/reservations', methods=['POST'])
@app.route('/reservations', methods=['POST'])
def create_reservation():
    """POST - Create new reservation"""
    format_type = request.args.get('format', 'json').lower()
    
    # Check content type
    content_type = request.headers.get('Content-Type', '').lower()
    
    data = {}
    if 'xml' in content_type:
        # Parse XML request
        xml_data = request.data.decode('utf-8')
        print(f"📨 Received XML: {xml_data[:200]}...")
        data = parse_xml_request(xml_data)
    else:
        # Parse JSON (default)
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid or empty request body'}), 400
    
    print(f"📨 Parsed data: {data}")
    
    # Generate sequential ID (1, 2, 3, ...)
    next_id = get_next_id()
    data['id'] = next_id
    data['created_at'] = datetime.now().isoformat()
    data['updated_at'] = data['created_at']
    
    # Add default values for optional fields if not present
    optional_fields = ['phone', 'street_address', 'municipality', 'region', 
                      'country', 'payment_gateway']
    for field in optional_fields:
        if field not in data:
            data[field] = ""
    
    # Validate
    is_valid, error = validate_reservation(data)
    if not is_valid:
        print(f"❌ Validation failed: {error}")
        return jsonify({'error': error}), 400
    
    # Save
    reservations = read_reservations()
    reservations.append(data)
    save_reservations(reservations)
    
    print(f"✅ Reservation created with ID: {next_id}")
    
    if format_type == 'xml':
        # Return XML response
        xml_data = json_to_xml(data)
        return Response(xml_data, status=201, mimetype='application/xml')
    
    return jsonify(data), 201

@app.route('/api/reservations/<reservation_id>', methods=['GET'])
@app.route('/reservations/<reservation_id>', methods=['GET'])
def get_reservation(reservation_id):
    """GET /{id} - Get specific reservation"""
    format_type = request.args.get('format', 'json').lower()
    
    reservations = read_reservations()
    
    # Try to find by integer ID
    reservation = None
    try:
        # Convert reservation_id to integer for comparison
        search_id = int(reservation_id)
        for res in reservations:
            if isinstance(res, dict):
                res_id = res.get('id')
                if res_id is not None:
                    try:
                        if int(res_id) == search_id:
                            reservation = res
                            break
                    except (ValueError, TypeError):
                        continue
    except ValueError:
        # If not an integer, try string match
        for res in reservations:
            if isinstance(res, dict) and str(res.get('id')) == str(reservation_id):
                reservation = res
                break
    
    if not reservation:
        return jsonify({'error': f'Reservation {reservation_id} not found'}), 404
    
    if format_type == 'xml':
        # Convert to XML
        xml_data = json_to_xml(reservation)
        return Response(xml_data, mimetype='application/xml')
    
    return jsonify(reservation), 200

@app.route('/api/reservations/<reservation_id>', methods=['PUT'])
@app.route('/reservations/<reservation_id>', methods=['PUT'])
def update_reservation(reservation_id):
    """PUT /{id} - Update reservation"""
    format_type = request.args.get('format', 'json').lower()
    
    reservations = read_reservations()
    
    # Find the reservation
    index = None
    try:
        # Convert reservation_id to integer for comparison
        search_id = int(reservation_id)
        for i, res in enumerate(reservations):
            if isinstance(res, dict):
                res_id = res.get('id')
                if res_id is not None:
                    try:
                        if int(res_id) == search_id:
                            index = i
                            break
                    except (ValueError, TypeError):
                        continue
    except ValueError:
        # If not an integer, try string match
        for i, res in enumerate(reservations):
            if isinstance(res, dict) and str(res.get('id')) == str(reservation_id):
                index = i
                break
    
    if index is None:
        return jsonify({'error': f'Reservation {reservation_id} not found'}), 404
    
    # Check content type
    content_type = request.headers.get('Content-Type', '').lower()
    
    if 'xml' in content_type:
        xml_data = request.data.decode('utf-8')
        data = parse_xml_request(xml_data)
    else:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid or empty request body'}), 400
    
    # Keep existing ID and timestamps
    data['id'] = reservations[index]['id']  # Keep the original ID
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
        # Return XML response
        xml_data = json_to_xml(data)
        return Response(xml_data, mimetype='application/xml')
    
    return jsonify(data), 200

@app.route('/api/reservations/<reservation_id>', methods=['DELETE'])
@app.route('/reservations/<reservation_id>', methods=['DELETE'])
def delete_reservation(reservation_id):
    """DELETE /{id} - Delete reservation"""
    format_type = request.args.get('format', 'json').lower()
    
    reservations = read_reservations()
    
    # Filter out the reservation to delete
    new_reservations = []
    deleted_id = None
    
    for res in reservations:
        if not isinstance(res, dict):
            new_reservations.append(res)
            continue
            
        try:
            # Try integer comparison
            if int(res.get('id', 0)) == int(reservation_id):
                deleted_id = res.get('id')
                continue  # Skip this one (delete it)
        except (ValueError, TypeError):
            # Try string comparison
            if str(res.get('id')) == str(reservation_id):
                deleted_id = res.get('id')
                continue
        
        new_reservations.append(res)
    
    if len(new_reservations) == len(reservations):
        return jsonify({'error': f'Reservation {reservation_id} not found'}), 404
    
    save_reservations(new_reservations)
    
    if format_type == 'xml':
        # Return XML response
        response_data = {
            'message': f'Reservation {deleted_id} deleted successfully',
            'status': 'success',
            'deleted_id': deleted_id
        }
        xml_data = json_to_xml(response_data)
        return Response(xml_data, mimetype='application/xml')
    
    return jsonify({
        'message': f'Reservation {deleted_id} deleted successfully',
        'status': 'success',
        'deleted_id': deleted_id
    }), 200

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    reservations = read_reservations()
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'data_count': len(reservations),
        'next_id': get_next_id(),
        'endpoints': {
            'GET /reservations': 'List all reservations',
            'POST /reservations': 'Create reservation',
            'GET /reservations/{id}': 'Get specific reservation',
            'PUT /reservations/{id}': 'Update reservation',
            'DELETE /reservations/{id}': 'Delete reservation'
        },
        'supported_formats': ['json', 'xml']
    }), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    print("=" * 60)
    print("🏝️  SubiC Resort Reservation API Server Starting...")
    print("=" * 60)
    print(f"\n🌐 Environment: {'Development' if debug else 'Production'}")
    print(f"🔧 Port: {port}")
    print(f"🔗 URL: http://0.0.0.0:{port}")
    
    print("\n📊 Initial Stats:")
    reservations = read_reservations()
    print(f"   Reservations: {len(reservations)}")
    print(f"   Next available ID: {get_next_id()}")
    
    print("\n" + "=" * 60)
    print("✅ Server is ready!")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=port, debug=debug)