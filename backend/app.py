from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
from datetime import datetime, timedelta
from collections import defaultdict
import statistics

app = Flask(__name__)
CORS(app)

BASE_URL = "https://hackutd2025.eog.systems/api"

cache = {}
CACHE_DURATION = 60

def get_cached_or_fetch(endpoint, cache_key=None, params=None):
    """Fetch from cache or make API call"""
    key = cache_key or endpoint
    now = datetime.now().timestamp()
    
    if key in cache:
        data, timestamp = cache[key]
        if now - timestamp < CACHE_DURATION:
            return data
    
    try:
        url = f"{BASE_URL}/{endpoint}"
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        cache[key] = (data, now)
        return data
    except Exception as e:
        print(f"Error fetching {endpoint}: {e}")
        # Return cached data if available, even if expired
        if key in cache:
            return cache[key][0]
        raise

@app.route("/")
def home():
    return "Welcome to the HackUTD API proxy! Try /api/couriers, /api/market, or /api/tickets."

@app.route("/api/<path:endpoint>")
def proxy(endpoint):
    """
    Proxy all GET requests to the external API
    Handles query parameters and caching automatically
    """
    try:
        params = request.args.to_dict()
        
        cache_key = f"{endpoint}_{str(params)}" if params else endpoint
        
        data = get_cached_or_fetch(endpoint, cache_key, params if params else None)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/analyze/discrepancy-detection", methods=["GET"])
