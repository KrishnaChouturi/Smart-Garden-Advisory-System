import os
import requests
from flask import Flask, jsonify, request
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


@app.route('/check-watering-need/<int:plant_id>', methods=['GET'])
def check_watering_need(plant_id):
    try:
        plant_profile = supabase.table('plant_profiles').select('*').eq('id', plant_id).single().execute()

        if not plant_profile.data:
            return jsonify({"status": "Error", "message": "Plant profile not found"}), 404

        target_moisture = plant_profile.data.get('min_moisture_threshold', 40)
        # To this:
        recent_reading = supabase.table('soil_readings').select('*').eq('plant_id', plant_id).order('created_at',desc=True).limit(1).execute()
        if not recent_reading.data:
            return jsonify({"status": "Pending", "message": "No soil readings available yet for this plant."}), 200

        current_moisture = recent_reading.data[0].get('moisture_level')

        watering_needed = current_moisture < target_moisture
        recommendation = "None"

        if watering_needed:
            deficit = target_moisture - current_moisture
            recommendation = "High" if deficit > 20 else "Medium"

            log_data = {
                "plant_id": plant_id,
                "amount_recommended": recommendation,
                "amount_applied": "Pending",
                "log_type": "System"
            }
            supabase.table('watering_history').insert(log_data).execute()

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

@app.route('/simulate-watering-log', methods=['GET'])
def simulate_watering_log():
    try:
        simulated_log = {
            "plant_id": 1,
            "amount_recommended": "Medium",
            "amount_applied": "Medium",
            "log_type": "System"
        }

        response = supabase.table('watering_history').insert(simulated_log).execute()
        
        return jsonify({
            "status": "Success",
            "message": "Simulated watering ledger entry written to cloud database!",
            "inserted_data": response.data
        }), 201

    except Exception as e:
        return jsonify({"status": "Server Error", "message": str(e)}), 500

@app.route('/get-watering-history/<int:plant_id>', methods=['GET'])
def get_watering_history(plant_id):
    try:
        history_data = supabase.table('watering_history') \
            .select('*') \
            .eq('plant_id', plant_id) \
            .order('created_at', desc=True) \
            .execute()

        if not history_data.data:
            return jsonify({
                "status": "Success",
                "plant_id": plant_id,
                "message": "No watering history records found for this plant.",
                "history": []
            }), 200

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
            return jsonify({
                "status": "Error",
                "message": "Missing required fields: 'plant_id' and 'amount' are required."
            }), 400

        new_log = supabase.table('watering_history').insert({
            "plant_id": plant_id,
            "amount_recommended": amount_requested,
            "amount_applied": "Pending",
            "log_type": "Manual"
        }).execute()

        return jsonify({
            "status": "Success",
            "message": f"Manual watering event successfully logged for plant {plant_id}.",
            "log_details": new_log.data[0]
        }), 201

    except Exception as e:
        return jsonify({"status": "Server Error", "message": str(e)}), 500

@app.route('/hardware/control-signal/<int:plant_id>', methods=['GET'])
def hardware_control_signal(plant_id):
    try:
        latest_action = supabase.table('watering_history') \
            .select('*') \
            .eq('plant_id', plant_id) \
            .order('created_at', desc=True) \
            .limit(1) \
            .execute()

        if not latest_action.data or latest_action.data[0].get('amount_applied') != 'Pending':
            return jsonify({
                "pump_signal": "OFF",
                "amount": "None",
                "message": "No pending watering commands found. Keep pump off."
            }), 200

        record_id = latest_action.data[0].get('id')
        dosage = latest_action.data[0].get('amount_recommended')

        supabase.table('watering_history') \
            .update({"amount_applied": dosage}) \
            .eq('id', record_id) \
            .execute()

        return jsonify({
            "pump_signal": "ON",
            "amount": dosage,
            "message": f"Valid pending task found! Activating pump for a {dosage} dose."
        }), 200

    except Exception as e:
        return jsonify({"pump_signal": "OFF", "error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)