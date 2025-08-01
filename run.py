import webbrowser
from waitress import serve
from app import app

# --- Configuration ---
HOST = '0.0.0.0'  # <-- This allows access from other devices on the network
PORT = 8000

# Get local IP for browser opening
import socket
local_ip = socket.gethostbyname(socket.gethostname())
URL = f"http://{local_ip}:{PORT}"

if __name__ == "__main__":
    # --- Open the browser on the local machine ---
    webbrowser.open_new(URL)

    # --- Start the Waitress server ---
    print(f"Starting server at {URL}")
    serve(app, host=HOST, port=PORT)
