import os
import uuid
import requests
import openai
from datetime import timedelta
from flask import Flask, request, jsonify, session
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

load_dotenv()

openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "your-secret-key")

app.config['SESSION_TYPE'] = 'filesystem'
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL", "sqlite:///app.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# enforce secure cookies for production
if os.getenv("FLASK_ENV") == "production":
    app.config['SESSION_COOKIE_SECURE'] = True
else:
    app.config['SESSION_COOKIE_SECURE'] = False

# should mean that sessions last 7 days
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

Session(app)
db = SQLAlchemy(app)


# defines teacher model
class Teacher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    voucher = db.Column(db.String(20), unique=True)
    persistent_token = db.Column(db.String(200), unique=True, nullable=True)

# create table if it doesn't exist (unsure if this still works with render)
with app.app_context():
    db.create_all()

# health check endpoint for monitoring.
@app.route("/health")
def health():
    return jsonify({"status": "ok"})

# endpoint to validate a voucher
@app.route("/validate_voucher", methods=["POST"])
def validate_voucher():
    data = request.get_json()
    if not data or "voucher" not in data:
        return jsonify({"error": "Voucher not provided"}), 400

    voucher = data["voucher"].strip()
    teacher = Teacher.query.filter_by(voucher=voucher).first()
    if not teacher:
        return jsonify({"error": "Invalid voucher"}), 401

    # save teacher info in session
    session["user_id"] = teacher.id
    session["user_info"] = {"name": teacher.name, "email": teacher.email}

    # generate a persistent token if one doesn’t exist
    if not teacher.persistent_token:
        teacher.persistent_token = str(uuid.uuid4())
        db.session.commit()

    return jsonify({
        "message": "Voucher validated",
        "user_info": session["user_info"],
        "persistent_token": teacher.persistent_token
    })

# endpoint for persistent login using a stored token
@app.route("/persistent_login", methods=["POST"])
def persistent_login():
    data = request.get_json()
    token = data.get("persistent_token")
    if not token:
        return jsonify({"error": "Token not provided"}), 400

    teacher = Teacher.query.filter_by(persistent_token=token).first()
    if not teacher:
        return jsonify({"error": "Invalid token"}), 401

    session["user_id"] = teacher.id
    session["user_info"] = {"name": teacher.name, "email": teacher.email}
    return jsonify({
        "message": "Persistent login successful",
        "user_info": session["user_info"]
    })

# logout endpoint: clear the session
@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out successfully"})

# endpoint to fetch current session user info
@app.route("/user_info")
def user_info():
    if "user_info" in session:
        return jsonify(session["user_info"])
    else:
        return jsonify({"error": "No user logged in"}), 404
    
# ---------- WINSTONAPI CONNECTION ---------

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

# --------- Chatbot Endpoint using OpenAI ---------
@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    if not data or "messages" not in data:
        return jsonify({"error": "Messages not provided"}), 400

    messages = data["messages"]
    model = data.get("model", "gpt-4")  # Default to a model if not provided

    print("messages:", messages)
    print("model:", model)
    print(openai)

    try:
        # Create a chat completion using OpenAI's API (adjust model as necessary)
        response = openai.chat.completions.create(
            model="gpt-4",  # Replace with your desired model
            messages=messages,  # Taking the latest message in the conversation
            max_tokens=150,  # You can adjust max_tokens as per your use case
            temperature=0.7  # Set the temperature (optional)
        )

        # Assuming the response contains the text from the completion
        return jsonify({"message": response.choices[0].message.content()}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(port=5000, debug=True)
