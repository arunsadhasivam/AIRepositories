from flask import Flask
from app import app
from mcp.mcp_server import mcp_bp

rest = Flask(__name__)
rest.register_blueprint(app)
rest.register_blueprint(mcp_bp)

rest.run(port=8080)