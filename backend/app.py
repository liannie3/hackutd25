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
    """Fetch from cache or make API call - NOW WITH DETAILED LOGGING"""
    key = cache_key or endpoint
    now = datetime.now().timestamp()
    
    # Check cache
    if key in cache:
        data, timestamp = cache[key]
        if now - timestamp < CACHE_DURATION:
            print(f"✓ Returning cached data for {key}")
            return data
    
    # Fetch from API
    try:
        url = f"{BASE_URL}/{endpoint}"
        print(f"\n{'='*60}")
        print(f"FETCHING: {url}")
        if params:
            print(f"PARAMS: {params}")
        
        r = requests.get(url, params=params, timeout=10)
        
        print(f"STATUS CODE: {r.status_code}")
        print(f"CONTENT TYPE: {r.headers.get('Content-Type', 'NOT SET')}")
        print(f"CONTENT LENGTH: {len(r.text)} characters")
        print(f"FIRST 500 CHARS:\n{r.text[:500]}")
        print(f"{'='*60}\n")
        
        # Check if empty
        if not r.text or r.text.strip() == '':
            print(f"❌ ERROR: Empty response from {url}")
            if key in cache:
                print(f"⚠️  Returning stale cache")
                return cache[key][0]
            return None
        
        # Check status code
        if r.status_code != 200:
            print(f"❌ ERROR: Bad status code {r.status_code}")
            if key in cache:
                print(f"⚠️  Returning stale cache")
                return cache[key][0]
            return None
        
        # Try to parse JSON
        try:
            data = r.json()
            print(f"✓ Successfully parsed JSON")
            print(f"  Type: {type(data)}")
            if isinstance(data, list):
                print(f"  Length: {len(data)} items")
            elif isinstance(data, dict):
                print(f"  Keys: {list(data.keys())}")
            
            cache[key] = (data, now)
            return data
            
        except Exception as json_err:
            print(f"❌ JSON PARSE ERROR: {json_err}")
            print(f"  Raw content: {r.text[:200]}")
            if key in cache:
                print(f"⚠️  Returning stale cache")
                return cache[key][0]
            return None
            
    except requests.exceptions.Timeout as e:
        print(f"❌ TIMEOUT ERROR: {e}")
        if key in cache:
            return cache[key][0]
        return None
        
    except Exception as e:
        print(f"❌ UNEXPECTED ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        if key in cache:
            return cache[key][0]
        return None
@app.route("/api/debug/fill-rate-analysis", methods=['GET'])
def debug_fill_rate_analysis():
    """Analyze why fill rate estimation is failing for some cauldrons"""
    try:
        historical_data = get_cached_or_fetch("Data", "historical_data")
        converted_data = convert_historical_data(historical_data)
        
        # Group by cauldron
        cauldron_data = defaultdict(list)
        for entry in converted_data:
            cauldron_data[entry['cauldronId']].append(entry)
        
        analysis = {}
        
        for cid, entries in cauldron_data.items():
            entries.sort(key=lambda x: x['timestamp'])
            
            # Count increases, decreases, and flat
            increases = 0
            decreases = 0
            flat = 0
            total_intervals = 0
            positive_rates = []
            
            for i in range(len(entries) - 1):
                try:
                    curr = entries[i]
                    next_e = entries[i + 1]
                    
                    time_curr = datetime.fromisoformat(curr['timestamp'].replace('Z', '+00:00'))
                    time_next = datetime.fromisoformat(next_e['timestamp'].replace('Z', '+00:00'))
                    time_diff_min = (time_next - time_curr).total_seconds() / 60
                    
                    if time_diff_min <= 0 or time_diff_min > 5:
                        continue
                    
                    level_change = next_e['level'] - curr['level']
                    total_intervals += 1
                    
                    if level_change > 0:
                        increases += 1
                        rate = level_change / time_diff_min
                        if 0.01 < rate < 10:
                            positive_rates.append(rate)
                    elif level_change < 0:
                        decreases += 1
                    else:
                        flat += 1
                        
                except:
                    continue
            
            fill_rate = estimate_fill_rate(entries)
            
            analysis[cid] = {
                "total_data_points": len(entries),
                "total_intervals": total_intervals,
                "increases": increases,
                "decreases": decreases,
                "flat": flat,
                "positive_rates_found": len(positive_rates),
                "estimated_fill_rate": round(fill_rate, 3) if fill_rate > 0 else 0,
                "median_positive_rate": round(statistics.median(positive_rates), 3) if positive_rates else 0,
                "sample_positive_rates": [round(r, 3) for r in positive_rates[:10]],
                "will_be_processed": fill_rate > 0
            }
        
        # Summary
        cauldrons_with_rate = sum(1 for a in analysis.values() if a['estimated_fill_rate'] > 0)
        cauldrons_without_rate = len(analysis) - cauldrons_with_rate
        
        return jsonify({
            "total_cauldrons": len(analysis),
            "cauldrons_with_fill_rate": cauldrons_with_rate,
            "cauldrons_without_fill_rate": cauldrons_without_rate,
            "cauldron_analysis": analysis
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        })
@app.route("/api/debug/estimated-rates")
def debug_estimated_rates():
    """See what fill rates we're estimating"""
    historical_data = get_cached_or_fetch("Data", "historical_data")
    converted_data = convert_historical_data(historical_data)
    
    # Group by cauldron
    cauldron_data = defaultdict(list)
    for entry in converted_data:
        cauldron_data[entry['cauldronId']].append(entry)
    
    rates = {}
    for cid, entries in list(cauldron_data.items())[:5]:  # First 5
        entries.sort(key=lambda x: x['timestamp'])
        fill_rate = estimate_fill_rate(entries)
        rates[cid] = {
            "fill_rate": round(fill_rate, 3),
            "data_points": len(entries)
        }
    
    return jsonify(rates)
# Add this brand new test endpoint
@app.route("/api/debug/historical-data", methods=['GET'])
def debug_historical_data():
    """Debug the historical data to see why drains aren't being detected"""
    try:
        historical_data = get_cached_or_fetch("Data", "historical_data")
        
        if not historical_data:
            return jsonify({"error": "No historical data"})
        
        converted_data = convert_historical_data(historical_data)
        
        debug_info = {
            "raw_data_type": str(type(historical_data)),
            "raw_data_length": len(historical_data) if isinstance(historical_data, list) else "N/A",
            "raw_data_sample": historical_data[:2] if isinstance(historical_data, list) else str(historical_data)[:500],
            "converted_data_length": len(converted_data),
            "converted_data_sample": converted_data[:10],
            "cauldrons_in_data": list(set(d['cauldronId'] for d in converted_data[:100])),
        }
        
        # Check for level changes
        if converted_data:
            cauldron_data = {}
            for entry in converted_data[:1000]:  # First 1000 entries
                cid = entry['cauldronId']
                if cid not in cauldron_data:
                    cauldron_data[cid] = []
                cauldron_data[cid].append(entry)
            
            # Analyze one cauldron
            sample_cauldron = list(cauldron_data.keys())[0]
            entries = sorted(cauldron_data[sample_cauldron], key=lambda x: x['timestamp'])[:20]
            
            level_changes = []
            for i in range(1, len(entries)):
                change = entries[i]['level'] - entries[i-1]['level']
                level_changes.append({
                    "from": entries[i-1]['level'],
                    "to": entries[i]['level'],
                    "change": change,
                    "time_from": entries[i-1]['timestamp'],
                    "time_to": entries[i]['timestamp']
                })
            
            debug_info["sample_cauldron"] = sample_cauldron
            debug_info["sample_level_changes"] = level_changes
        
        return jsonify(debug_info)
    
    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        })

