# services/auth.py
import jwt
import datetime
from flask import request, jsonify, current_app
from functools import wraps

# Credentials hardcoded for demo; later can be loaded from env or DB
ADMIN_EMAIL = "admin@unsw.edu.au"
ADMIN_PASSWORD = "unswcse2025"

def create_admin_token():
    """
    Creates a JWT token for the admin user valid for 1 hour.
    """
    return jwt.encode(
        {"role": "admin", "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)},
        current_app.config["SECRET_KEY"],
        algorithm="HS256"
    )

def verify_admin_credentials(email, password):
    """
    Verifies the static admin credentials. Returns True if correct.
    """
    return email == ADMIN_EMAIL and password == ADMIN_PASSWORD

def require_admin(f):
    """
    Flask decorator to protect routes requiring admin JWT.
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({"error": "Missing token"}), 401
        try:
            token = token.split(" ")[1]
            decoded = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
            if decoded.get("role") != "admin":
                return jsonify({"error": "Admin access required"}), 403
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError as e:
            return jsonify({"error": f"Invalid token: {str(e)}"}), 401
        return f(*args, **kwargs)
    return wrapper
