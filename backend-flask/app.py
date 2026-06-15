import os
import requests
from flask import Flask, jsonify
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

app = Flask(__name__)

url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(url, key)


@app.route('/test-db', methods=['GET'])
def test_db_connection():
    try:
        response = supabase.table('plant_profiles').select('*').execute()
        return jsonify({"status": "Success", "data": response.data}), 200
    except Exception as e:
        return jsonify({"status": "Error", "message": str(e)}), 500


@app.route('/test-weather', methods=['GET'])
def test_weather():
    try:
        lat = "39.973251"
        lon = "-86.203782"
        meteo_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,rain&temperature_unit=fahrenheit"

        response = requests.get(meteo_url)
        data = response.json()

        if response.status_code != 200:
            return jsonify({"status": "Weather API Error",
                            "message": "Failed to fetch data from Open-Meteo"}), response.status_code

        current_data = data['current']
        current_temp = current_data['temperature_2m']
        humidity = current_data['relative_humidity_2m']
        rain_mm = current_data['rain']

        return jsonify({
            "status": "Success",
            "provider": "Open-Meteo",
            "location_coordinates": f"Lat: {lat}, Lon: {lon}",
            "temperature_f": current_temp,
            "humidity_percent": humidity,
            "current_rain_mm": rain_mm
        }), 200

    except Exception as e:
        return jsonify({"status": "Server Error", "message": str(e)}), 500


# 📝 NEW: Simulate log entry into the Watering History Table
@app.route('/simulate-watering-log', methods=['GET'])
def simulate_watering_log():
    try:
        # Mocking a data payload that either an ESP32 or a Frontend click would submit
        simulated_log = {
            "plant_id": 1,  # Assuming a plant with ID 1 exists in your database
            "amount_recommended": "Medium",
            "amount_applied": "Medium",
            "log_type": "System"
        }
        
        # Inject the mock data payload directly into your Supabase cloud table
        response = supabase.table('watering_history').insert(simulated_log).execute()
        
        return jsonify({
            "status": "Success",
            "message": "Simulated watering ledger entry written to cloud database!",
            "inserted_data": response.data
        }), 201

    except Exception as e:
        return jsonify({"status": "Server Error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)