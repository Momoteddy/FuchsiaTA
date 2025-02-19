import os
import uuid
from datetime import timedelta
from flask import Flask, request, jsonify, session
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "your-secret-key")

# Environment-based configuration
# Use filesystem sessions and SQLite for demo purposes.
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URI", "sqlite:///app.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Enforce secure cookies in production.
if os.getenv("FLASK_ENV") == "production":
    app.config['SESSION_COOKIE_SECURE'] = True
else:
    app.config['SESSION_COOKIE_SECURE'] = False

# Set session lifetime (e.g., 7 days)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

Session(app)
db = SQLAlchemy(app)

# Optional: Add rate limiting if desired.
# from flask_limiter import Limiter
# from flask_limiter.util import get_remote_address
# limiter = Limiter(app, key_func=get_remote_address)

# Define a Teacher model.
class Teacher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    voucher = db.Column(db.String(20), unique=True)
    persistent_token = db.Column(db.String(200), unique=True, nullable=True)

# Create tables if they do not exist.
with app.app_context():
    db.create_all()

# Health check endpoint for monitoring.
@app.route("/health")
def health():
    return jsonify({"status": "ok"})

# Endpoint to validate a voucher.
@app.route("/validate_voucher", methods=["POST"])
def validate_voucher():
    data = request.get_json()
    if not data or "voucher" not in data:
        return jsonify({"error": "Voucher not provided"}), 400

    voucher = data["voucher"].strip()
    teacher = Teacher.query.filter_by(voucher=voucher).first()
    if not teacher:
        return jsonify({"error": "Invalid voucher"}), 401

    # Save teacher info in session.
    session["user_id"] = teacher.id
    session["user_info"] = {"name": teacher.name, "email": teacher.email}

    # Generate a persistent token if one doesn’t exist.
    if not teacher.persistent_token:
        teacher.persistent_token = str(uuid.uuid4())
        db.session.commit()

    return jsonify({
        "message": "Voucher validated",
        "user_info": session["user_info"],
        "persistent_token": teacher.persistent_token
    })

# Endpoint for persistent login using a stored token.
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

# Logout endpoint: clear the session.
@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out successfully"})

# Endpoint to fetch current session user info.
@app.route("/user_info")
def user_info():
    if "user_info" in session:
        return jsonify(session["user_info"])
    else:
        return jsonify({"error": "No user logged in"}), 404

if __name__ == "__main__":
    # For production, ensure that debug mode is off and consider using a production WSGI server.
    app.run(port=5000, debug=True)