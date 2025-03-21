from flask import Blueprint, request, jsonify, send_file
from database import get_db_connection
from flask_bcrypt import Bcrypt
import pyotp
import qrcode
from io import BytesIO
from flask_jwt_extended import create_access_token
from datetime import timedelta

bcrypt = Bcrypt()
auth_bp = Blueprint("auth", __name__)

# 🟢 User Registration
@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Please provide a username and password"}), 400

    hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")
    twofa_secret = pyotp.random_base32()  # 🔹 Generate a 2FA secret key for the user

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            "INSERT INTO users (username, password, twofa_secret) VALUES (%s, %s, %s)",
            (username, hashed_password, twofa_secret),
        )
        connection.commit()
        return jsonify({"message": "User registered successfully", "2FA_secret": twofa_secret}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        connection.close()

# 🟢 Login (Password Verification Only)
@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Please provide a username and password"}), 400

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()

    cursor.close()
    connection.close()

    if not user or not bcrypt.check_password_hash(user["password"], password):
        return jsonify({"error": "❌ Incorrect username or password"}), 401

    return jsonify({"message": "✅ Please enter your 2FA code"}), 200

# 🟢 Generate QR Code for 2FA Secret Key
@auth_bp.route("/generate_qr/<username>", methods=["GET"])
def generate_qr(username):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT twofa_secret FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()

    cursor.close()
    connection.close()

    if not user:
        return jsonify({"error": "User not found"}), 404

    twofa_secret = user["twofa_secret"]
    otp_uri = pyotp.TOTP(twofa_secret).provisioning_uri(name=username, issuer_name="FlaskAuthApp")

    # 🟢 Optimize QR Code size
    qr = qrcode.QRCode(
        version=2,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=5,
        border=2,
    )
    qr.add_data(otp_uri)
    qr.make(fit=True)

    img = qr.make_image(fill="black", back_color="white")

    # 🟢 Save and return the QR code image
    qr_io = BytesIO()
    img.save(qr_io, format="PNG")
    qr_io.seek(0)

    return send_file(qr_io, mimetype="image/png")

# 🟢 Verify 2FA Code
@auth_bp.route("/verify_2fa", methods=["POST"])
def verify_2fa():
    data = request.json
    username = data.get("username")
    otp_code = data.get("otp_code")

    if not username or not otp_code:
        return jsonify({"error": "Username and 2FA code are required"}), 400

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT twofa_secret FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()

    cursor.close()
    connection.close()

    if not user:
        return jsonify({"error": "User not found"}), 404

    twofa_secret = user["twofa_secret"]
    totp = pyotp.TOTP(twofa_secret, interval=30)  # ✅ Google Authenticator uses interval=30
    expected_code = totp.now()
    print(f"🔍 [DEBUG] Expected 2FA Code: {expected_code}")

    is_valid = totp.verify(otp_code, valid_window=2)  # 🔹 Allows previous and next codes

    if not is_valid:
        print(f"🚨 [DEBUG] Invalid or expired 2FA code: {otp_code}")
        return jsonify({"error": "❌ Invalid or expired 2FA code"}), 401

    return jsonify({"message": "✅ 2FA verification successful!"}), 200

# 🟢 Verify 2FA and Issue JWT Token
@auth_bp.route("/login_2fa", methods=["POST"])
def login_2fa():
    data = request.json
    username = data.get("username")
    otp_code = data.get("otp_code")

    if not username or not otp_code:
        return jsonify({"error": "Username and 2FA code are required"}), 400

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT twofa_secret FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()

    cursor.close()
    connection.close()

    if not user:
        return jsonify({"error": "User not found"}), 404

    twofa_secret = user["twofa_secret"]
    totp = pyotp.TOTP(twofa_secret, interval=30)
    expected_code = totp.now()
    print(f"🔍 [DEBUG] Expected 2FA Code: {expected_code}")

    is_valid = totp.verify(otp_code, valid_window=2)

    if not is_valid:
        print(f"🚨 [DEBUG] Invalid or expired 2FA code: {otp_code}")
        return jsonify({"error": "❌ Invalid or expired 2FA code"}), 401

    # 🟢 Issue JWT valid for 10 minutes
    access_token = create_access_token(identity=username, expires_delta=timedelta(minutes=10))
    return jsonify({"message": "✅ Login successful!", "token": access_token}), 200