def discrepancy_detection():
    """Perform full discrepancy detection between tickets and drain data."""
    try:
        historical_data = get_cached_or_fetch("Data", "historical_data")
        tickets_response = get_cached_or_fetch("Tickets", "tickets")
        tickets = tickets_response.get("transport_tickets", [])
        data = convert_historical_data(historical_data)
        drain_events = detect_drain_events(data)
        discrepancies = find_discrepancies(drain_events, tickets)

        return jsonify({
            "success": True,
            "discrepancies": discrepancies,
            "summary": {
                "total": len(discrepancies),
                "critical": len([d for d in discrepancies if d["severity"] == "critical"]),
                "high": len([d for d in discrepancies if d["severity"] == "high"]),
                "medium": len([d for d in discrepancies if d["severity"] == "medium"]),
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
"""Analysis"""

@app.route("/api/analyze/summary")
def analyze_summary():
    """Get quick summary of system status"""
    try:
        force_refresh = request.args.get("forceRefresh", "false").lower() == "true"
        if force_refresh:
            cache.clear()
        # Fetch all required data
        historical_data = get_cached_or_fetch("Data", "historical_data")
        tickets_response = get_cached_or_fetch("Tickets", "tickets")
        cauldrons = get_cached_or_fetch("Information/cauldrons", "cauldrons")
        
        # Convert historical data format
        converted_data = convert_historical_data(historical_data)
        tickets = tickets_response.get('transport_tickets', [])
        
        # Run analyses
        drain_events = detect_drain_events(converted_data)
        discrepancies = find_discrepancies(drain_events, tickets)
        fill_rates = calculate_fill_rates(converted_data)
        predictions = predict_overflow(converted_data, cauldrons, fill_rates, 24)
        
        return jsonify({
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "totalCauldrons": len(cauldrons),
                "totalDrainEvents": len(drain_events),
                "totalTickets": tickets_response.get('metadata', {}).get('total_tickets', len(tickets)),
                "suspiciousTickets": tickets_response.get('metadata', {}).get('suspicious_tickets', 0),
                "discrepancies": {
                    "total": len(discrepancies),
                    "critical": len([d for d in discrepancies if d['severity'] == 'critical']),
                    "high": len([d for d in discrepancies if d['severity'] == 'high']),
                    "medium": len([d for d in discrepancies if d['severity'] == 'medium'])
                },
                "overflowRisk": len([p for p in predictions if p['urgency'] == 'critical'])
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/analyze/drain-events", methods=['POST'])
def analyze_drain_events():
    """
    Detect drain events from historical data
    Expects: { "cauldronId": "optional" }
    """
    try:
        force_refresh = request.args.get("forceRefresh", "false").lower() == "true"
        if force_refresh:
            cache.clear()
        params = request.json or {}
        cauldron_id = params.get('cauldronId')
        
        # Fetch historical data
        historical_data = get_cached_or_fetch("Data", "historical_data")
        converted_data = convert_historical_data(historical_data)
        
        drain_events = detect_drain_events(converted_data, cauldron_id)
        
        return jsonify({
            "success": True,
            "drainEvents": drain_events,
            "count": len(drain_events)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/analyze/discrepancies", methods=['POST'])
def analyze_discrepancies():
    """
    Analyze discrepancies between tickets and actual drains
    Expects: { "ticketThreshold": 0.05 } (optional 5% tolerance)
    """
    try:
        force_refresh = request.args.get("forceRefresh", "false").lower() == "true"
        if force_refresh:
            cache.clear()
        params = request.json or {}
        threshold = params.get('ticketThreshold', 0.05)
        
        # Fetch required data
        historical_data = get_cached_or_fetch("Data", "historical_data")
        tickets_response = get_cached_or_fetch("Tickets", "tickets")
        
        converted_data = convert_historical_data(historical_data)
        tickets = tickets_response.get('transport_tickets', [])
        
        # Detect drain events
        drain_events = detect_drain_events(converted_data)
        
        # Find discrepancies
        discrepancies = find_discrepancies(drain_events, tickets, threshold)
        
        return jsonify({
            "success": True,
            "discrepancies": discrepancies,
            "summary": {
                "total": len(discrepancies),
                "critical": len([d for d in discrepancies if d['severity'] == 'critical']),
                "high": len([d for d in discrepancies if d['severity'] == 'high']),
                "medium": len([d for d in discrepancies if d['severity'] == 'medium'])
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/analyze/fill-rates", methods=['POST'])
def analyze_fill_rates():
    """
    Calculate fill rates for each cauldron
    Expects: { "cauldronId": "optional" }
    """
    try:
        force_refresh = request.args.get("forceRefresh", "false").lower() == "true"
        if force_refresh:
            cache.clear()
        params = request.json or {}
        cauldron_id = params.get('cauldronId')
        
        historical_data = get_cached_or_fetch("Data", "historical_data")
        converted_data = convert_historical_data(historical_data)
        fill_rates = calculate_fill_rates(converted_data, cauldron_id)
        
        return jsonify({
            "success": True,
            "fillRates": fill_rates
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/analyze/predictions", methods=['POST'])
def analyze_predictions():
    """
    Predict when cauldrons will reach capacity
    Expects: { "hoursAhead": 24 }
    """
    try:
        force_refresh = request.args.get("forceRefresh", "false").lower() == "true"
        if force_refresh:
            cache.clear()
        params = request.json or {}
        hours_ahead = params.get('hoursAhead', 24)
        
        historical_data = get_cached_or_fetch("Data", "historical_data")
        cauldrons = get_cached_or_fetch("Information/cauldrons", "cauldrons")
        
        converted_data = convert_historical_data(historical_data)
        fill_rates = calculate_fill_rates(converted_data)
        predictions = predict_overflow(converted_data, cauldrons, fill_rates, hours_ahead)
        
        return jsonify({
            "success": True,
            "predictions": predictions
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =======================
# Helper Functions
# =======================

def convert_historical_data(raw_data):
    """
    Convert API format to analysis format
    From: [{ timestamp, cauldron_levels: { cauldron_001: 123 } }]
    To: [{ timestamp, cauldronId: "cauldron_001", level: 123 }]
    """
    converted = []
    for entry in raw_data:
        timestamp = entry.get('timestamp')
        cauldron_levels = entry.get('cauldron_levels', {})
        
        for cauldron_id, level in cauldron_levels.items():
            converted.append({
                'timestamp': timestamp,
                'cauldronId': cauldron_id,
                'level': level
            })
    
    return converted

# =======================
# Analysis Functions
# =======================

def detect_drain_events(data, cauldron_id=None):
    """
    Detect drain events from time-series data
    A drain is characterized by a significant negative level change
    """
    drain_events = []
    
    # Group data by cauldron
    cauldron_data = defaultdict(list)
    for entry in data:
        cid = entry.get('cauldronId')
        if cauldron_id is None or cid == cauldron_id:
            cauldron_data[cid].append(entry)
    
    # Process each cauldron
    for cid, entries in cauldron_data.items():
        # Sort by timestamp
        entries.sort(key=lambda x: x.get('timestamp', ''))
        
        for i in range(1, len(entries)):
            prev = entries[i-1]
            curr = entries[i]
            
            level_change = curr.get('level', 0) - prev.get('level', 0)
            
            # Detect significant drops (drains)
            # Threshold: drop of more than 10% of previous level or > 50L
            threshold = max(prev.get('level', 0) * 0.1, 50)
            
            if level_change < -threshold:
                # Found a drain event
                prev_time = datetime.fromisoformat(prev['timestamp'].replace('Z', '+00:00'))
                curr_time = datetime.fromisoformat(curr['timestamp'].replace('Z', '+00:00'))
                duration = (curr_time - prev_time).total_seconds() / 60  # minutes
                
                # Estimate fill rate from nearby stable periods
                fill_rate = estimate_fill_rate_at_point(entries, i)
                
                # Calculate total potion removed
                level_drop = abs(level_change)
                potion_generated = fill_rate * duration
                total_removed = level_drop + potion_generated
                
                drain_events.append({
                    "cauldronId": cid,
                    "startTime": prev['timestamp'],
                    "endTime": curr['timestamp'],
                    "duration": round(duration, 2),
                    "levelDrop": round(level_drop, 2),
                    "potionGeneratedDuringDrain": round(potion_generated, 2),
                    "totalPotionRemoved": round(total_removed, 2),
                    "estimatedFillRate": round(fill_rate, 3),
                    "startLevel": round(prev.get('level', 0), 2),
                    "endLevel": round(curr.get('level', 0), 2)
                })
    
    return drain_events

def estimate_fill_rate_at_point(entries, index, lookback=60):
    """
    Estimate fill rate from stable periods before a drain event
    lookback: number of data points to look back
    """
    if index < 2:
        return 0
    
    # Look at previous entries
    start_idx = max(0, index - lookback)
    relevant_entries = entries[start_idx:index]
    
    if len(relevant_entries) < 2:
        return 0
    
    # Calculate positive level changes (filling periods)
    increases = []
    for i in range(1, len(relevant_entries)):
        prev = relevant_entries[i-1]
        curr = relevant_entries[i]
        change = curr.get('level', 0) - prev.get('level', 0)
        
        # Only consider positive changes (filling)
        if change > 0:
            try:
                prev_time = datetime.fromisoformat(prev['timestamp'].replace('Z', '+00:00'))
                curr_time = datetime.fromisoformat(curr['timestamp'].replace('Z', '+00:00'))
                time_diff = (curr_time - prev_time).total_seconds() / 60  # minutes
                
                if time_diff > 0:
                    rate = change / time_diff
                    increases.append(rate)
            except:
                continue
    
    if increases:
        return statistics.median(increases)
    return 0

def calculate_fill_rates(data, cauldron_id=None):
    """Calculate average fill rates for each cauldron"""
    cauldron_data = defaultdict(list)
    
    for entry in data:
        cid = entry.get('cauldronId')
        if cauldron_id is None or cid == cauldron_id:
            cauldron_data[cid].append(entry)
    
    fill_rates = {}
    
    for cid, entries in cauldron_data.items():
        entries.sort(key=lambda x: x.get('timestamp', ''))
        rates = []
        
        for i in range(1, len(entries)):
            prev = entries[i-1]
            curr = entries[i]
            change = curr.get('level', 0) - prev.get('level', 0)
            
            # Only consider increases
            if change > 0:
                try:
                    prev_time = datetime.fromisoformat(prev['timestamp'].replace('Z', '+00:00'))
                    curr_time = datetime.fromisoformat(curr['timestamp'].replace('Z', '+00:00'))
                    time_diff = (curr_time - prev_time).total_seconds() / 60
                    
                    if time_diff > 0:
                        rate = change / time_diff
                        rates.append(rate)
                except:
                    continue
        
        if rates:
            fill_rates[cid] = {
                "average": round(statistics.mean(rates), 3),
                "median": round(statistics.median(rates), 3),
                "min": round(min(rates), 3),
                "max": round(max(rates), 3),
                "samples": len(rates)
            }
    
    return fill_rates

def find_discrepancies(drain_events, tickets, threshold=0.05):
    """
    Match tickets to drain events and identify discrepancies
    threshold: acceptable percentage difference (default 5%)
    """
    discrepancies = []
    
    # Group drains by date and cauldron
    drains_by_date = defaultdict(list)
    for drain in drain_events:
        date = drain['startTime'].split('T')[0]
        key = f"{date}_{drain['cauldronId']}"
        drains_by_date[key].append(drain)
    
    # Group tickets by date and cauldron
    tickets_by_date = defaultdict(list)
    for ticket in tickets:
        date = ticket.get('date', '').split('T')[0]
        cauldron_id = ticket.get('cauldron_id', '')
        key = f"{date}_{cauldron_id}"
        tickets_by_date[key].append(ticket)
    
    # Check all drain events for matching tickets
    for key, drains in drains_by_date.items():
        date, cauldron_id = key.split('_', 1)
        matching_tickets = tickets_by_date.get(key, [])
        total_drained = sum(d['totalPotionRemoved'] for d in drains)
        
        if not matching_tickets:
            # Drain with no ticket - CRITICAL
            discrepancies.append({
                "type": "UNLOGGED_DRAIN",
                "severity": "critical",
                "cauldronId": cauldron_id,
                "date": date,
                "drainEvents": drains,
                "totalVolume": round(total_drained, 2),
                "message": f"Drain detected on {date} for {cauldron_id} but no ticket found! {round(total_drained, 2)}L unaccounted for."
            })
        else:
            # Check volume match
            total_ticket_volume = sum(t.get('amount_collected', 0) for t in matching_tickets)
            difference = abs(total_ticket_volume - total_drained)
            tolerance = total_drained * threshold
            
            if difference > tolerance:
                severity = "critical" if difference > tolerance * 3 else "high" if difference > tolerance * 1.5 else "medium"
                discrepancies.append({
                    "type": "VOLUME_MISMATCH",
                    "severity": severity,
                    "cauldronId": cauldron_id,
                    "date": date,
                    "ticketVolume": round(total_ticket_volume, 2),
                    "actualDrained": round(total_drained, 2),
                    "difference": round(difference, 2),
                    "percentDifference": round((difference / total_drained * 100), 2),
                    "drainEvents": drains,
                    "tickets": matching_tickets,
                    "message": f"Volume mismatch on {date}: Tickets show {round(total_ticket_volume, 2)}L but actual drain was {round(total_drained, 2)}L (difference: {round(difference, 2)}L)"
                })
    
    # Check for tickets without matching drains
    for key, tickets_list in tickets_by_date.items():
        if key not in drains_by_date:
            date, cauldron_id = key.split('_', 1)
            total_ticket_volume = sum(t.get('amount_collected', 0) for t in tickets_list)
            discrepancies.append({
                "type": "PHANTOM_TICKET",
                "severity": "high",
                "cauldronId": cauldron_id,
                "date": date,
                "tickets": tickets_list,
                "ticketVolume": round(total_ticket_volume, 2),
                "message": f"Ticket found for {date} but no drain event detected for {cauldron_id}"
            })
    
    return discrepancies

def predict_overflow(data, cauldrons, fill_rates, hours_ahead=24):
    """
    Predict when cauldrons will reach capacity
    """
    predictions = []
    
    # Create cauldron lookup
    cauldron_map = {c['id']: c for c in cauldrons}
    
    # Get latest data point for each cauldron
    latest_data = {}
    for entry in data:
        cid = entry['cauldronId']
        timestamp = entry['timestamp']
        if cid not in latest_data or timestamp > latest_data[cid]['timestamp']:
            latest_data[cid] = entry
    
    for cid, latest in latest_data.items():
        if cid not in cauldron_map or cid not in fill_rates:
            continue
        
        cauldron = cauldron_map[cid]
        current_level = latest['level']
        max_volume = cauldron.get('max_volume', 0)
        fill_rate = fill_rates[cid]['median']  # liters per minute
        
        remaining_capacity = max_volume - current_level
        
        if fill_rate > 0 and remaining_capacity > 0:
            minutes_to_full = remaining_capacity / fill_rate
            hours_to_full = minutes_to_full / 60
            
            if hours_to_full <= hours_ahead:
                try:
                    current_time = datetime.fromisoformat(latest['timestamp'].replace('Z', '+00:00'))
                    overflow_time = current_time + timedelta(minutes=minutes_to_full)
                    
                    predictions.append({
                        "cauldronId": cid,
                        "cauldronName": cauldron.get('name', cid),
                        "currentLevel": round(current_level, 2),
                        "maxVolume": max_volume,
                        "fillRate": round(fill_rate, 3),
                        "hoursToFull": round(hours_to_full, 2),
                        "estimatedOverflowTime": overflow_time.isoformat(),
                        "urgency": "critical" if hours_to_full < 4 else "high" if hours_to_full < 12 else "medium"
                    })
                except:
                    continue
    
    # Sort by urgency
    predictions.sort(key=lambda x: x['hoursToFull'])
    
    return predictions

if __name__ == "__main__":
    app.run(debug=True)
