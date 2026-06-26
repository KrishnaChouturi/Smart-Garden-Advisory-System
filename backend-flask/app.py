import os
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

app = Flask(__name__)
CORS(app)

url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(url, key)

DEFAULT_PLANT_ID = 1
@app.route('/test-weather', methods=['GET'])
def test_weather():
    try:
        lat, lon = "39.973251", "-86.203782"
        meteo_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,rain&daily=rain_sum&temperature_unit=fahrenheit&timezone=auto"

        response = requests.get(meteo_url)
        if response.status_code != 200:
            return jsonify({"status": "Weather API Error", "message": "Failed to fetch data"}), response.status_code

        res_data = response.json()
        current_data = res_data['current']

        upcoming_rain_mm = res_data['daily']['rain_sum'][0]
        will_rain_today = upcoming_rain_mm > 0.5

        return jsonify({
            "status": "Success",
            "temperature_f": current_data['temperature_2m'],
            "humidity_percent": current_data['relative_humidity_2m'],
            "current_rain_mm": current_data['rain'],
            "upcoming_rain": will_rain_today,
            "upcoming_rain_val": upcoming_rain_mm
        }), 200
    except Exception as e:
        return jsonify({"status": "Server Error", "message": str(e)}), 500


@app.route('/compute-recommendation', methods=['POST'])
def compute_recommendation():
    try:
        data = request.get_json() or {}
        target_threshold = int(data.get('target_threshold', 40))

        recent_reading = supabase.table('soil_readings').select('*').eq('plant_id', DEFAULT_PLANT_ID).order(
            'created_at', desc=True).limit(1).execute()

        if not recent_reading.data:
            return jsonify({"status": "Error", "message": "No soil telemetry data available to calculate."}), 400

        current_moisture = recent_reading.data[0].get('moisture_level')

        weather_res = requests.get(
            "https://api.open-meteo.com/v1/forecast?latitude=39.973251&longitude=-86.203782&current=temperature_2m&daily=rain_sum&temperature_unit=fahrenheit&timezone=auto").json()
        temp = weather_res['current']['temperature_2m']
        upcoming_rain = weather_res['daily']['rain_sum'][0] > 0.5

        recommendation = "None"
        if current_moisture < target_threshold:
            deficit = target_threshold - current_moisture

            if upcoming_rain:
                recommendation = "None"
            elif deficit > 25 or temp > 85:
                recommendation = "Large"
            elif deficit > 15:
                recommendation = "Medium"
            else:
                recommendation = "Small"
        else:
            if current_moisture - target_threshold < 5 and temp > 90 and not upcoming_rain:
                recommendation = "Small"

        supabase.table('watering_history').insert({
            "plant_id": DEFAULT_PLANT_ID,
            "amount_recommended": recommendation,
            "amount_applied": "Pending",
            "log_type": "System"
        }).execute()

        return jsonify({
            "status": "Success",
            "current_moisture": current_moisture,
            "recommendation": recommendation
        }), 200
    except Exception as e:
        return jsonify({"status": "Server Error", "message": str(e)}), 500



@app.route('/manual-watering', methods=['POST'])
def manual_watering():
    try:
        data = request.get_json() or {}
        amount_requested = data.get('amount')

        if not amount_requested:
            return jsonify({"status": "Error", "message": "Missing required fields."}), 400

        new_log = supabase.table('watering_history').insert({
            "plant_id": DEFAULT_PLANT_ID,
            "amount_recommended": amount_requested,
            "amount_applied": amount_requested,
            "log_type": "User Override"
        }).execute()

        return jsonify({
            "status": "Success",
            "message": f"Manual override set to {amount_requested}.",
            "log_details": new_log.data[0] if (hasattr(new_log, 'data') and new_log.data) else {}
        }), 201
    except Exception as e:
        return jsonify({"status": "Server Error", "message": str(e)}), 500


@app.route('/api/submit-reading', methods=['POST'])
def submit_reading():
    try:
        data = request.get_json() or {}
        moisture_level = data.get('moisture_level')

        if moisture_level is None:
            return jsonify({"status": "Error", "message": "Missing telemetry data."}), 400

        response = supabase.table('soil_readings').insert({
            "plant_id": DEFAULT_PLANT_ID,
            "moisture_level": int(moisture_level)
        }).execute()

        return jsonify({
            "status": "Success",
            "message": "Telemetry logged successfully.",
            "logged_data": response.data[0] if (hasattr(response, 'data') and response.data) else {}
        }), 201
    except Exception as e:
        return jsonify({"status": "Server Error", "message": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)