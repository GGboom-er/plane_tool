import socket
import sys
import json

def send_to_maya(command, port=7001):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client.connect(("127.0.0.1", port))
        # Maya requires code to be ending with a null character or similar for some modes,
        # but for python sourceType, a simple string is usually fine.
        client.sendall(command.encode("utf-8"))
        
        # We might not get a response back easily depending on how the port is configured,
        # but we try to receive a small buffer.
        client.settimeout(2.0)
        try:
            response = client.recv(4096)
            return response.decode("utf-8")
        except socket.timeout:
            return "Command sent (timeout waiting for response)"
    except Exception as e:
        return f"Error: {e}"
    finally:
        client.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python maya_remote_bridge.py \"cmds.sphere()\"")
        sys.exit(1)
    
    cmd_text = sys.argv[1]
    res = send_to_maya(cmd_text)
    print(res)
