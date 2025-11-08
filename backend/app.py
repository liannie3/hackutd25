from flask import Flask, jsonify
import requests

app = Flask(__name__)
BASE = "https://hackutd2025.eog.systems"

@app.route("/api/couriers")
def couriers():
    r = requests.get(f"{BASE}/api/Information/couriers", headers={"accept": "application/json"})
    return jsonify(r.json())

@app.route("/api/cauldrons")
def cauldrons():
    r = requests.get(f"{BASE}/api/Information/cauldrons", headers={"accept": "application/json"})
    return jsonify(r.json())

if __name__ == "__main__":
    app.run(debug=True)
