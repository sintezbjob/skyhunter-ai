from flask import Flask, jsonify, request, send_from_directory
import json
import os
from datetime import datetime
import random

app = Flask(__name__, static_folder='.', static_url_path='')

# Загрузи маршруты из routes.json (если есть)
ROUTES_CONFIG = {
    "countries": {
        "Turkey": ["IST", "SAW"],
        "Poland": ["WAW", "KRK"],
        "Italy": ["MXP", "BGY", "FCO"],
        "Spain": ["BCN", "MAD"],
        "Hungary": ["BUD"],
        "Greece": ["ATH"],
        "Portugal": ["LIS"],
        "Czechia": ["PRG"],
        "Austria": ["VIE"],
        "Croatia": ["ZAG"],
        "Georgia": ["TBS"],
        "Ukraine": ["KBP", "ODS"]
    },
    "departure_airports": {
        "ZRH": {"name": "Zürich", "time_from_thun": "1h 15min"},
        "BSL": {"name": "Basel", "time_from_thun": "1h 15min"},
        "GVA": {"name": "Geneva", "time_from_thun": "2h 30min"},
        "FKB": {"name": "Karlsruhe", "time_from_thun": "2h"},
        "STR": {"name": "Stuttgart", "time_from_thun": "2h 30min"},
        "MUC": {"name": "Munich", "time_from_thun": "4h"},
        "MXP": {"name": "Milan", "time_from_thun": "3h"},
        "BGY": {"name": "Bergamo", "time_from_thun": "3h 30min"}
    }
}

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/api/routes', methods=['GET'])
def get_routes():
    return jsonify(ROUTES_CONFIG)

@app.route('/api/search', methods=['POST'])
def search():
    data = request.json
    from_code = data.get('from_code')
    to_country = data.get('to_country')
    adults = int(data.get('adults', 2))
    children = int(data.get('children', 0))
    infants = int(data.get('infants', 0))
    
    to_airports = ROUTES_CONFIG['countries'].get(to_country, [])
    if not to_airports:
        return jsonify({'error': 'Invalid destination', 'data': []}), 400
    
    results = []
    for to_code in to_airports:
        base_price = 120
        adult_price = int(base_price * random.uniform(0.8, 1.5))
        child_price = int(adult_price * 0.6)
        infant_price = int(adult_price * 0.1)
        total_price = (adult_price * adults) + (child_price * children) + (infant_price * infants)
        
        results.append({
            'price': total_price,
            'airline': random.choice(['Wizz Air', 'Ryanair', 'EasyJet', 'SWISS']),
            'departure_time': '08:00',
            'arrival_time': '11:30',
            'duration': '3h 30m',
            'transfers': random.randint(0, 1),
            'route': f"{from_code} → {to_code}",
            'link': f'https://www.kiwi.com/search/results/{from_code}/{to_code}',
            'date': '2026-09-15'
        })
    
    results.sort(key=lambda x: x['price'])
    
    return jsonify({
        'flights': results,
        'total': len(results),
        'mock_mode': True,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/status', methods=['GET'])
def status():
    return jsonify({
        'status': 'ok',
        'mode': 'MOCK',
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
