import os
from dotenv import load_dotenv

load_dotenv()

from flask import Flask, request, jsonify

from embeddings.DocumentEmbedding import DocumentEmbedder
from prompt.query import query
import logging
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("langchain").setLevel(logging.WARNING)
logging.getLogger("pgvector").setLevel(logging.WARNING)
logging.getLogger("presidio-analyzer").setLevel(logging.WARNING)
logging.getLogger("presidio-anonymizer").setLevel(logging.WARNING)
logging.getLogger("pdfminer").setLevel(logging.WARNING)
logging.getLogger("matplotlib").setLevel(logging.WARNING)
logging.getLogger("layoutparser").setLevel(logging.WARNING)
logging.getLogger("numexpr").setLevel(logging.WARNING)
logging.getLogger("unstructured").setLevel(logging.WARNING)
logging.getLogger("filelock").setLevel(logging.WARNING)
logging.getLogger(":pikepdf._core").setLevel(logging.WARNING)

TEMP_FOLDER = os.getenv('TEMP_FOLDER', './_temp')
os.makedirs(TEMP_FOLDER, exist_ok=True)

app = Flask(__name__)
@app.route('/embed', methods=['POST'])
def route_embed():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    data = request.form
    user_role = data.get("user_role")
    pwd = data.get("password")

    logging.info(f'::::: REST EMBED CONTROLLER: file={file}, user_role={user_role}, pwd={pwd}')

    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    if(user_role=='' or pwd ==''):
         return jsonify({"error": "enter valid user/pwd"}), 400
    docEmbed = DocumentEmbedder()

    embedded = docEmbed.embed(file,user_role,pwd)

    if embedded:
        return jsonify({"message": "File embedded successfully"}), 200

    return jsonify({"error": "File embedded unsuccessfully"}), 400

@app.route('/query', methods=['POST'])
def route_query():
    data = request.get_json()
    logging.info('::::: REST CONTROLLER ::::::::::::Query APP:data:::',data )
    #search_type,user_role,st.session_state.password
    search_query=data.get('query')
    search_type=data.get('search_type')
    user_role=data.get('user_role')
    pwd = data.get('pwd')
    logging.info(f'::::: REST API : route_query::::{search_query} , search_type:{search_type},user_role={user_role},pwd={pwd}' )

    response = query(search_query,search_type,user_role,pwd)
    #logging.info(f'::::: APP:response:::'+response )
     

    if response:
        return jsonify({"message": response}), 200

    return jsonify({"error": "Something went wrong"}), 400

@app.route('/delete', methods=['DELETE'])
def route_delete():
    data = request.get_json()
    user_role = data.get("user_role")
    pwd = data.get("password")
    docEmbed = DocumentEmbedder()
    db = docEmbed.get_pg_vector_connection(user_role=user_role,pwd=pwd)
    db.delete_collection()

    return jsonify({"message": "Collection deleted successfully"}), 200



@app.route('/admin/clear-cache', methods=['POST'])
def admin_clear_cache():
    """
    Admin endpoint to manually clear connection cache.
    Requires authentication in production.
    """
    try:
        # Clear the cache
        docEmbed = DocumentEmbedder()
        docEmbed.clear_connection_cache()
        # Return success response
        return jsonify({
            'status': 'success',
            'message': 'Database connection cache cleared'
        }), 200
    except Exception as e:
        # Return error response
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080, debug=False)