@app.route("/")
def home():
    return "Welcome to the HackUTD API proxy! Try /api/couriers, /api/market, or /api/tickets."
# Add this anywhere in your app.py file

@app.route("/api/analyze/discrepancy-detection", methods=["GET"])
def discrepancy_detection():
    """Perform full discrepancy detection between tickets and drain data."""
    try:
        historical_data = get_cached_or_fetch("Data", "historical_data")
        tickets_response = get_cached_or_fetch("Tickets", "tickets")
        cauldrons = get_cached_or_fetch("Information/cauldrons", "cauldrons")  # ADD THIS
        tickets = tickets_response.get("transport_tickets", [])
        data = convert_historical_data(historical_data)
        drain_events = detect_drain_events(data, cauldron_id=None, cauldron_info=cauldrons)
        drain_events = merge_nearby_drains(drain_events, max_gap_minutes=60)  # Add this line
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

# Update the analyze endpoints to fetch and pass cauldron info

@app.route("/api/analyze/drain-events", methods=['POST', 'GET'])
def analyze_drain_events():
    """
    Detect drain events from historical data
    Expects: { "cauldronId": "optional" }
    """
    try:
        force_refresh = request.args.get("forceRefresh", "false").lower() == "true"
        if force_refresh:
            cache.clear()
        if request.method == 'POST' and request.is_json:
            params = request.get_json()
        else:
            params = {}
        cauldron_id = params.get('cauldronId')
        
        # Fetch historical data AND cauldron info
        historical_data = get_cached_or_fetch("Data", "historical_data")
        cauldrons = get_cached_or_fetch("Information/cauldrons", "cauldrons")
        converted_data = convert_historical_data(historical_data)
        
        # Pass cauldron info to drain detection
        drain_events = detect_drain_events(converted_data, cauldron_id=None, cauldron_info=cauldrons)
        drain_events = merge_nearby_drains(drain_events, max_gap_minutes=60) 
        return jsonify({
            "success": True,
            "drainEvents": drain_events,
            "count": len(drain_events)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/analyze/discrepancies", methods=['POST', 'GET'])
def analyze_discrepancies():
    """
    Analyze discrepancies between tickets and actual drains
    Expects: { "ticketThreshold": 0.05 } (optional 5% tolerance)
    """
    try:
        force_refresh = request.args.get("forceRefresh", "false").lower() == "true"
        if force_refresh:
            cache.clear()
        
        # Handle parameters for both GET and POST
        threshold = 0.05  # default
        
        if request.method == 'POST':
            if request.is_json:
                params = request.get_json()
                threshold = params.get('ticketThreshold', 0.05)
        else:
            threshold = float(request.args.get('threshold', 0.05))
        
        # Fetch required data including cauldron info
        historical_data = get_cached_or_fetch("Data", "historical_data")
        tickets_response = get_cached_or_fetch("Tickets", "tickets")
        cauldrons = get_cached_or_fetch("Information/cauldrons", "cauldrons")
        
        if not historical_data or not tickets_response:
            return jsonify({
                "success": False,
                "error": "Failed to fetch data from API",
                "discrepancies": [],
                "summary": {"total": 0, "critical": 0, "high": 0, "medium": 0}
            })
        
        converted_data = convert_historical_data(historical_data)
        tickets = tickets_response.get('transport_tickets', [])
        
        # Detect drain events with cauldron info
        
        drain_events = detect_drain_events(converted_data, cauldron_id=None, cauldron_info=cauldrons)
        drain_events = merge_nearby_drains(drain_events, max_gap_minutes=60) 
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
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e),
            "discrepancies": [],
            "summary": {"total": 0, "critical": 0, "high": 0, "medium": 0}
        })

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
        
        # Run analyses with cauldron info
        
        drain_events = detect_drain_events(converted_data, cauldron_id=None, cauldron_info=cauldrons)
        drain_events = merge_nearby_drains(drain_events, max_gap_minutes=60) 
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

