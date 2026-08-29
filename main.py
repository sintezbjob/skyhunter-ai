from flask import Flask, jsonify, request, send_from_directory
import requests
import json
import os
from datetime import datetime

# Ищем index.html: сначала в папке public, потом в корне
if os.path.exists('public/index.html'):
    app = Flask(__name__, static_folder='public', static_url_path='')
else:
    app = Flask(__name__, static_folder='.', static_url_path='')

# Безопасная загрузка routes.json (не упадет, если файла нет)
ROUTES_CONFIG = {}
try:
    with open('routes.json', 'r', encoding='utf-8') as f:
        ROUTES_CONFIG = json.load(f)
except FileNotFoundError:
    ROUTES_CONFIG = {
        "countries": {"Georgia": ["TBS"], "Turkey": ["IST", "SAW"]},
        "departure_airports": {"ZRH": {"name": "Zürich"}, "BSL": {"name": "Basel"}, "GVA": {"name": "Geneva"}}
    }

KIWI_API_KEY = os.getenv('KIWI_API_KEY', None)
KIWI_BASE_URL = "https://tequila-api.kiwi.com/v2/search"

def get_mock_prices(from_code, to_code, adults, children, infants):
    import random
    distance_multipliers = {
        ('ZRH', 'TBS'): 1.8, ('BSL', 'TBS'): 1.8, ('GVA', 'TBS'): 1.9,
        ('ZRH', 'IST'): 1.2, ('ZRH', 'WAW'): 0.8, ('ZRH', 'BCN'): 0.9,
    }
    base_price = 150 # Реалистичная базовая цена
    multiplier = distance_multipliers.get((from_code, to_code), 1.5)
    variation = random.uniform(0.9, 1.3)
    
    adult_price = int(base_price * multiplier * variation)
    child_price = int(adult_price * 0.7)
    infant_price = int(adult_price * 0.1)
    total_price = (adult_price * adults) + (child_price * children) + (infant_price * infants)
    
    return {'adult': adult_price, 'child': child_price, 'infant': infant_price, 'total': total_price}

def search_kiwi(from_code, to_code, date_from, date_to, adults, children, infants):
    if not KIWI_API_KEY:
        import random
        prices = get_mock_prices(from_code, to_code, adults, children, infants)
        mock_flights = [
            {
                'id': f'flight_{i}',
                'price': prices['total'] + random.randint(-20, 50),
                'airline': random.choice(['Wizz Air', 'Ryanair', 'EasyJet', 'SWISS', 'Pegasus', 'Georgian Airways']),
                'departure': f'{date_from}T08:00:00',
                'arrival': f'{date_from}T13:30:00',
                'duration': random.randint(14400, 18000), # 4-5 часов в секундах
                'fly_from': from_code,
                'fly_to': to_code,
                'deep_link': f'https://www.kiwi.com/search/results/{from_code}/{to_code}/{date_from}',
                'transfers': random.randint(0, 1),
                'local_departure': f'{date_from}T08:00:00',
                'local_arrival': f'{date_from}T13:30:00'
            }
            for i in range(5)
        ]
        return {'data': sorted(mock_flights, key=lambda x: x['price']), 'currency': 'CHF', 'mock': True}
    else:
        params = {
            'fly_from': from_code, 'fly_to': to_code, 'date_from': date_from, 'date_to': date_to,
            'adults': adults, 'children': children, 'infants': infants, 'curr': 'CHF',
            'apikey': KIWI_API_KEY, 'limit': 10, 'vehicle_type': 'aircraft'
        }
        try:
            response = requests.get(KIWI_BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {'data': [], 'error': str(e), 'currency': 'CHF'}

def format_time(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return f"{hours}ч {minutes}м"

def format_flights(flights_data, include_self_transfer=True):
    formatted = []
    if not flights_data.get('data'):
        return []
    for flight in flights_data['data'][:20]:
        if flight.get('transfers', 0) > 0 and not include_self_transfer:
            continue
        departure = flight.get('local_departure', flight.get('departure', ''))
        arrival = flight.get('local_arrival', flight.get('arrival', ''))
        try:
            dep_time = datetime.fromisoformat(departure.replace('Z', '+00:00')).strftime('%H:%M')
            arr_time = datetime.fromisoformat(arrival.replace('Z', '+00:00')).strftime('%H:%M')
        except:
            dep_time, arr_time = 'N/A', 'N/A'
        
        formatted.append({
            'price': flight.get('price', 0),
            'airline': flight.get('airlines', ['Unknown'])[0] if flight.get('airlines') else 'Unknown',
            'departure_time': dep_time,
            'arrival_time': arr_time,
            'duration': format_time(flight.get('duration', 0)),
            'transfers': flight.get('transfers', 0),
            'route': f"{flight.get('fly_from', 'N/A')} → {flight.get('fly_to', 'N/A')}",
            'link': flight.get('deep_link', '#'),
            'date': departure[:10] if departure else 'N/A'
        })
    return formatted

@app.route('/')
def index():
    if os.path.exists('public/index.html'):
        return send_from_directory('public', 'index.html')
    return send_from_directory('.', 'index.html')

@app.route('/api/routes', methods=['GET'])
def get_routes():
    return jsonify(ROUTES_CONFIG)

@app.route('/api/search', methods=['POST'])
def search():
    data = request.json
    from_code = data.get('from_code')
    to_country = data.get('to_country')
    date_from = data.get('date_from')
    date_to = data.get('date_to')
    adults = int(data.get('adults', 1))
    children = int(data.get('children', 0))
    infants = int(data.get('infants', 0))
    include_self_transfer = data.get('include_self_transfer', True)
    sort_by = data.get('sort_by', 'price')
    
    to_airports = ROUTES_CONFIG['countries'].get(to_country, [])
    if not to_airports:
        return jsonify({'error': 'Invalid destination', 'data': []}), 400
    
    results = []
    for to_code in to_airports:
        flights_data = search_kiwi(from_code, to_code, date_from, date_to, adults, children, infants)
        formatted = format_flights(flights_data, include_self_transfer)
        results.extend(formatted)
    
    if sort_by == 'price':
        results = sorted(results, key=lambda x: x['price'])
    
    return jsonify({
        'flights': results,
        'total': len(results),
        'mock_mode': not KIWI_API_KEY,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/status', methods=['GET'])
def status():
    return jsonify({
        'status': 'ok',
        'kiwi_connected': bool(KIWI_API_KEY),
        'mode': 'REAL' if KIWI_API_KEY else 'MOCK',
        'timestamp': datetime.now().isoformat()
    })
