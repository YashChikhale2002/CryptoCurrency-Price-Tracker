from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import threading
import json
import websocket

# The line `app = Flask(__name__)` in the provided Python code is creating a Flask application
# instance.
app = Flask(__name__)
socketio = SocketIO(app)  # Initialize Flask-SocketIO

# Shared dictionary for real-time prices
latest_prices = {}
allowed_symbols = ["dogeusdt", 'btcusdt','ethusdt', 'bnbusdt']

# WebSocket message handler
# WebSocket message handler
def on_message(ws, message):
    try:
        data = json.loads(message)
        symbol = data["s"].lower()
        price = float(data["c"])  # Current price
        volume = float(data["v"])  # 24h trading volume
        price_change = float(data["P"])  # 24h price change percentage

        latest_prices[symbol.upper()] = {
            "price": price,
            "volume": volume,
            "change": price_change
        }

        # Emit the updated price, volume, and change to all connected clients
        socketio.emit("price_update", {
            "symbol": symbol.upper(),
            "price": price,
            "volume": volume,
            "change": price_change
        })
    except Exception as e:
        print(f"Error processing message: {e}, message: {message}")

# WebSocket error handler
def on_error(ws, error):
    print(error)

# WebSocket close handler
def on_close(ws):
    print("### WebSocket closed ###")

# WebSocket open handler
def on_open(ws):
    print("### WebSocket opened ###")
    params = [f"{symbol}@ticker" for symbol in allowed_symbols]
    subscribe_message = {"method": "SUBSCRIBE", "params": params, "id": 1}
    ws.send(json.dumps(subscribe_message))

# Start WebSocket connection
def start_websocket():
    websocket.enableTrace(True)
    ws = websocket.WebSocketApp(
        "wss://stream.binance.com:9443/ws",
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
    )
    ws.on_open = on_open
    ws.run_forever()

# Start the WebSocket in a separate thread
ws_thread = threading.Thread(target=start_websocket)
ws_thread.daemon = True
ws_thread.start()

# Flask Routes

@app.route("/")
def index():
    return render_template("index.html", allowed_symbols=allowed_symbols)




# Run Flask app with SocketIO
if __name__ == "__main__":
    socketio.run(app, debug=True)
