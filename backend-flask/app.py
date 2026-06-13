import os
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
        return jsonify({
            "status": "Success",
            "message": "Connected to cloud database!",
            "data": response.data
        }), 200

    except Exception as e:
        return jsonify({
            "status": "Error",
            "message": str(e)
        }), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)