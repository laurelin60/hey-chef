from flask import Flask, request, jsonify
from perplexity import get_chat_response
from singlestore import *

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

@app.route('/callsessioncontexts', methods=['GET'])
def get_call_session_texts():
    data = fetch_data_from_table("CallSessionContexts")
    return jsonify(data)

# @app.route('/callsessionimages', methods=['GET'])
# def get_call_session_images():
#     data = fetch_image_data_from_table("CallSessionImages")
#     return jsonify(data)

# add routes that insert into callsession, callsessioncontexts, and callsessionimages tables
@app.route('/callsessions', methods=['POST'])
def insert_call_session():
    insert_new_call_session()
    return jsonify({'message': 'success'})

@app.route('/callsessioncontexts', methods=['POST'])
def insert_call_session_context():
    data = request.json
    if 'callId' not in data or 'contextData' not in data:
        return jsonify({'error': 'Missing callId or text'}), 400

    call_id = data['callId']
    contextData = data['contextData']
    insert_new_call_session_context(call_id, contextData)
    return jsonify({'message': 'success'})

@app.route('/callsessionimages', methods=['POST'])
def insert_call_session_image():
    data = request.json
    if 'callId' not in data or 'image' not in data:
        return jsonify({'error': 'Missing callId or image'}), 400

    call_id = data['callId']
    image = data['image']
    vectorize_and_insert_image(call_id, image)
    return jsonify({'message': 'success'})
        

if __name__ == '__main__':
    app.run(debug=True)
    # To run the server, execute the following command in your terminal:
    # python /Users/zackeryhe/Desktop/hey-chef/server/main.py

    # To perform a dummy POST request, open a new terminal and use the following curl command:
    # curl -X POST http://127.0.0.1:5000/chat -H "Content-Type: application/json" -d '{"message": "What is gordon ramsay's ham and cheese sandwich?"}'




