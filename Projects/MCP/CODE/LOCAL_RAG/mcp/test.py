#!/usr/bin/env python3
"""
Simple test to verify MCP server works
"""
import json
import subprocess
import sys
import os

def test_server_manually():
    """Test server by sending JSON directly"""
    print("=== Testing MCP Server Manually ===")
    
    # Start server process
    try:
        process = subprocess.Popen(
            [sys.executable, "mcp_server.py"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Send initialize request
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0"}
            }
        }
        
        print("Sending initialize request...")
        process.stdin.write(json.dumps(init_request) + "\n")
        process.stdin.flush()
        
        # Read response
        response_line = process.stdout.readline()
        if response_line:
            response = json.loads(response_line.strip())
            print("✓ Initialize response:", json.dumps(response, indent=2))
        else:
            print("✗ No response received")
            stderr = process.stderr.read()
            if stderr:
                print("Server error:", stderr)
        
        # Send resources/list request
        list_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "resources/list"
        }
        
        print("\nSending resources/list request...")
        process.stdin.write(json.dumps(list_request) + "\n")
        process.stdin.flush()
        
        # Read response
        response_line = process.stdout.readline()
        if response_line:
            response = json.loads(response_line.strip())
            print("✓ Resources list:", json.dumps(response, indent=2))
        else:
            print("✗ No response received")
        
        # Cleanup
        process.terminate()
        process.wait()
        
    except Exception as e:
        print(f"✗ Test failed: {e}")

def check_files():
    """Check if required files exist"""
    print("=== Checking Files ===")
    
    files_to_check = [
        "mcp_server.py",
        "data/users.json", 
        "data/settings.json"
    ]
    
    all_exist = True
    for file_path in files_to_check:
        exists = os.path.exists(file_path)
        status = "✓" if exists else "✗"
        print(f"{status} {file_path}")
        if not exists:
            all_exist = False
    
    return all_exist

def main():
    print("🔧 MCP Test Script")
    print()
    
    # Check files first
    if not check_files():
        print("\n❌ Missing required files!")
        print("Make sure you have:")
        print("- mcp_server.py")
        print("- data/users.json")
        print("- data/settings.json")
        return
    
    print("\n✅ All files present")
    
    # Test server
    test_server_manually()

if __name__ == "__main__":
    main()