@app.route("/api/analyze/annotated-tickets", methods=['GET'])
def get_annotated_tickets():
    """Get tickets with discrepancy annotations"""
    try:
        tickets_response = get_cached_or_fetch("Tickets", "tickets")
        historical_data = get_cached_or_fetch("Data", "historical_data")
        cauldrons = get_cached_or_fetch("Information/cauldrons", "cauldrons")
        
        tickets = tickets_response.get('transport_tickets', [])
        converted_data = convert_historical_data(historical_data)
        
        drain_events = detect_drain_events(converted_data, cauldron_id=None, cauldron_info=cauldrons)
        drain_events = merge_nearby_drains(drain_events, max_gap_minutes=60) 
        discrepancies = find_discrepancies(drain_events, tickets)
        
        # Use the annotate function
        annotated = annotate_tickets_with_discrepancies(tickets, discrepancies)
        
        return jsonify({
            "success": True,
            "tickets": annotated,
            "summary": {
                "total": len(tickets),
                "suspicious": len([t for t in annotated if t.get('is_suspicious')]),
                "critical": len([t for t in annotated if t.get('suspicion_severity') == 'critical'])
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/debug/drain-detection-all-cauldrons", methods=['GET'])
def debug_drain_detection_all_cauldrons():
    """Debug drain detection across ALL cauldrons"""
    try:
        historical_data = get_cached_or_fetch("Data", "historical_data")
        cauldrons = get_cached_or_fetch("Information/cauldrons", "cauldrons")
        converted_data = convert_historical_data(historical_data)
        
        # Detect drains for ALL cauldrons
        
        drain_events = detect_drain_events(converted_data, cauldron_id=None, cauldron_info=cauldrons)
        drain_events = merge_nearby_drains(drain_events, max_gap_minutes=60) 
        # Group by cauldron
        drains_by_cauldron = defaultdict(list)
        for drain in drain_events:
            drains_by_cauldron[drain['cauldronId']].append(drain)
        
        # Get tickets
        tickets_response = get_cached_or_fetch("Tickets", "tickets")
        tickets = tickets_response.get('transport_tickets', []) if tickets_response else []
        
        tickets_by_cauldron = defaultdict(int)
        for ticket in tickets:
            tickets_by_cauldron[ticket.get('cauldron_id', '')] += 1
        
        summary = {
            "total_drains_detected": len(drain_events),
            "total_tickets": len(tickets),
            "drains_per_cauldron": {cid: len(drains) for cid, drains in drains_by_cauldron.items()},
            "tickets_per_cauldron": dict(tickets_by_cauldron),
            "sample_drains": drain_events[:20]  # First 20 drains
        }
        
        return jsonify(summary)
    
    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        })
    
@app.route("/api/test/simple")
def test_simple():
    """Simple test to see if basic API calls work"""
    results = {}
    
    # Test 1: Can we reach the API at all?
    try:
        r = requests.get(f"{BASE_URL}/Data", timeout=5)
        results['data_endpoint'] = {
            'status': r.status_code,
            'success': r.status_code == 200,
            'has_content': len(r.text) > 0,
            'preview': r.text[:200] if r.text else 'EMPTY'
        }
    except Exception as e:
        results['data_endpoint'] = {'error': str(e)}
    
    # Test 2: Can we get tickets?
    try:
        r = requests.get(f"{BASE_URL}/Tickets", timeout=5)
        results['tickets_endpoint'] = {
            'status': r.status_code,
            'success': r.status_code == 200,
            'has_content': len(r.text) > 0,
            'preview': r.text[:200] if r.text else 'EMPTY'
        }
    except Exception as e:
        results['tickets_endpoint'] = {'error': str(e)}
    
    return jsonify(results)

@app.route("/api/debug/matching", methods=['GET'])
def debug_matching():
    """Debug ticket-to-drain matching to see what's going wrong"""
    try:
        historical_data = get_cached_or_fetch("Data", "historical_data")
        tickets_response = get_cached_or_fetch("Tickets", "tickets")
        cauldrons = get_cached_or_fetch("Information/cauldrons", "cauldrons")
        
        if not historical_data or not tickets_response:
            return jsonify({"error": "Failed to fetch data"})
        
        tickets = tickets_response.get('transport_tickets', [])
        converted_data = convert_historical_data(historical_data)
        
        drain_events = detect_drain_events(converted_data, cauldron_id=None, cauldron_info=cauldrons)
        drain_events = merge_nearby_drains(drain_events, max_gap_minutes=60) 
        # Get a sample day to debug
        sample_ticket = tickets[0] if tickets else None
        
        debug_info = {
            "total_tickets": len(tickets),
            "total_drain_events": len(drain_events),
            "sample_ticket": sample_ticket,
            "sample_drain": drain_events[0] if drain_events else None,
            "tickets_by_date": {},
            "drains_by_date": {}
        }
        
        # Group tickets by date
        for t in tickets[:10]:
            date = t.get('date', '').split('T')[0]
            cauldron = t.get('cauldron_id', '')
            key = f"{date}_{cauldron}"
            if key not in debug_info["tickets_by_date"]:
                debug_info["tickets_by_date"][key] = []
            debug_info["tickets_by_date"][key].append({
                "amount": t.get('amount_collected'),
                "courier": t.get('courier_id'),
                "date": t.get('date')
            })
        
        # Group drains by date
        for d in drain_events[:10]:
            date = d['startTime'].split('T')[0]
            cauldron = d['cauldronId']
            key = f"{date}_{cauldron}"
            if key not in debug_info["drains_by_date"]:
                debug_info["drains_by_date"][key] = []
            debug_info["drains_by_date"][key].append({
                "volume": d['totalPotionRemoved'],
                "startTime": d['startTime'],
                "duration": d['duration']
            })
        
        return jsonify(debug_info)
    
    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        })
    
