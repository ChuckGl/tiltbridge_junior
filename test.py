import requests
import json

# Example JSON payload with next_request_ms field
payload = {
    'apikey': 'your_api_key',
    'type': 'tilt',
    'brand': 'tiltbridge_junior',
    'version': '1.0',
    'chipid': 'Orange',
    's_number_wort_0': 1.02,
    's_number_temp_0': 4.44,
    's_number_voltage_0': 0.0,
    's_number_wifi_0': -31,
    's_number_tilt_0': 123.456,
    'next_request_ms': 10000  # Example value for next_request_ms (10 seconds)
}

try:
    # Send POST request with JSON payload
    r = requests.post('http://127.0.0.1/api/endpoint', json=payload, timeout=5)
    response_data = json.loads(r.text)
    next_request_ms = response_data.get('next_request_ms')
    # Handle next_request_ms value if needed
except Exception as e:
    print("Error:", e)
    # Handle error

