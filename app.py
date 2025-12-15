"""
Resort Booking API Server
Supports JSON and XML formats for both request and response
"""
from flask import Flask, request, jsonify, send_from_directory, Response
from flask_cors import CORS
import json
import os
import re
from datetime import datetime
from jsonschema import validate, ValidationError
import xml.etree.ElementTree as ET
from xml.dom import minidom

# Initialize Flask app
app = Flask(__name__, static_folder='frontend', static_url_path='')
CORS(app)

# File paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, 'backend', 'reservations.json')
SCHEMA_FILE = os.path.join(BASE_DIR, 'backend', 'reservation_schema.json')

# Approved values
APPROVED_RESORTS = [
    "Arcadia Beach Resort",
    "Kuya Boy Beach Resort",
    "Blue Horizon Resort",
    "White Sand Paradise",
    "Mountain View Villa"
]

APPROVED_PAYMENT_GATEWAYS = [
    "Credit Card",
    "GCash",
    "PayPal",
    "Bank Transfer",
    "BANCO DE ORO",
    "Metrobank",
    "BDO"
]

# Ensure data file exists
if not os.path.exists(DATA_FILE):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, 'w') as f:
        json.dump([], f, indent=2)

# Load schema
try:
    with open(SCHEMA_FILE, 'r') as f:
        RESERVATION_SCHEMA = json.load(f)
    print("Schema loaded successfully")
except FileNotFoundError:
    print("ERROR: Schema file not found!")
    exit(1)
except json.JSONDecodeError as e:
    print(f"ERROR: Error parsing schema file: {e}")
    exit(1)


# ============ HELPER FUNCTIONS ============

def read_reservations():
    """Read all reservations from JSON file with error handling"""
    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
        
        # Ensure it's a list
        if not isinstance(data, list):
            if isinstance(data, dict):
                data = [data]
            else:
                data = []
        
        # Ensure each item is a dict
        valid_reservations = []
        for item in data:
            if isinstance(item, dict):
                valid_reservations.append(item)
        
        return valid_reservations
    except json.JSONDecodeError:
        print("ERROR: JSON decode error, returning empty list")
        return []
    except Exception as e:
        print(f"ERROR: Error reading reservations: {e}")
        return []


def save_reservations(data):
    """Save reservations to JSON file"""
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"ERROR: Error saving reservations: {e}")
        raise


def get_next_id():
    """Get the next sequential ID"""
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
                        continue
        
        return max_id + 1
    except Exception as e:
        print(f"ERROR: Error in get_next_id(): {e}")
        return 1


def validate_philippine_phone(phone):
    """Validate Philippine phone number format: 11 digits starting with 09"""
    if not phone:
        return True  # Optional field
    
    # Remove any whitespace
    phone = phone.strip()
    
    # Check if it matches pattern: 09 followed by 9 digits
    pattern = r'^09\d{9}$'
    return bool(re.match(pattern, phone))


def normalize_reservation_data(data):
    """
    Normalize reservation data by trimming string fields
    This ensures consistent data format before validation and saving
    """
    normalized = data.copy()
    
    # Normalize string fields (trim whitespace)
    string_fields = ['guest_name', 'email', 'phone', 'street_address', 
                     'municipality', 'region', 'country', 'resort_name', 
                     'checkin_date', 'checkout_date', 'payment_gateway']
    
    for field in string_fields:
        if field in normalized and normalized[field] is not None:
            if isinstance(normalized[field], str):
                normalized[field] = normalized[field].strip()
            else:
                normalized[field] = str(normalized[field]).strip()
    
    # Ensure guests is integer
    if 'guests' in normalized and normalized['guests'] is not None:
        try:
            normalized['guests'] = int(normalized['guests'])
        except (ValueError, TypeError):
            pass  # Will be caught in validation
    
    return normalized


def validate_reservation(data, is_update=False):
    """
    Validate reservation against schema with custom validators
    
    Args:
        data: Dictionary containing reservation data
        is_update: Boolean indicating if this is an update operation
    
    Returns:
        tuple: (is_valid: bool, error_message: str or None)
    """
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
                return False, "guests must be a valid integer"
        
        # Custom validation: Philippine phone number (if provided and not empty)
        if 'phone' in validation_data and validation_data.get('phone'):
            phone_value = validation_data['phone'].strip() if isinstance(validation_data['phone'], str) else str(validation_data['phone'])
            if phone_value:
                if not validate_philippine_phone(phone_value):
                    return False, "phone must be in Philippine format: 11 digits starting with 09 (e.g., 09171234567)"
                # Normalize phone value (remove any whitespace)
                validation_data['phone'] = phone_value
            else:
                # Empty string - normalize
                validation_data['phone'] = ""
        
        # Custom validation: Resort name must be from approved list
        if 'resort_name' in validation_data and validation_data['resort_name']:
            resort_name = validation_data['resort_name'].strip() if isinstance(validation_data['resort_name'], str) else str(validation_data['resort_name'])
            if resort_name not in APPROVED_RESORTS:
                return False, f"resort_name must be one of: {', '.join(APPROVED_RESORTS)}"
            # Normalize resort name value
            validation_data['resort_name'] = resort_name
        
        # Custom validation: Payment gateway must be from approved list (if provided and not empty)
        if 'payment_gateway' in validation_data:
            payment_gateway = validation_data['payment_gateway'].strip() if isinstance(validation_data.get('payment_gateway'), str) else str(validation_data.get('payment_gateway', ''))
            if payment_gateway:
                if payment_gateway not in APPROVED_PAYMENT_GATEWAYS:
                    return False, f"payment_gateway must be one of: {', '.join(APPROVED_PAYMENT_GATEWAYS)}"
                # Normalize payment gateway value
                validation_data['payment_gateway'] = payment_gateway
            else:
                # Empty string - normalize
                validation_data['payment_gateway'] = ""
        
        # Validate against schema
        validate(instance=validation_data, schema=RESERVATION_SCHEMA)
        return True, None
        
    except ValidationError as e:
        # Extract meaningful error message
        error_path = '.'.join(str(p) for p in e.path) if e.path else 'root'
        error_msg = f"Schema validation failed at {error_path}: {e.message}"
        return False, error_msg
    except Exception as e:
        return False, f"Validation error: {str(e)}"


