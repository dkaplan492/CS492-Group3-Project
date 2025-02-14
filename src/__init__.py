import os
from flask import Flask
from flask_pymongo import PyMongo
from dotenv import load_dotenv

# Initialize the MongoDB connection
mongo = PyMongo()

def create_app():
    # Load environment variables
    load_dotenv()

    app = Flask(__name__)

    # Configure the MongoDB URI (from environment variable for security)
    app.config['MONGO_URI'] = os.getenv('MONGO_URI')  # Store MongoDB URI in a .env file
    app.secret_key = os.getenv('SECRET_KEY', 'your_secret_key')  # Load SECRET_KEY from .env

    # Initialize MongoDB
    mongo.init_app(app)
    print(f"MONGO_URI: {app.config.get('MONGO_URI')}")
    print(f"Mongo initialized: {mongo}")


    # Import and register blueprints
    from .main import main as main_blueprint
    from .auth import auth as auth_blueprint

    app.register_blueprint(main_blueprint)
    app.register_blueprint(auth_blueprint)

    return app