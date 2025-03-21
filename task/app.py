from flask import Flask
from flask_jwt_extended import JWTManager
from config import Config
from auth import auth_bp
from products import products_bp  

app = Flask(__name__)  
app.config.from_object(Config)


if not app.config.get("JWT_SECRET_KEY"):
    raise ValueError("⚠️ Error: JWT_SECRET_KEY is missing from Config!")


jwt = JWTManager(app)


app.register_blueprint(auth_bp, url_prefix="/auth")
app.register_blueprint(products_bp, url_prefix="/api") 


print("🔍 Registered Routes:")
for rule in app.url_map.iter_rules():
    print(rule)

if __name__ == "__main__":
    try:
        app.run(debug=True)
    except Exception as e:
        print(f"❌ Error: {e}")