def get_response_format():
    """
    Determine response format from Accept header or format query parameter
    Returns: 'xml' or 'json'
    """
    # Check query parameter first
    format_param = request.args.get('format', '').lower()
    if format_param in ['xml', 'json']:
        return format_param
    
    # Check Accept header
    accept_header = request.headers.get('Accept', '').lower()
    if 'application/xml' in accept_header or 'text/xml' in accept_header:
        return 'xml'
    if 'application/json' in accept_header:
        return 'json'
    
    # Default to JSON
    return 'json'


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


def json_to_xml(data, root_name="reservation"):
    """Convert JSON data to XML format"""
    if isinstance(data, list):
        # Multiple reservations
        root = ET.Element("reservations")
        for item in data:
            reservation = dict_to_xml(item, "reservation")
            root.append(reservation)
    else:
        # Single reservation
        root = dict_to_xml(data, root_name)
    
    return prettify_xml(root)


def parse_xml_request(xml_string):
    """Parse XML request to dictionary"""
    try:
        root = ET.fromstring(xml_string)
        data = {}
        
        for child in root:
            if child.text is not None:
                text = child.text.strip()
                # Try to convert to appropriate type
                if child.tag == 'guests':
                    try:
                        data[child.tag] = int(text)
                    except ValueError:
                        data[child.tag] = 1
                else:
                    data[child.tag] = text
            elif len(child) > 0:
                # Nested element
                data[child.tag] = {}
                for subchild in child:
                    if subchild.text is not None:
                        data[child.tag][subchild.tag] = subchild.text.strip()
        
        return data
    except ET.ParseError as e:
        print(f"XML parsing error: {e}")
        raise ValueError(f"Invalid XML format: {str(e)}")
    except Exception as e:
        print(f"Error parsing XML: {e}")
        raise ValueError(f"Error parsing XML: {str(e)}")


def parse_request_data():
    """
    Parse request data based on Content-Type header
    Returns: dictionary with parsed data
    """
    content_type = request.headers.get('Content-Type', '').lower()
    
    if 'xml' in content_type:
        # Parse XML request
        try:
            xml_data = request.data.decode('utf-8')
            return parse_xml_request(xml_data)
        except Exception as e:
            raise ValueError(f"Failed to parse XML: {str(e)}")
    else:
        # Parse JSON (default)
        data = request.get_json(force=True)
        if not data:
            raise ValueError("Invalid or empty request body")
        return data


def create_response(data, status_code=200, root_name="reservation"):
    """
    Create response in appropriate format (JSON or XML)
    """
    format_type = get_response_format()
    
    if format_type == 'xml':
        xml_data = json_to_xml(data, root_name)
        return Response(xml_data, status=status_code, mimetype='application/xml')
    else:
        return jsonify(data), status_code


def create_error_response(error_message, status_code=400):
    """Create error response in appropriate format"""
    error_data = {'error': error_message}
    format_type = get_response_format()
    
    if format_type == 'xml':
        xml_data = json_to_xml(error_data, "error")
        return Response(xml_data, status=status_code, mimetype='application/xml')
    else:
        return jsonify(error_data), status_code


# ============ STATIC FILE ROUTES ============

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
    search_query = request.args.get('q', '').strip()
    
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
    
    return create_response(reservations, 200, "reservations")


@app.route('/api/reservations/<reservation_id>', methods=['GET'])
@app.route('/reservations/<reservation_id>', methods=['GET'])
def get_reservation(reservation_id):
    """GET /{id} - Get specific reservation"""
    reservations = read_reservations()
    
    # Find reservation by ID
    reservation = None
    try:
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
        # Try string match
        for res in reservations:
            if isinstance(res, dict) and str(res.get('id')) == str(reservation_id):
                reservation = res
                break
    
    if not reservation:
        return create_error_response(f'Reservation {reservation_id} not found', 404)
    
    return create_response(reservation, 200)


