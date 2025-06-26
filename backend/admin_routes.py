from flask import Blueprint, request, jsonify, current_app
import jwt
import datetime
from functools import wraps

admin_bp = Blueprint('admin_bp', __name__)

# Admin Info
ADMIN_EMAIL = "admin@unsw.edu.au"
ADMIN_PASSWORD = "unswcse2025"

# JWT Authentication
def require_admin(f):
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

# Admin Login
@admin_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
        token = jwt.encode(
            {
                "role": "admin",
                "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
            },
            current_app.config["SECRET_KEY"],
            algorithm="HS256"
        )
        return jsonify({"token": token}), 200

    return jsonify({"error": "Invalid credentials"}), 401



