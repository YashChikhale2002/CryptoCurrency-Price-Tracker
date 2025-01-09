from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import threading
import json
import websocket
import requests
import time

app = Flask(__name__)
socketio = SocketIO(app)

# Configuration
COINMARKETCAP_API_KEY = "d2731549-19f8-405a-8017-6df613de03dd"
allowed_symbols = ["dogeusdt", "btcusdt", "ethusdt", "bnbusdt", "xrpusdt", "solusdt"]

# Shared dictionary for real-time prices
latest_prices = {}

# Cache configuration
cache = {}
cache_expiry = 300  # Cache expiry time in seconds (5 minutes)

# Function to get conversion rate with caching
def get_conversion_rate(from_currency, to_currency):
    key = f"{from_currency}_{to_currency}"
    if key in cache and time.time() - cache[key]["timestamp"] < cache_expiry:
        return cache[key]["rate"]

    url = "https://pro-api.coinmarketcap.com/v1/tools/price-conversion"
    headers = {"X-CMC_PRO_API_KEY": COINMARKETCAP_API_KEY}
    params = {"amount": 1, "symbol": from_currency, "convert": to_currency}

    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        rate = response.json()["data"]["quote"][to_currency]["price"]
        cache[key] = {"rate": rate, "timestamp": time.time()}
        return rate
    else:
        raise Exception(f"API Error: {response.text}")

# WebSocket Handlers
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
            "change": price_change,
        }

        socketio.emit(
            "price_update",
            {"symbol": symbol.upper(), "price": price, "volume": volume, "change": price_change},
        )
    except Exception as e:
        print(f"Error processing message: {e}, message: {message}")

def on_error(ws, error):
    print(f"WebSocket Error: {error}")

def on_close(ws):
    print("### WebSocket closed ###")

def on_open(ws):
    print("### WebSocket opened ###")
    params = [f"{symbol}@ticker" for symbol in allowed_symbols]
    subscribe_message = {"method": "SUBSCRIBE", "params": params, "id": 1}
    ws.send(json.dumps(subscribe_message))

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

# Start WebSocket in a separate thread
ws_thread = threading.Thread(target=start_websocket)
ws_thread.daemon = True
ws_thread.start()

# Currency conversion route using CoinMarketCap
@app.route("/convert", methods=["GET"])
def convert_currency():
    try:
        amount = float(request.args.get("amount"))
        from_currency = request.args.get("from", "USD")
        to_currency = request.args.get("to", "USD")

        if from_currency == to_currency:
            return jsonify({"converted": amount})

        rate = get_conversion_rate(from_currency, to_currency)
        converted_amount = amount * rate
        return jsonify({"converted": converted_amount})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/")
def index():
    return render_template("index.html", allowed_symbols=allowed_symbols)

if __name__ == "__main__":
    socketio.run(app, debug=True)
