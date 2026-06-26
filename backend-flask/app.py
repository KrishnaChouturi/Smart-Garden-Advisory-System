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

@app.route('/test-weather', methods=['GET'])
def test_weather():
    try:
        lat, lon = "39.973251", "-86.203782"
        meteo_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,rain&temperature_unit=fahrenheit"

        response = requests.get(meteo_url)
        if response.status_code != 200:
            return jsonify({"status": "Weather API Error", "message": "Failed to fetch data"}), response.status_code

        current_data = response.json()['current']
        return jsonify({
            "status": "Success",
            "temperature_f": current_data['temperature_2m'],
            "humidity_percent": current_data['relative_humidity_2m'],
            "current_rain_mm": current_data['rain']
        }), 200
    except Exception as e:
        return jsonify({"status": "Server Error", "message": str(e)}), 500


@app.route('/check-watering-need/<int:plant_id>', methods=['GET'])
def check_watering_need(plant_id):
    try:
        plant_profile = supabase.table('plant_profiles').select('*').eq('id', plant_id).single().execute()
        if not plant_profile.data:
            return jsonify({"status": "Error", "message": "Plant profile not found"}), 404

        target_moisture = plant_profile.data.get('min_moisture_threshold', 40)

        recent_reading = supabase.table('soil_readings').select('*').eq('plant_id', plant_id).order('created_at', desc=True).limit(1).execute()
        if not recent_reading.data:
            return jsonify({"status": "Pending", "message": "No soil readings available yet for this plant."}), 200

        current_moisture = recent_reading.data[0].get('moisture_level')
        watering_needed = current_moisture < target_moisture
        recommendation = "None"

        if watering_needed:
            deficit = target_moisture - current_moisture
            recommendation = "High" if deficit > 20 else "Medium"

            supabase.table('watering_history').insert({
                "plant_id": plant_id,
                "amount_recommended": recommendation,
                "amount_applied": "Pending",
                "log_type": "System"
            }).execute()

        return jsonify({
            "status": "Success",
            "plant_id": plant_id,
            "current_moisture": f"{current_moisture}%",
            "target_threshold": f"{target_moisture}%",
            "watering_required": watering_needed,
            "recommended_amount": recommendation
        }), 200

    except Exception as e:
        return jsonify({"status": "Server Error", "message": str(e)}), 500


@app.route('/get-watering-history/<int:plant_id>', methods=['GET'])
def get_watering_history(plant_id):
    try:
        history_data = supabase.table('watering_history').select('*').eq('plant_id', plant_id).order('created_at', desc=True).execute()
        return jsonify({
            "status": "Success",
            "plant_id": plant_id,
            "total_records": len(history_data.data),
            "history": history_data.data
        }), 200
    except Exception as e:
        return jsonify({"status": "Server Error", "message": str(e)}), 500


@app.route('/manual-watering', methods=['POST'])
def manual_watering():
    try:
        data = request.get_json()
        plant_id = data.get('plant_id')
        amount_requested = data.get('amount')

        if not plant_id or not amount_requested:
            return jsonify({"status": "Error", "message": "Missing required fields."}), 400

        new_log = supabase.table('watering_history').insert({
            "plant_id": plant_id,
            "amount_recommended": amount_requested,
            "amount_applied": amount_requested,
            "log_type": "Manual"
        }).execute()

        return jsonify({
            "status": "Success",
            "message": f"Manual watering event successfully logged for plant {plant_id}.",
            "log_details": new_log.data[0]
        }), 201
    except Exception as e:
        return jsonify({"status": "Server Error", "message": str(e)}), 500


@app.route('/api/submit-reading', methods=['POST'])
def submit_reading():
    try:
        data = request.get_json()

        plant_id = data.get('plant_id')
        moisture_level = data.get('moisture_level')

        if plant_id is None or moisture_level is None:
            return jsonify({"status": "Error", "message": "Missing telemetry data."}), 400

        response = supabase.table('soil_readings').insert({
            "plant_id": plant_id,
            "moisture_level": int(moisture_level)
        }).execute()

        return jsonify({
            "status": "Success",
            "message": "Telemetry logged successfully.",
            "logged_data": response.data[0]
        }), 201

    except Exception as e:
        return jsonify({"status": "Server Error", "message": str(e)}), 500


@app.route('/add-override', methods=['POST'])
def add_override():
    data = request.json
    plant_id = data.get('plant_id')
    water_amount = data.get('water_amount')

    if not plant_id or not water_amount:
        return jsonify({"status": "error", "message": "Missing form data!"}), 400

    try:
        response = supabase.table("water_logs").insert({
            "plant_id": int(plant_id),
            "amount_ml": int(water_amount),
            "source": "manual_override"
        }).execute()
        return jsonify({"status": "success", "message": "Override logged successfully!"}), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)