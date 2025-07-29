import os
import threading
from flask import Flask
from flask_cors import CORS
from routes.user import user_bp
from routes.admin import admin_bp
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
CORS(app)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-change-in-production')

# Register Blueprints
app.register_blueprint(user_bp, url_prefix='/api')
app.register_blueprint(admin_bp, url_prefix='/api/admin')

def initialize_vector_store():
    """Initialize vector store in background if it doesn't exist"""
    try:
        from rag.vector_store import validate_vector_database_exists
        from rag import update_knowledge_base
        
        if not validate_vector_database_exists():
            print("[App] Vector store not found, initializing in background...")
            print("[App] This may take a few minutes for first-time setup...")
            
            # Initialize vector store with existing content
            result = update_knowledge_base(include_scraped=True)
            if result:
                print("[App] Vector store initialization completed successfully")
            else:
                print("[App] Vector store initialization completed (no updates needed)")
        else:
            print("[App] Vector store already exists and is valid")
            
    except Exception as e:
        print(f"[App] Error during vector store initialization: {e}")
        print("[App] Application will continue to run, but search functionality may be limited")

# Initialize vector store in background thread to avoid blocking app startup
print("[App] Starting vector store initialization check...")
init_thread = threading.Thread(target=initialize_vector_store, daemon=True)
init_thread.start()

if __name__ == '__main__':
    debug = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 5000))
    app.run(debug=debug, host=host, port=port)


