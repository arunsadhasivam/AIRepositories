#!/usr/bin/env python3
"""
MCP HTTP Server - Exposes MCP functionality via REST API endpoints
"""

from flask import Flask, request, jsonify,Blueprint

import json
import asyncio
from datetime import datetime
import logging
import sys
from typing import Dict, Any, List
from prompt.query import query

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp_bp = Blueprint('mcp', __name__)

class MCPServer:
    def __init__(self):
        self.tools = {
            "get_weather": {
                "description": "Get current weather for a location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "City name or location"
                        }
                    },
                    "required": ["location"]
                }
            },
            "calculate": {
                "description": "Perform mathematical calculations",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "expression": {
                            "type": "string",
                            "description": "Mathematical expression to evaluate"
                        }
                    },
                    "required": ["expression"]
                }
            },
            "get_time": {
                "description": "Get current date and time",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
        
        self.resources = {
            "system_info": {
                "description": "System information resource",
                "uri": "system://info",
                "mimeType": "application/json"
            },
            "config": {
                "description": "Server configuration",
                "uri": "config://server",
                "mimeType": "application/json"
            }
        }

    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool with given parameters"""
        try:
            if tool_name == "get_weather":
                location = parameters.get("location", "Unknown")
                # Simulate weather data
                return {
                    "success": True,
                    "result": {
                        "location": location,
                        "temperature": "22°C",
                        "condition": "Partly cloudy",
                        "humidity": "65%",
                        "timestamp": datetime.now().isoformat()
                    }
                }
            
            elif tool_name == "calculate":
                expression = parameters.get("expression", "")
                try:
                    # Simple calculator (be careful with eval in production!)
                    result = eval(expression)
                    return {
                        "success": True,
                        "result": {
                            "expression": expression,
                            "answer": result,
                            "timestamp": datetime.now().isoformat()
                        }
                    }
                except Exception as e:
                    return {
                        "success": False,
                        "error": f"Calculation error: {str(e)}"
                    }
            
            elif tool_name == "get_time":
                return {
                    "success": True,
                    "result": {
                        "current_time": datetime.now().isoformat(),
                        "timezone": "UTC",
                        "timestamp": datetime.now().timestamp()
                    }
                }
            
            else:
                return {
                    "success": False,
                    "error": f"Unknown tool: {tool_name}"
                }
                
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {str(e)}")
            return {
                "success": False,
                "error": f"Tool execution failed: {str(e)}"
            }

    async def get_resource(self, resource_name: str) -> Dict[str, Any]:
        """Get a resource by name"""
        try:
            if resource_name == "system_info":
                return {
                    "success": True,
                    "result": {
                        "server": "MCP HTTP Server",
                        "version": "1.0.0",
                        "uptime": datetime.now().isoformat(),
                        "tools_count": len(self.tools),
                        "resources_count": len(self.resources)
                    }
                }
            
            elif resource_name == "config":
                return {
                    "success": True,
                    "result": {
                        "server_config": {
                            "host": "localhost",
                            "port": 5000,
                            "debug": True,
                            "tools_enabled": list(self.tools.keys())
                        }
                    }
                }
            
            else:
                return {
                    "success": False,
                    "error": f"Unknown resource: {resource_name}"
                }
                
        except Exception as e:
            logger.error(f"Error getting resource {resource_name}: {str(e)}")
            return {
                "success": False,
                "error": f"Resource retrieval failed: {str(e)}"
            }

# Initialize MCP server
mcp_server = MCPServer()

@mcp_bp.route('/mcp/query', methods=['POST'])
def mcp_route_query():
    data = request.get_json()
    print('MCP Query APP:data:::',data )
    response = query(data.get('query'))
    print('MCP APP:response:::'+response )
     

    if response:
        return jsonify({"message": response}), 200

    return jsonify({"error": "Something went wrong"}), 400


@mcp_bp.route('/', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "server": "MCP HTTP Server",
        "timestamp": datetime.now().isoformat()
    })

@mcp_bp.route('/tools', methods=['GET'])
def list_tools():
    """List all available tools"""
    return jsonify({
        "success": True,
        "tools": mcp_server.tools
    })

@mcp_bp.route('/tools/<tool_name>', methods=['POST'])
def execute_tool(tool_name):
    """Execute a specific tool"""
    try:
        # Get parameters from request
        data = request.get_json() or {}
        parameters = data.get('parameters', {})
        
        # Run async tool execution
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            mcp_server.execute_tool(tool_name, parameters)
        )
        loop.close()
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in execute_tool endpoint: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Request failed: {str(e)}"
        }), 500

@mcp_bp.route('/resources', methods=['GET'])
def list_resources():
    """List all available resources"""
    return jsonify({
        "success": True,
        "resources": mcp_server.resources
    })

@mcp_bp.route('/resources/<resource_name>', methods=['GET'])
def get_resource(resource_name):
    """Get a specific resource"""
    try:
        # Run async resource retrieval
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            mcp_server.get_resource(resource_name)
        )
        loop.close()
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in get_resource endpoint: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Request failed: {str(e)}"
        }), 500

@mcp_bp.route('/invoke', methods=['POST'])
def invoke_generic():
    """Generic invoke endpoint for any tool or resource"""
    try:
        data = request.get_json() or {}
        action_type = data.get('type')  # 'tool' or 'resource'
        name = data.get('name')
        parameters = data.get('parameters', {})
        
        if not action_type or not name:
            return jsonify({
                "success": False,
                "error": "Missing 'type' or 'name' in request"
            }), 400
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        if action_type == 'tool':
            result = loop.run_until_complete(
                mcp_server.execute_tool(name, parameters)
            )
        elif action_type == 'resource':
            result = loop.run_until_complete(
                mcp_server.get_resource(name)
            )
        else:
            result = {
                "success": False,
                "error": f"Unknown action type: {action_type}"
            }
        
        loop.close()
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in invoke endpoint: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Request failed: {str(e)}"
        }), 500

@mcp_bp.errorhandler(404)
def not_found(error):
    return jsonify({
        "success": False,
        "error": "Endpoint not found"
    }), 404

@mcp_bp.errorhandler(500)
def internal_error(error):
    return jsonify({
        "success": False,
        "error": "Internal server error"
    }), 500

if __name__ == '__main__':
    print("Starting MCP HTTP Server...")
    print("Available endpoints:")
    print("  GET  /                     - Health check")
    print("  GET  /tools                - List all tools")
    print("  POST /tools/<tool_name>    - Execute specific tool")
    print("  GET  /resources            - List all resources")
    print("  GET  /resources/<name>     - Get specific resource")
    print("  POST /invoke               - Generic invoke endpoint")
    print("\nExample usage:")
    print("  curl http://localhost:8080/tools")
    print("  curl -X POST http://localhost:8080/tools/get_weather -H 'Content-Type: application/json' -d '{\"parameters\": {\"location\": \"New York\"}}'")
    print("  curl -X POST http://localhost:8080/invoke -H 'Content-Type: application/json' -d '{\"type\": \"tool\", \"name\": \"calculate\", \"parameters\": {\"expression\": \"2+2\"}}'")
    
    mcp_bp.run(host='0.0.0.0', port=8080, debug=True)