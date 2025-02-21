import os
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Retrieve your WinstonAI API key from the environment.
WINSTONAI_API_KEY = os.getenv("WINSTONAI_API_KEY")

# Endpoint for AI content detection.
@app.route("/detect-ai", methods=["POST"])
def detect_ai():
    data = request.get_json()
    text = data.get("text", "")
    
    # Prepare payload. You can extend this with "file", "website", etc. as needed.
    payload = {
        "text": text,
        "file": data.get("file", ""),         # Optional
        "website": data.get("website", ""),   # Optional
        "version": data.get("version", "v2"),   # Default or provided version
        "sentences": data.get("sentences", True),
        "language": data.get("language", "en")
    }
    
    headers = {
        "Authorization": f"Bearer {WINSTONAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    response = requests.post("https://api.gowinston.ai/v2/ai-content-detection",
                             json=payload, headers=headers)
    
    # Optionally process response here before returning.
    return jsonify(response.json()), response.status_code

# Endpoint for plagiarism detection.
@app.route("/plagiarism", methods=["POST"])
def detect_plagiarism():
    data = request.get_json()
    text = data.get("text", "")
    
    payload = {
        "text": text,
        "file": data.get("file", ""),         # Optional
        "website": data.get("website", ""),   # Optional
        "excluded_sources": data.get("excluded_sources", []),
        "language": data.get("language", "en"),
        "country": data.get("country", "us")
    }
    
    headers = {
        "Authorization": f"Bearer {WINSTONAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    response = requests.post("https://api.gowinston.ai/v2/plagiarism",
                             json=payload, headers=headers)
    
    return jsonify(response.json()), response.status_code

if __name__ == "__main__":
    # Run the backend on port 5000 (adjust as needed)
    app.run(port=5000, debug=True)
