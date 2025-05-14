from flask import Flask, jsonify
from flask_jwt_extended import JWTManager
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from datetime import timedelta
from constants.settings import Settings
import os

db = SQLAlchemy()

def create_app():
    load_dotenv()
    
    app = Flask(__name__)

    # Setting JWT
    app.config["JWT_SECRET_KEY"] = os.environ.get('JWT_KEY')
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=Settings.ACCESS_TOKEN_EXPIRES_HOURS)
    app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=Settings.REFRESH_TOKEN_EXPIRES_DAY)

    # Setting Database
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize JWT
    jwt = JWTManager(app)

    # Add expired token callback
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({
            "message": "토큰이 만료되었습니다. 다시 로그인해주세요."
        }), 401
    
    # Connect DB
    db.init_app(app)

    # Register routes
    from app.routes import bp as routes_bp
    app.register_blueprint(routes_bp)

    return app