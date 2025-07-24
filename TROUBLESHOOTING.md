# BlenderMCP Troubleshooting Guide

## Connection Issues Between Claude and Blender

The main issue with connecting Claude to Blender was that the `addon.py` file was **severely incomplete** and missing all the required command handlers. This has been fixed in the updated version.

## Common Issues and Solutions

### 1. "Connection refused" or "Connection timeout" errors

**Problem**: The MCP server cannot connect to the Blender addon.

**Solutions**:
1. **Make sure Blender is running** with the addon installed and enabled
2. **Install the updated addon.py** (the previous version was incomplete)
3. **Enable the addon** in Blender:
   - Go to Edit > Preferences > Add-ons
   - Search for "BlenderMCP" 
   - Check the box to enable it
4. **Start the server** in Blender:
   - Open the 3D Viewport sidebar (press N)
   - Find the "BlenderMCP" tab
   - Click "Connect to Claude"

### 2. "Unknown command type" errors

**Problem**: The addon doesn't recognize commands from the MCP server.

**Solution**: This was caused by missing command handlers in the original addon. The updated `addon.py` now includes all required handlers:
- `get_scene_info`
- `get_object_info` 
- `create_object`
- `modify_object`
- `delete_object`
- `execute_code`
- `set_material`
- `get_viewport_screenshot`
- And more...

### 3. MCP server fails to start

**Problem**: The `uvx blender-mcp` command fails.

**Solutions**:
1. **Install uv package manager**:
   ```bash
   # On Mac
   brew install uv
   
   # On Windows
   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```
2. **Verify Python version**: Ensure you have Python 3.10 or newer
3. **Check dependencies**: The project requires `mcp[cli]>=1.3.0`

### 4. Claude doesn't show Blender tools

**Problem**: Claude doesn't display the hammer icon or Blender tools.

**Solutions**:
1. **Check MCP configuration** in Claude Desktop:
   ```json
   {
       "mcpServers": {
           "blender": {
               "command": "uvx",
               "args": ["blender-mcp"]
           }
       }
   }
   ```
2. **Restart Claude** after updating the configuration
3. **Verify the MCP server is running** in the background

### 5. Blender addon doesn't appear in the sidebar

**Problem**: The BlenderMCP panel is not visible in the 3D Viewport.

**Solutions**:
1. **Reinstall the addon** with the updated `addon.py`
2. **Check for errors** in Blender's System Console (Window > Toggle System Console on Windows)
3. **Verify the addon is enabled** in Edit > Preferences > Add-ons

## Testing the Connection

Use the provided `test_connection.py` script to verify the connection:

```bash
python3 test_connection.py
```

This will:
- Test the socket connection to Blender
- Send a test command
- Verify the response format

## Step-by-Step Setup

1. **Install the updated addon**:
   - Download the fixed `addon.py` from this repository
   - In Blender: Edit > Preferences > Add-ons > Install
   - Select the `addon.py` file
   - Enable the addon

2. **Start the Blender server**:
   - Open 3D Viewport sidebar (N key)
   - Find "BlenderMCP" tab
   - Click "Connect to Claude"

3. **Configure Claude**:
   - Go to Claude > Settings > Developer > Edit Config
   - Add the MCP server configuration
   - Restart Claude

4. **Test the connection**:
   - Run `python3 test_connection.py`
   - Try asking Claude to "get scene info"

## What Was Fixed

The original `addon.py` was missing:
- All command handler methods (`get_scene_info`, `create_object`, etc.)
- Proper UI panel and operators
- Scene properties for integrations
- Complete server implementation

The updated version includes:
- ✅ All required command handlers
- ✅ Proper UI panel in the 3D Viewport sidebar
- ✅ Connect/Disconnect operators
- ✅ Integration toggles for PolyHaven and Hyper3D
- ✅ Robust error handling and logging
- ✅ Proper socket communication

## Still Having Issues?

If you're still experiencing problems:

1. **Check the logs**:
   - Blender System Console (Windows: Window > Toggle System Console)
   - Claude's developer console
   - Terminal output from `uvx blender-mcp`

2. **Verify versions**:
   - Blender 3.0 or newer
   - Python 3.10 or newer
   - Latest `addon.py` from this repository

3. **Test step by step**:
   - First test the addon installation
   - Then test the socket connection
   - Finally test the MCP server

4. **Common workarounds**:
   - Restart both Blender and Claude
   - Try a different port (modify port 9876 in both addon and server)
   - Check firewall settings
   - Ensure no other applications are using port 9876 