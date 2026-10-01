import os
import re

cflib_dir = "/usr/local/lib/python3.10/dist-packages/cflib"

def patch_file(filepath, patch_func):
    with open(filepath, "r") as f:
        content = f.read()
    new_content = patch_func(content)
    if new_content != content:
        with open(filepath, "w") as f:
            f.write(new_content)
        print(f"Patched {filepath}")
    else:
        print(f"No changes made to {filepath} (already patched or pattern not found)")

def patch_udpdriver(content):
    # Change Exception as e: ... break -> continue for ConnectionRefusedError
    target = """            except Exception as e:
                self.link_error_callback("Error communicating with the Crazyflie\\nException:" + str(e))
                break"""
    
    replacement = """            except ConnectionRefusedError:
                # Ignore ICMP port unreachable, crazysim might not be up yet
                continue
            except Exception as e:
                self.link_error_callback("Error communicating with the Crazyflie\\nException:" + str(e))
                break"""
    
    content = content.replace(target, replacement)

    # Change Exception in send_packet to ignore ConnectionRefusedError
    target_send = """        except Exception as e:
            if self.link_error_callback:
                self.link_error_callback(
                    'UdpDriver: Could not send packet to Crazyflie\\n'
                    'Exception: %s' % e)"""

    replacement_send = """        except ConnectionRefusedError:
            pass
        except Exception as e:
            if self.link_error_callback:
                self.link_error_callback(
                    'UdpDriver: Could not send packet to Crazyflie\\n'
                    'Exception: %s' % e)"""

    content = content.replace(target_send, replacement_send)
    
    # Increase socket buffer size
    target2 = "self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)"
    replacement2 = """self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 2000000)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 2000000)"""
        
    return content.replace(target2, replacement2)

def patch_init(content):
    # Remove _get_toc() bypass
    target = """        def _get_toc():
            \"\"\"Get TOC bypass\"\"\"
            self.link.receive_packet = lambda wait=0: None # dummy
            self._fetch_param_toc(None, None)"""
            
    replacement = """        def _get_toc():
            self._param_updater = ParamUpdater(self, self._param_toc,
                                               self._fetch_param_toc)
            self._param_updater.refresh()"""
            
    return content.replace(target, replacement)

def patch_joystick(content):
    target = "self.js.open(self.joyID)"
    replacement = """try:
                    self.js.open(self.joyID)
                except Exception:
                    self.joyID = None
                    print('Warning: Failed to open joystick device. Continuing without joystick.')"""
    return content.replace(target, replacement)

def patch_console(content):
    return content.replace("packet.data.decode('UTF-8')", "packet.data.decode('UTF-8', errors='replace')")

def patch_server(content):
    target = """    def _connection_failed(self, link_uri, msg):
        self.get_logger().info(f'[{self.cf_dict[link_uri]}] connection Failed')
        self.swarm.close_links()"""
    replacement = """    def _connection_failed(self, link_uri, msg):
        self.get_logger().warn(f'[{self.cf_dict[link_uri]}] connection Failed: {msg} (skipping)')"""
    return content.replace(target, replacement)

def patch_crazyradio(content):
    target = "        self.dev.set_configuration(1)"
    replacement = """        try:
            self.dev.set_configuration(1)
        except Exception:
            pass"""
    return content.replace(target, replacement)

if __name__ == "__main__":
    patch_file(os.path.join(cflib_dir, "crtp/udpdriver.py"), patch_udpdriver)
    patch_file(os.path.join(cflib_dir, "crazyflie/__init__.py"), patch_init)
    console_file = os.path.join(cflib_dir, "crazyflie/console.py")
    if os.path.exists(console_file):
        patch_file(console_file, patch_console)
    radio_file = os.path.join(cflib_dir, "drivers/crazyradio.py")
    if os.path.exists(radio_file):
        patch_file(radio_file, patch_crazyradio)
    
    server_file = "/ros2_ws/src/crazyswarm2/crazyflie_server_py/crazyflie_server_py/crazyflie_server.py"
    if os.path.exists(server_file):
        patch_file(server_file, patch_server)

    joystick_file = "/ros2_ws/src/crazyswarm2/crazyflie_py/crazyflie_py/genericJoystick.py"
    if os.path.exists(joystick_file):
        patch_file(joystick_file, patch_joystick)
