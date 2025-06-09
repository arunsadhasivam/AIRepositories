import os
from dotenv import load_dotenv

load_dotenv()

from flask import Flask, request, jsonify,Blueprint
from embeddings.embed import embed
from embeddings.get_vector_db import get_vector_db
from prompt.query import query
from mcp.mcp_server import MCPServer

TEMP_FOLDER = os.getenv('TEMP_FOLDER', './_temp')
os.makedirs(TEMP_FOLDER, exist_ok=True)

app = Blueprint('app',__name__)
@app.route('/embed', methods=['POST'])
def route_embed():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    embedded = embed(file)

    if embedded:
        return jsonify({"message": "File embedded successfully"}), 200

    return jsonify({"error": "File embedded unsuccessfully"}), 400

@app.route('/query', methods=['POST'])
def route_query():
    data = request.get_json()
    print('Query APP:data:::',data )
    response = query(data.get('query'))
    print('APP:response:::'+response )
     

    if response:
        return jsonify({"message": response}), 200

    return jsonify({"error": "Something went wrong"}), 400

@app.route('/delete', methods=['DELETE'])
def route_delete():
    db = get_vector_db()
    db.delete_collection()

    return jsonify({"message": "Collection deleted successfully"}), 200

if __name__ == '__main__':
    mcp_server = MCPServer()
    combined_app = Flask(__name__)
    combined_app = Flask(__name__)
    combined_app.register_blueprint(app, url_prefix='/app')
    combined_app.register_blueprint(mcp_server, url_prefix='/mcp_server')
    combined_app.run(host="0.0.0.0", port=8080, debug=True)

