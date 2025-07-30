import webbrowser
from waitress import serve
from app import app

# --- Configuration ---
HOST = '127.0.0.1'
PORT = 8000
URL = f"http://{HOST}:{PORT}"

if __name__ == "__main__":
    # --- Open the browser ---
    # This will open the URL in a new tab of the default browser.
    webbrowser.open_new(URL)

    # --- Start the Waitress server ---
    # This is a production-ready server that is more robust than Flask's
    # built-in development server.
    print(f"Starting server at {URL}")
    serve(app, host=HOST, port=PORT)
