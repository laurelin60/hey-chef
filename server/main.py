from flask import Flask, request, jsonify
from perplexity import get_chat_response

app = Flask(__name__)

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    if 'message' not in data:
        return jsonify({'error': 'No message provided'}), 400
    
    message = data['message']
    response = get_chat_response(message)
    
    return jsonify({'response': response})

if __name__ == '__main__':
    app.run(debug=True)
    # To run the server, execute the following command in your terminal:
    # python /Users/zackeryhe/Desktop/hey-chef/server/main.py

    # To perform a dummy POST request, open a new terminal and use the following curl command:
    # curl -X POST http://127.0.0.1:5000/chat -H "Content-Type: application/json" -d '{"message": "Hello"}'