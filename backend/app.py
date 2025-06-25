from flask import Flask, request, jsonify
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

# Load API key
openai.api_key = os.getenv("OPENAI_API_KEY")

# User Query
@app.route('/api/query', methods=['POST'])
def query():
    data = request.get_json()
    question = data.get("question")
    session_id = data.get("session_id", "unknown-session")
    
    if not question:
        return jsonify({"error": "Question is required"}), 400
    
    response = f"The question is: {question}" # TODO: Replace with actual LLM response
    return jsonify({
        "answer": response,
        "session_id": session_id,
        "status": "answered"
    })

# Start the server
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

