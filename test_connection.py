#!/usr/bin/env python3
"""
Test script to verify BlenderMCP connection
"""

import socket
import json
import time

def test_blender_connection():
    """Test connection to Blender addon"""
    print("Testing BlenderMCP connection...")
    
    try:
        # Create socket connection
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        
        print("Attempting to connect to Blender on localhost:9876...")
        sock.connect(('localhost', 9876))
        print("✓ Connected to Blender!")
        
        # Test basic command
        test_command = {
            "type": "get_scene_info",
            "params": {}
        }
        
        print("Sending test command...")
        sock.sendall(json.dumps(test_command).encode('utf-8'))
        
        # Receive response
        response_data = sock.recv(4096)
        response = json.loads(response_data.decode('utf-8'))
        
        print(f"✓ Received response: {response.get('status', 'unknown')}")
        
        if response.get('status') == 'success':
            print("✓ BlenderMCP connection is working!")
            scene_info = response.get('result', {})
            print(f"Scene: {scene_info.get('scene_name', 'Unknown')}")
            print(f"Objects: {len(scene_info.get('objects', []))}")
        else:
            print(f"✗ Error: {response.get('message', 'Unknown error')}")
        
        sock.close()
        return True
        
    except socket.timeout:
        print("✗ Connection timeout - is Blender running with the addon enabled?")
        return False
    except ConnectionRefusedError:
        print("✗ Connection refused - is the Blender addon server running?")
        print("Make sure to:")
        print("1. Install the addon.py in Blender")
        print("2. Enable the addon in Edit > Preferences > Add-ons")
        print("3. Click 'Connect to Claude' in the BlenderMCP panel")
        return False
    except Exception as e:
        print(f"✗ Connection error: {str(e)}")
        return False

if __name__ == "__main__":
    test_blender_connection() 