@app.route('/api/reservations', methods=['POST'])
@app.route('/reservations', methods=['POST'])
def create_reservation():
    """POST - Create new reservation"""
    try:
        # Parse request data (JSON or XML)
        data = parse_request_data()
        
        # Normalize data (trim whitespace, etc.)
        data = normalize_reservation_data(data)
        
        # Generate sequential ID and timestamps
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
        is_valid, error = validate_reservation(data, is_update=False)
        if not is_valid:
            return create_error_response(error, 400)
        
        # Save
        reservations = read_reservations()
        reservations.append(data)
        save_reservations(reservations)
        
        print(f"Reservation created with ID: {next_id}")
        return create_response(data, 201)
        
    except ValueError as e:
        return create_error_response(str(e), 400)
    except Exception as e:
        print(f"ERROR: Error creating reservation: {e}")
        return create_error_response(f"Internal server error: {str(e)}", 500)


@app.route('/api/reservations/<reservation_id>', methods=['PUT'])
@app.route('/reservations/<reservation_id>', methods=['PUT'])
def update_reservation(reservation_id):
    """PUT /{id} - Update reservation (id and created_at cannot be edited)"""
    try:
        reservations = read_reservations()
        
        # Find the reservation
        index = None
        try:
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
            # Try string match
            for i, res in enumerate(reservations):
                if isinstance(res, dict) and str(res.get('id')) == str(reservation_id):
                    index = i
                    break
        
        if index is None:
            return create_error_response(f'Reservation {reservation_id} not found', 404)
        
        # Parse request data (JSON or XML)
        data = parse_request_data()
        
        # Normalize data (trim whitespace, etc.)
        data = normalize_reservation_data(data)
        
        # Preserve id and created_at - these cannot be edited
        original_reservation = reservations[index]
        data['id'] = original_reservation['id']
        data['created_at'] = original_reservation['created_at']
        data['updated_at'] = datetime.now().isoformat()
        
        # Add default values for optional fields if not present
        optional_fields = ['phone', 'street_address', 'municipality', 'region', 
                          'country', 'payment_gateway']
        for field in optional_fields:
            if field not in data:
                data[field] = ""
        
        # Validate
        is_valid, error = validate_reservation(data, is_update=True)
        if not is_valid:
            return create_error_response(error, 400)
        
        # Update
        reservations[index] = data
        save_reservations(reservations)
        
        print(f"Reservation {reservation_id} updated")
        return create_response(data, 200)
        
    except ValueError as e:
        return create_error_response(str(e), 400)
    except Exception as e:
        print(f"ERROR: Error updating reservation: {e}")
        return create_error_response(f"Internal server error: {str(e)}", 500)


@app.route('/api/reservations/<reservation_id>', methods=['DELETE'])
@app.route('/reservations/<reservation_id>', methods=['DELETE'])
def delete_reservation(reservation_id):
    """DELETE /{id} - Delete reservation"""
    reservations = read_reservations()
    
    # Filter out the reservation to delete
    new_reservations = []
    deleted_id = None
    found = False
    
    for res in reservations:
        if not isinstance(res, dict):
            new_reservations.append(res)
            continue
        
        try:
            # Try integer comparison
            if int(res.get('id', 0)) == int(reservation_id):
                deleted_id = res.get('id')
                found = True
                continue  # Skip this one (delete it)
        except (ValueError, TypeError):
            # Try string comparison
            if str(res.get('id')) == str(reservation_id):
                deleted_id = res.get('id')
                found = True
                continue
        
        new_reservations.append(res)
    
    if not found:
        return create_error_response(f'Reservation {reservation_id} not found', 404)
    
    save_reservations(new_reservations)
    
    response_data = {
        'message': f'Reservation {deleted_id} deleted successfully',
        'status': 'success',
        'deleted_id': deleted_id
    }
    
    return create_response(response_data, 200, "response")


# ============ HEALTH CHECK ============

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    reservations = read_reservations()
    health_data = {
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
        'supported_formats': ['json', 'xml'],
        'approved_resorts': APPROVED_RESORTS,
        'approved_payment_gateways': APPROVED_PAYMENT_GATEWAYS
    }
    
    return create_response(health_data, 200, "health")


# ============ MAIN ============

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    print("=" * 60)
    print("Resort Reservation API Server Starting...")
    print("=" * 60)
    print(f"\nEnvironment: {'Development' if debug else 'Production'}")
    print(f"Port: {port}")
    print(f"URL: http://0.0.0.0:{port}")
    
    print("\nInitial Stats:")
    reservations = read_reservations()
    print(f"   Reservations: {len(reservations)}")
    print(f"   Next available ID: {get_next_id()}")
    
    print("\nApproved Resorts:")
    for resort in APPROVED_RESORTS:
        print(f"   - {resort}")
    
    print("\nApproved Payment Gateways:")
    for gateway in APPROVED_PAYMENT_GATEWAYS:
        print(f"   - {gateway}")
    
    print("\n" + "=" * 60)
    print("Server is ready!")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=port, debug=debug)
