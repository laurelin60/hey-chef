from flask import Flask, request, jsonify
from perplexity import get_chat_response
from singlestore import fetch_data_from_table

app = Flask(__name__)

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    if 'message' not in data:
        return jsonify({'error': 'No message provided'}), 400
    
    message = data['message']
    response = get_chat_response(message)
    
    return jsonify({'response': response})


@app.route('/callsessions', methods=['GET'])
def get_call_sessions():
    data = fetch_data_from_table("CallSessions")
    return jsonify(data)

@app.route('/callsessiontexts', methods=['GET'])
def get_call_session_texts():
    data = fetch_data_from_table("CallSessionTexts")
    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True)
    # To run the server, execute the following command in your terminal:
    # python /Users/zackeryhe/Desktop/hey-chef/server/main.py

    # To perform a dummy POST request, open a new terminal and use the following curl command:
    # curl -X POST http://127.0.0.1:5000/chat -H "Content-Type: application/json" -d '{"message": "What is gordon ramsay's ham and cheese sandwich?"}'