@app.route("/debug/routes")
def list_routes():
    """List all registered routes"""
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append({
            "endpoint": rule.endpoint,
            "methods": list(rule.methods),
            "path": str(rule.rule)
        })
    return jsonify(sorted(routes, key=lambda x: x['path']))

@app.route("/api/<path:endpoint>")
def proxy(endpoint):
    """
    Proxy all GET requests to the external API
    This MUST come AFTER all specific /api/* routes
    """
    try:
        # Don't proxy analyze, test, or debug routes - they should have been handled above
        if endpoint.startswith('analyze/') or endpoint.startswith('test/') or endpoint.startswith('debug/'):
            return jsonify({
                "error": f"Endpoint /{endpoint} not found",
                "hint": "This endpoint may not be implemented yet"
            }), 404
        
        params = request.args.to_dict()
        cache_key = f"{endpoint}_{str(params)}" if params else endpoint
        data = get_cached_or_fetch(endpoint, cache_key, params if params else None)
        
        if data is None:
            return jsonify({"error": "Failed to fetch data from external API"}), 500
            
        return jsonify(data)
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


def detect_drain_events(data, cauldron_id=None, cauldron_info=None):
    """
    Improved drain detection with stricter criteria to reduce false positives.
    Key changes:
    1. Larger minimum volume threshold (30L instead of 10L)
    2. Stricter rate threshold (30% of fill rate instead of 50%)
    3. Longer minimum duration (20 min instead of 10 min)
    4. Better handling of brief fluctuations
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
        entries.sort(key=lambda x: x.get('timestamp', ''))
        
        if len(entries) < 10:
            continue
        
        # Estimate fill rate
        fill_rate = estimate_fill_rate(entries)
        if fill_rate <= 0:
            fill_rate = 0.1
        
        # STRICTER THRESHOLD: Only detect when rate is < 30% of fill rate
        # This catches real drains but ignores minor fluctuations
        DRAIN_THRESHOLD = 0.3  # Was 0.5, now 0.3
        
        i = 0
        while i < len(entries) - 30:
            start_idx = i
            start_entry = entries[start_idx]
            
            try:
                start_time = datetime.fromisoformat(start_entry['timestamp'].replace('Z', '+00:00'))
                
                # Find entry ~30 minutes later
                target_idx = None
                for j in range(i + 20, min(i + 50, len(entries))):
                    check_time = datetime.fromisoformat(entries[j]['timestamp'].replace('Z', '+00:00'))
                    time_diff = (check_time - start_time).total_seconds() / 60
                    if 25 <= time_diff <= 35:
                        target_idx = j
                        break
                
                if target_idx is None:
                    i += 1
                    continue
                
                end_entry = entries[target_idx]
                end_time = datetime.fromisoformat(end_entry['timestamp'].replace('Z', '+00:00'))
                window_duration = (end_time - start_time).total_seconds() / 60
                
                expected_increase = fill_rate * window_duration
                actual_change = end_entry['level'] - start_entry['level']
                net_rate = actual_change / window_duration
                
                # STRICTER: Only trigger on significant deviations
                if net_rate < fill_rate * DRAIN_THRESHOLD:
                    drain_start_idx = i
                    drain_end_idx = target_idx
                    
                    # Extend drain period
                    k = target_idx
                    while k < len(entries) - 30:
                        check_start = entries[k]
                        check_start_time = datetime.fromisoformat(check_start['timestamp'].replace('Z', '+00:00'))
                        
                        next_idx = None
                        for m in range(k + 20, min(k + 50, len(entries))):
                            check_time = datetime.fromisoformat(entries[m]['timestamp'].replace('Z', '+00:00'))
                            time_diff = (check_time - check_start_time).total_seconds() / 60
                            if 25 <= time_diff <= 35:
                                next_idx = m
                                break
                        
                        if next_idx is None:
                            break
                        
                        check_end = entries[next_idx]
                        check_end_time = datetime.fromisoformat(check_end['timestamp'].replace('Z', '+00:00'))
                        check_duration = (check_end_time - check_start_time).total_seconds() / 60
                        check_change = check_end['level'] - check_start['level']
                        check_rate = check_change / check_duration
                        
                        if check_rate < fill_rate * DRAIN_THRESHOLD:
                            drain_end_idx = next_idx
                            k = next_idx
                        else:
                            break
                    
                    # Calculate final statistics
                    final_start = entries[drain_start_idx]
                    final_end = entries[drain_end_idx]
                    
                    final_start_time = datetime.fromisoformat(final_start['timestamp'].replace('Z', '+00:00'))
                    final_end_time = datetime.fromisoformat(final_end['timestamp'].replace('Z', '+00:00'))
                    total_duration = (final_end_time - final_start_time).total_seconds() / 60
                    
                    level_drop = final_start['level'] - final_end['level']
                    potion_generated = fill_rate * total_duration
                    total_removed = level_drop + potion_generated
                    
                    # STRICTER THRESHOLDS:
                    # - Minimum 20 minutes (was 10)
                    # - Minimum 30L removed (was 10L)
                    # This filters out noise and small fluctuations
                    MIN_DURATION = 20  # minutes
                    MIN_VOLUME = 30    # liters
                    
                    if total_duration >= MIN_DURATION and total_removed >= MIN_VOLUME:
                        drain_events.append({
                            "cauldronId": cid,
                            "startTime": final_start['timestamp'],
                            "endTime": final_end['timestamp'],
                            "duration": round(total_duration, 2),
                            "levelDrop": round(level_drop, 2),
                            "potionGeneratedDuringDrain": round(potion_generated, 2),
                            "totalPotionRemoved": round(total_removed, 2),
                            "estimatedFillRate": round(fill_rate, 3),
                            "estimatedDrainRate": round(total_removed / total_duration, 3) if total_duration > 0 else 0,
                            "startLevel": round(final_start['level'], 2),
                            "endLevel": round(final_end['level'], 2)
                        })
                        
                        i = drain_end_idx + 1
                    else:
                        i += 1
                else:
                    i += 1
                    
            except Exception as e:
                i += 1
                continue
    
    return drain_events


# Additional helper: Merge nearby drains that might be the same collection event
def merge_nearby_drains(drain_events, max_gap_minutes=60):
    """
    Merge drain events that are close together in time.
    Sometimes a single collection appears as 2-3 small drains.
    """
    if not drain_events:
        return []
    
    # Group by cauldron
    by_cauldron = defaultdict(list)
    for drain in drain_events:
        by_cauldron[drain['cauldronId']].append(drain)
    
    merged = []
    
    for cid, drains in by_cauldron.items():
        drains.sort(key=lambda d: d['startTime'])
        
        if not drains:
            continue
        
        current_merge = drains[0].copy()
        
        for i in range(1, len(drains)):
            curr_end = datetime.fromisoformat(current_merge['endTime'].replace('Z', '+00:00'))
            next_start = datetime.fromisoformat(drains[i]['startTime'].replace('Z', '+00:00'))
            gap = (next_start - curr_end).total_seconds() / 60
            
            # If drains are within max_gap_minutes, merge them
            if gap <= max_gap_minutes:
                # Extend the current merge
                current_merge['endTime'] = drains[i]['endTime']
                current_merge['endLevel'] = drains[i]['endLevel']
                current_merge['totalPotionRemoved'] += drains[i]['totalPotionRemoved']
                current_merge['potionGeneratedDuringDrain'] += drains[i]['potionGeneratedDuringDrain']
                current_merge['levelDrop'] = current_merge['startLevel'] - current_merge['endLevel']
                
                # Recalculate duration
                new_start = datetime.fromisoformat(current_merge['startTime'].replace('Z', '+00:00'))
                new_end = datetime.fromisoformat(current_merge['endTime'].replace('Z', '+00:00'))
                current_merge['duration'] = (new_end - new_start).total_seconds() / 60
                current_merge['estimatedDrainRate'] = (
                    current_merge['totalPotionRemoved'] / current_merge['duration'] 
                    if current_merge['duration'] > 0 else 0
                )
            else:
                # Gap too large, save current and start new
                merged.append(current_merge)
                current_merge = drains[i].copy()
        
        # Add the last one
        merged.append(current_merge)
    
    return merged

def estimate_fill_rate(entries):
    """
    Estimate fill rate from periods of consistent level increase.
    Returns median fill rate in L/min.
    """
    fill_rates = []
    
    for i in range(len(entries) - 1):
        try:
            curr = entries[i]
            next_e = entries[i + 1]
            
            time_curr = datetime.fromisoformat(curr['timestamp'].replace('Z', '+00:00'))
            time_next = datetime.fromisoformat(next_e['timestamp'].replace('Z', '+00:00'))
            time_diff_min = (time_next - time_curr).total_seconds() / 60
            
            if time_diff_min <= 0 or time_diff_min > 5:
                continue
            
            level_change = next_e['level'] - curr['level']
            
            # Only consider increases (filling periods)
            if level_change > 0:
                rate = level_change / time_diff_min
                # Filter out unrealistic rates
                if 0.01 < rate < 10:
                    fill_rates.append(rate)
                    
        except:
            continue
    
    if not fill_rates:
        return 0
    
    return statistics.median(fill_rates)


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

def annotate_tickets_with_discrepancies(tickets, discrepancies):
    """
    Annotate individual tickets with their specific discrepancy information.
    Now works with granular ticket-to-drain matching.
    """
    # Create a lookup for tickets by ID (or by unique key if no ID)
    ticket_lookup = {}
    for t in tickets:
        # Create unique key for ticket
        ticket_id = t.get('ticket_id') or t.get('id')
        if not ticket_id:
            # Create synthetic ID from ticket properties
            date = t.get('date', '')
            cauldron = t.get('cauldron_id', '')
            amount = t.get('amount_collected', 0)
            courier = t.get('courier_id', '')
            ticket_id = f"{date}_{cauldron}_{amount}_{courier}"
        
        ticket_lookup[ticket_id] = t
    
    # Map discrepancies to tickets
    ticket_discrepancies = {}
    
    for disc in discrepancies:
        if 'ticket' in disc:
            # Get the ticket from the discrepancy
            ticket_data = disc['ticket']
            ticket_id = ticket_data.get('ticket_id') or ticket_data.get('id')
            
            if not ticket_id:
                # Create same synthetic ID
                date = ticket_data.get('date', '')
                cauldron = ticket_data.get('cauldron_id', '')
                amount = ticket_data.get('amount_collected', 0)
                courier = ticket_data.get('courier_id', '')
                ticket_id = f"{date}_{cauldron}_{amount}_{courier}"
            
            if ticket_id not in ticket_discrepancies:
                ticket_discrepancies[ticket_id] = []
            ticket_discrepancies[ticket_id].append(disc)
    
    # Annotate each ticket
    annotated = []
    
    for ticket in tickets:
        t_copy = dict(ticket)
        
        # Get ticket ID
        ticket_id = t_copy.get('ticket_id') or t_copy.get('id')
        if not ticket_id:
            date = t_copy.get('date', '')
            cauldron = t_copy.get('cauldron_id', '')
            amount = t_copy.get('amount_collected', 0)
            courier = t_copy.get('courier_id', '')
            ticket_id = f"{date}_{cauldron}_{amount}_{courier}"
        
        # Check if this ticket has any discrepancies
        ticket_discs = ticket_discrepancies.get(ticket_id, [])
        
        if not ticket_discs:
            # Clean ticket
            t_copy['is_suspicious'] = False
            t_copy['suspicion_type'] = None
            t_copy['suspicion_severity'] = None
            t_copy['suspicion_message'] = None
            t_copy['linked_drain_events'] = []
        else:
            # Has discrepancies
            t_copy['is_suspicious'] = True
            
            # Combine info from all discrepancies for this ticket
            types = [d['type'] for d in ticket_discs]
            severities = [d['severity'] for d in ticket_discs]
            messages = [d['message'] for d in ticket_discs]
            drains = []
            
            for d in ticket_discs:
                if 'drainEvent' in d:
                    drains.append(d['drainEvent'])
            
            # Use highest severity
            severity_order = {'critical': 3, 'high': 2, 'medium': 1, 'low': 0}
            max_severity = max(severities, key=lambda s: severity_order.get(s, 0))
            
            t_copy['suspicion_type'] = types[0] if len(types) == 1 else "MULTIPLE_ISSUES"
            t_copy['suspicion_severity'] = max_severity
            t_copy['suspicion_message'] = " | ".join(messages)
            t_copy['linked_drain_events'] = drains
            t_copy['discrepancy_details'] = ticket_discs  # Include full details
        
        annotated.append(t_copy)
    
    return annotated

def find_discrepancies(drain_events, tickets, threshold=0.05):
    """
    Match individual tickets to specific drain events and identify discrepancies.
    Uses a greedy matching algorithm to pair tickets with drains on the same day.
    threshold: acceptable percentage difference (default 5%)
    """
    discrepancies = []
    
    # Group drains and tickets by date and cauldron
    drains_by_key = {}
    tickets_by_key = {}
    
    for drain in drain_events:
        date = drain['startTime'].split('T')[0]
        cauldron = drain['cauldronId']
        key = f"{date}_{cauldron}"
        if key not in drains_by_key:
            drains_by_key[key] = []
        drains_by_key[key].append(drain)
    
    for ticket in tickets:
        date = ticket.get('date', '').split('T')[0]
        cauldron = ticket.get('cauldron_id', '')
        key = f"{date}_{cauldron}"
        if key not in tickets_by_key:
            tickets_by_key[key] = []
        tickets_by_key[key].append(ticket)
    
    # Process each day/cauldron combination
    all_keys = set(drains_by_key.keys()) | set(tickets_by_key.keys())
    
    for key in all_keys:
        date, cauldron_id = key.split('_', 1)
        drains = drains_by_key.get(key, [])
        tickets_list = tickets_by_key.get(key, [])
        
        # Sort by volume for greedy matching
        drains = sorted(drains, key=lambda d: d['totalPotionRemoved'], reverse=True)
        tickets_list = sorted(tickets_list, key=lambda t: t.get('amount_collected', 0), reverse=True)
        
        # Track which drains and tickets have been matched
        matched_drains = set()
        matched_tickets = set()
        matches = []  # (ticket_idx, drain_idx, difference)
        
        # Greedy matching: pair largest ticket with closest drain
        for t_idx, ticket in enumerate(tickets_list):
            ticket_vol = ticket.get('amount_collected', 0)
            best_match = None
            best_diff = float('inf')
            
            for d_idx, drain in enumerate(drains):
                if d_idx in matched_drains:
                    continue
                
                drain_vol = drain['totalPotionRemoved']
                diff = abs(ticket_vol - drain_vol)
                tolerance = drain_vol * 0.10 
                
                # Consider this a valid match if within tolerance
                if diff <= tolerance and diff < best_diff:
                    best_match = d_idx
                    best_diff = diff
            
            if best_match is not None:
                matched_drains.add(best_match)
                matched_tickets.add(t_idx)
                matches.append((t_idx, best_match, best_diff))
        
        # Now identify discrepancies
        
        # 1. Unmatched tickets (PHANTOM TICKETS)
        for t_idx, ticket in enumerate(tickets_list):
            if t_idx not in matched_tickets:
                ticket_vol = ticket.get('amount_collected', 0)
                
                # Check if there are ANY unmatched drains
                unmatched_drains = [d for d_idx, d in enumerate(drains) if d_idx not in matched_drains]
                
                if unmatched_drains:
                    # There ARE drains, but none matched this ticket closely enough
                    closest_drain = min(unmatched_drains, key=lambda d: abs(d['totalPotionRemoved'] - ticket_vol))
                    difference = abs(closest_drain['totalPotionRemoved'] - ticket_vol)
                    percent_diff = (difference / closest_drain['totalPotionRemoved'] * 100) if closest_drain['totalPotionRemoved'] > 0 else 999
                    
                    severity = "critical" if percent_diff > 50 else "high" if percent_diff > 20 else "medium"
                    
                    discrepancies.append({
                        "type": "SIGNIFICANT_VOLUME_MISMATCH",
                        "severity": severity,
                        "cauldronId": cauldron_id,
                        "date": date,
                        "ticket": ticket,
                        "ticketVolume": round(ticket_vol, 2),
                        "closestDrainVolume": round(closest_drain['totalPotionRemoved'], 2),
                        "difference": round(difference, 2),
                        "percentDifference": round(percent_diff, 2),
                        "drainEvent": closest_drain,
                        "message": f"Ticket shows {round(ticket_vol, 2)}L but closest drain was {round(closest_drain['totalPotionRemoved'], 2)}L ({round(percent_diff, 1)}% difference)"
                    })
                else:
                    # No drain event at all for this ticket
                    discrepancies.append({
                        "type": "PHANTOM_TICKET",
                        "severity": "critical",
                        "cauldronId": cauldron_id,
                        "date": date,
                        "ticket": ticket,
                        "ticketVolume": round(ticket_vol, 2),
                        "message": f"Ticket claims {round(ticket_vol, 2)}L collected but no drain event detected"
                    })
        
        # 2. Unmatched drains (UNLOGGED DRAINS)
        for d_idx, drain in enumerate(drains):
            if d_idx not in matched_drains:
                drain_vol = drain['totalPotionRemoved']
                
                discrepancies.append({
                    "type": "UNLOGGED_DRAIN",
                    "severity": "critical",
                    "cauldronId": cauldron_id,
                    "date": date,
                    "drainEvent": drain,
                    "drainVolume": round(drain_vol, 2),
                    "message": f"Drain of {round(drain_vol, 2)}L detected but no matching ticket found"
                })
        
        # 3. Matched but with concerning differences
        for t_idx, d_idx, diff in matches:
            ticket = tickets_list[t_idx]
            drain = drains[d_idx]
            
            ticket_vol = ticket.get('amount_collected', 0)
            drain_vol = drain['totalPotionRemoved']
            
            # Even though they matched, flag if difference is non-trivial
            if diff > 1.0:  # More than 1L difference
                percent_diff = (diff / drain_vol * 100) if drain_vol > 0 else 0
                
                # Only flag if it's a meaningful percentage
                if percent_diff > 2:  # More than 2% off
                    severity = "medium" if percent_diff < 5 else "high"
                    
                    discrepancies.append({
                        "type": "MINOR_VOLUME_MISMATCH",
                        "severity": severity,
                        "cauldronId": cauldron_id,
                        "date": date,
                        "ticket": ticket,
                        "drainEvent": drain,
                        "ticketVolume": round(ticket_vol, 2),
                        "drainVolume": round(drain_vol, 2),
                        "difference": round(diff, 2),
                        "percentDifference": round(percent_diff, 2),
                        "message": f"Ticket and drain matched but differ by {round(diff, 2)}L ({round(percent_diff, 1)}%)"
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
