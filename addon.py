import bpy
import mathutils
import json
import threading
import socket
import time
import requests
import tempfile
import traceback
import os
import shutil
from bpy.props import StringProperty, IntProperty, BoolProperty, EnumProperty


bl_info = {
    "name": "Blender MCP Fixed",
    "author": "BlenderMCP",
    "version": (0, 2),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > BlenderMCP",
    "description": "Connect Blender to Claude via MCP (Fixed Version)",
    "category": "Interface",
}

class BlenderMCPServer:
    def __init__(self, host='localhost', port=9876):
        self.host = host
        self.port = port
        self.running = False
        self.socket = None
        self.server_thread = None
    
    def start(self):
        if self.running:
            print("Server is already running")
            return
            
        self.running = True
        
        try:
            # Create socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((self.host, self.port))
            self.socket.listen(1)
            
            # Start server thread
            self.server_thread = threading.Thread(target=self._server_loop)
            self.server_thread.daemon = True
            self.server_thread.start()
            
            print(f"BlenderMCP server started on {self.host}:{self.port}")
        except Exception as e:
            print(f"Failed to start server: {str(e)}")
            self.stop()
            
    def stop(self):
        self.running = False
        
        # Close socket
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        
        # Wait for thread to finish
        if self.server_thread:
            try:
                if self.server_thread.is_alive():
                    self.server_thread.join(timeout=1.0)
            except:
                pass
            self.server_thread = None
        
        print("BlenderMCP server stopped")
    
    def _server_loop(self):
        """Main server loop in a separate thread"""
        print("Server thread started")
        self.socket.settimeout(1.0)  # Timeout to allow for stopping
        
        while self.running:
            try:
                # Accept new connection
                try:
                    client, address = self.socket.accept()
                    print(f"Connected to client: {address}")
                    
                    # Handle client in a separate thread
                    client_thread = threading.Thread(
                        target=self._handle_client,
                        args=(client,)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                except socket.timeout:
                    # Just check running condition
                    continue
                except Exception as e:
                    if not self.running:
                        break
                    print(f"Error accepting connection: {str(e)}")
            except Exception as e:
                if not self.running:
                    break
                print(f"Error in server loop: {str(e)}")
    
    def _handle_client(self, client):
        """Handle a client connection"""
        print("Client handler started")
        client.settimeout(15.0)  # 15 second timeout
        
        try:
            buffer = b""
            while self.running:
                try:
                    # Receive data
                    data = client.recv(4096)
                    if not data:
                        break
                    
                    buffer += data
                    
                    # Try to parse JSON
                    try:
                        command = json.loads(buffer.decode('utf-8'))
                        buffer = b""  # Clear buffer after successful parse
                        
                        print(f"Received command: {command.get('type', 'unknown')}")
                        
                        # Execute command in main thread
                        def execute_wrapper():
                            try:
                                response = self.execute_command(command)
                                client.sendall(json.dumps(response).encode('utf-8'))
                            except Exception as e:
                                print(f"Error executing command: {str(e)}")
                                error_response = {
                                    "status": "error",
                                    "message": str(e)
                                }
                                client.sendall(json.dumps(error_response).encode('utf-8'))
                            return None
                        
                        # Schedule execution in main thread
                        bpy.app.timers.register(execute_wrapper, first_interval=0.0)
                    except json.JSONDecodeError:
                        # Incomplete data, wait for more
                        pass
                except Exception as e:
                    print(f"Error receiving data: {str(e)}")
                    break
        except Exception as e:
            print(f"Error in client handler: {str(e)}")
        finally:
            try:
                client.close()
            except:
                pass
            print("Client handler stopped")

    def execute_command(self, command):
        """Execute a command in the main Blender thread"""
        try:
            cmd_type = command.get("type")
            params = command.get("params", {})
            
            # Ensure we're in the right context
            if cmd_type in ["create_object", "modify_object", "delete_object"]:
                override = bpy.context.copy()
                override['area'] = [area for area in bpy.context.screen.areas if area.type == 'VIEW_3D'][0]
                with bpy.context.temp_override(**override):
                    return self._execute_command_internal(command)
            else:
                return self._execute_command_internal(command)
                
        except Exception as e:
            print(f"Error executing command: {str(e)}")
            traceback.print_exc()
            return {"status": "error", "message": str(e)}

    def _execute_command_internal(self, command):
        """Internal command execution with proper context"""
        cmd_type = command.get("type")
        params = command.get("params", {})

        # Add a handler for checking PolyHaven status
        if cmd_type == "get_polyhaven_status":
            return {"status": "success", "result": self.get_polyhaven_status()}
        
        # Base handlers that are always available
        handlers = {
            "get_scene_info": self.get_scene_info,
            "create_object": self.create_object,
            "modify_object": self.modify_object,
            "delete_object": self.delete_object,
            "get_object_info": self.get_object_info,
            "execute_code": self.execute_code,
            "set_material": self.set_material,
            "get_polyhaven_status": self.get_polyhaven_status,
            "get_hyper3d_status": self.get_hyper3d_status,
            "get_viewport_screenshot": self.get_viewport_screenshot,
        }
        
        # Add Polyhaven handlers only if enabled
        if bpy.context.scene.blendermcp_use_polyhaven:
            polyhaven_handlers = {
                "get_polyhaven_categories": self.get_polyhaven_categories,
                "search_polyhaven_assets": self.search_polyhaven_assets,
                "download_polyhaven_asset": self.download_polyhaven_asset,
                "set_texture": self.set_texture,
            }
            handlers.update(polyhaven_handlers)
        
        # Add Hyper3d handlers only if enabled
        if bpy.context.scene.blendermcp_use_hyper3d:
            polyhaven_handlers = {
                "create_rodin_job": self.create_rodin_job,
                "poll_rodin_job_status": self.poll_rodin_job_status,
                "import_generated_asset": self.import_generated_asset,
            }
            handlers.update(polyhaven_handlers)

        handler = handlers.get(cmd_type)
        if handler:
            try:
                print(f"Executing handler for {cmd_type}")
                result = handler(**params)
                print(f"Handler execution complete")
                return {"status": "success", "result": result}
            except Exception as e:
                print(f"Error in handler: {str(e)}")
                traceback.print_exc()
                return {"status": "error", "message": str(e)}
        else:
            return {"status": "error", "message": f"Unknown command type: {cmd_type}"}

    # Command handlers
    def get_scene_info(self):
        """Get detailed information about the current scene"""
        scene = bpy.context.scene
        objects = []
        
        for obj in scene.objects:
            obj_info = {
                "name": obj.name,
                "type": obj.type,
                "location": [obj.location.x, obj.location.y, obj.location.z],
                "rotation": [obj.rotation_euler.x, obj.rotation_euler.y, obj.rotation_euler.z],
                "scale": [obj.scale.x, obj.scale.y, obj.scale.z],
                "visible": obj.visible_get(),
                "active": obj == scene.objects.active
            }
            
            if obj.type == 'MESH':
                obj_info["vertices"] = len(obj.data.vertices) if obj.data else 0
                obj_info["faces"] = len(obj.data.polygons) if obj.data else 0
            
            objects.append(obj_info)
        
        return {
            "scene_name": scene.name,
            "frame_current": scene.frame_current,
            "frame_start": scene.frame_start,
            "frame_end": scene.frame_end,
            "objects": objects,
            "camera": scene.camera.name if scene.camera else None,
            "render_engine": scene.render.engine
        }

    def get_object_info(self, name):
        """Get detailed information about a specific object"""
        obj = bpy.data.objects.get(name)
        if not obj:
            raise Exception(f"Object '{name}' not found")
        
        obj_info = {
            "name": obj.name,
            "type": obj.type,
            "location": [obj.location.x, obj.location.y, obj.location.z],
            "rotation": [obj.rotation_euler.x, obj.rotation_euler.y, obj.rotation_euler.z],
            "scale": [obj.scale.x, obj.scale.y, obj.scale.z],
            "visible": obj.visible_get(),
            "active": obj == bpy.context.scene.objects.active
        }
        
        if obj.type == 'MESH':
            obj_info["vertices"] = len(obj.data.vertices) if obj.data else 0
            obj_info["faces"] = len(obj.data.polygons) if obj.data else 0
            obj_info["materials"] = [mat.name if mat else None for mat in obj.material_slots]
        
        return obj_info

    def create_object(self, type="CUBE", location=[0, 0, 0], rotation=[0, 0, 0], scale=[1, 1, 1], name=None):
        """Create a new object in the scene"""
        if type.upper() == "CUBE":
            bpy.ops.mesh.primitive_cube_add(location=location)
        elif type.upper() == "SPHERE":
            bpy.ops.mesh.primitive_uv_sphere_add(location=location)
        elif type.upper() == "CYLINDER":
            bpy.ops.mesh.primitive_cylinder_add(location=location)
        elif type.upper() == "PLANE":
            bpy.ops.mesh.primitive_plane_add(location=location)
        else:
            raise Exception(f"Unknown object type: {type}")
        
        obj = bpy.context.active_object
        obj.rotation_euler = rotation
        obj.scale = scale
        if name:
            obj.name = name
        
        return {"name": obj.name, "type": obj.type}

    def modify_object(self, name, location=None, rotation=None, scale=None):
        """Modify an existing object"""
        obj = bpy.data.objects.get(name)
        if not obj:
            raise Exception(f"Object '{name}' not found")
        
        if location is not None:
            obj.location = location
        if rotation is not None:
            obj.rotation_euler = rotation
        if scale is not None:
            obj.scale = scale
        
        return {"name": obj.name, "modified": True}

    def delete_object(self, name):
        """Delete an object from the scene"""
        obj = bpy.data.objects.get(name)
        if not obj:
            raise Exception(f"Object '{name}' not found")
        
        bpy.data.objects.remove(obj, do_unlink=True)
        return {"deleted": name}

    def execute_code(self, code):
        """Execute arbitrary Python code in Blender"""
        try:
            # Create a local namespace with common Blender modules
            local_vars = {
                'bpy': bpy,
                'mathutils': mathutils,
                'context': bpy.context,
                'scene': bpy.context.scene,
                'data': bpy.data
            }
            
            # Execute the code
            exec(code, globals(), local_vars)
            
            return {"executed": True, "message": "Code executed successfully"}
        except Exception as e:
            raise Exception(f"Code execution failed: {str(e)}")

    def set_material(self, object_name, material_name, color=None):
        """Set a material on an object"""
        obj = bpy.data.objects.get(object_name)
        if not obj:
            raise Exception(f"Object '{object_name}' not found")
        
        # Get or create material
        mat = bpy.data.materials.get(material_name)
        if not mat:
            mat = bpy.data.materials.new(name=material_name)
        
        # Set color if provided
        if color:
            mat.use_nodes = True
            if mat.node_tree:
                principled = mat.node_tree.nodes.get('Principled BSDF')
                if principled:
                    principled.inputs['Base Color'].default_value = (*color, 1.0)
        
        # Assign material to object
        if obj.data.materials:
            obj.data.materials[0] = mat
        else:
            obj.data.materials.append(mat)
        
        return {"material_set": material_name}

    def get_viewport_screenshot(self, max_size=800, filepath=None, format="PNG"):
        """Capture a screenshot of the current viewport"""
        if not filepath:
            filepath = os.path.join(tempfile.gettempdir(), f"blender_screenshot_{os.getpid()}.png")
        
        # Set render settings
        bpy.context.scene.render.image_settings.file_format = format
        bpy.context.scene.render.filepath = filepath
        
        # Get the 3D viewport area
        area = None
        for a in bpy.context.screen.areas:
            if a.type == 'VIEW_3D':
                area = a
                break
        
        if not area:
            raise Exception("No 3D viewport found")
        
        # Take screenshot
        bpy.ops.screen.screenshot(
            filepath=filepath,
            show_viewer=False,
            full=False,
            check_existing=False
        )
        
        return {"filepath": filepath, "format": format}

    def get_polyhaven_status(self):
        """Get PolyHaven integration status"""
        return {
            "enabled": getattr(bpy.context.scene, 'blendermcp_use_polyhaven', False),
            "available": True
        }

    def get_hyper3d_status(self):
        """Get Hyper3D integration status"""
        return {
            "enabled": getattr(bpy.context.scene, 'blendermcp_use_hyper3d', False),
            "available": True
        }

    # Placeholder methods for PolyHaven integration
    def get_polyhaven_categories(self, asset_type="hdris"):
        """Get PolyHaven categories (placeholder)"""
        return {"categories": [], "asset_type": asset_type}

    def search_polyhaven_assets(self, asset_type="all", categories=None):
        """Search PolyHaven assets (placeholder)"""
        return {"assets": [], "asset_type": asset_type}

    def download_polyhaven_asset(self, asset_id, asset_type, resolution="1k", file_format=None):
        """Download PolyHaven asset (placeholder)"""
        return {"asset_id": asset_id, "downloaded": False, "message": "PolyHaven integration not implemented"}

    def set_texture(self, object_name, texture_id):
        """Set texture on object (placeholder)"""
        return {"object": object_name, "texture_set": False, "message": "Texture setting not implemented"}

    # Placeholder methods for Hyper3D integration
    def create_rodin_job(self, **kwargs):
        """Create Hyper3D Rodin job (placeholder)"""
        return {"job_created": False, "message": "Hyper3D integration not implemented"}

    def poll_rodin_job_status(self, **kwargs):
        """Poll Hyper3D job status (placeholder)"""
        return {"status": "not_implemented", "message": "Hyper3D integration not implemented"}

    def import_generated_asset(self, **kwargs):
        """Import generated Hyper3D asset (placeholder)"""
        return {"imported": False, "message": "Hyper3D integration not implemented"}

# UI Panel
class BLENDERMCP_PT_main_panel(bpy.types.Panel):
    bl_label = "BlenderMCP"
    bl_idname = "BLENDERMCP_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'BlenderMCP'

    def draw(self, context):
        layout = self.layout
        
        # Server status
        if hasattr(context.scene, 'blendermcp_server') and context.scene.blendermcp_server:
            layout.label(text="Status: Connected", icon='CONNECTED')
            layout.operator("blendermcp.disconnect", text="Disconnect from Claude")
        else:
            layout.label(text="Status: Disconnected", icon='DISCLOSURE_TRI_DOWN')
            layout.operator("blendermcp.connect", text="Connect to Claude")
        
        # Integration options
        layout.separator()
        layout.label(text="Integrations:")
        
        # PolyHaven integration
        layout.prop(context.scene, "blendermcp_use_polyhaven", text="Poly Haven")
        
        # Hyper3D integration  
        layout.prop(context.scene, "blendermcp_use_hyper3d", text="Hyper3D Rodin")

# Operators
class BLENDERMCP_OT_connect(bpy.types.Operator):
    bl_idname = "blendermcp.connect"
    bl_label = "Connect to Claude"
    
    def execute(self, context):
        if not hasattr(context.scene, 'blendermcp_server') or not context.scene.blendermcp_server:
            context.scene.blendermcp_server = BlenderMCPServer()
            context.scene.blendermcp_server.start()
            self.report({'INFO'}, "Connected to Claude")
        else:
            self.report({'WARNING'}, "Already connected")
        return {'FINISHED'}

class BLENDERMCP_OT_disconnect(bpy.types.Operator):
    bl_idname = "blendermcp.disconnect"
    bl_label = "Disconnect from Claude"
    
    def execute(self, context):
        if hasattr(context.scene, 'blendermcp_server') and context.scene.blendermcp_server:
            context.scene.blendermcp_server.stop()
            context.scene.blendermcp_server = None
            self.report({'INFO'}, "Disconnected from Claude")
        else:
            self.report({'WARNING'}, "Not connected")
        return {'FINISHED'}

# Properties
def register_properties():
    bpy.types.Scene.blendermcp_server = bpy.props.PointerProperty(type=BlenderMCPServer)
    bpy.types.Scene.blendermcp_use_polyhaven = bpy.props.BoolProperty(
        name="Use Poly Haven",
        description="Enable Poly Haven asset integration",
        default=False
    )
    bpy.types.Scene.blendermcp_use_hyper3d = bpy.props.BoolProperty(
        name="Use Hyper3D Rodin",
        description="Enable Hyper3D Rodin AI model generation",
        default=False
    )

def unregister_properties():
    del bpy.types.Scene.blendermcp_server
    del bpy.types.Scene.blendermcp_use_polyhaven
    del bpy.types.Scene.blendermcp_use_hyper3d

# Registration
classes = [
    BLENDERMCP_PT_main_panel,
    BLENDERMCP_OT_connect,
    BLENDERMCP_OT_disconnect,
]

def register():
    register_properties()
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    # Stop server if running
    if hasattr(bpy.context.scene, 'blendermcp_server') and bpy.context.scene.blendermcp_server:
        bpy.context.scene.blendermcp_server.stop()
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    unregister_properties()

if __name__ == "__main__":
    register()