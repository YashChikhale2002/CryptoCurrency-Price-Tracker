from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_socketio import SocketIO, emit
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import threading
import json
import websocket
import requests
import time
import os

# Load environment variables from .env file
load_dotenv()
COINMARKETCAP_API_KEY = os.getenv("COINMARKETCAP_API_KEY")

if not COINMARKETCAP_API_KEY:
    raise ValueError("API key not found. Please check your .env file.")

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Required for session handling
socketio = SocketIO(app)

allowed_symbols = ["dogeusdt", "btcusdt", "ethusdt", "bnbusdt", "xrpusdt", "solusdt"]

latest_prices = {}

# Cache to store currency conversion rates with expiry time
cache = {}
cache_expiry = 300  # 5 minutes cache expiry

# Database initialization
def init_db():
    with sqlite3.connect("users.db") as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
            """
        )
        conn.commit()

init_db()

def get_conversion_rate(from_currency, to_currency):
    """
    Fetch the conversion rate from CoinMarketCap API and cache it.
    """
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

def on_message(ws, message):
    """
    WebSocket message handler for real-time price updates.
    """
    try:
        data = json.loads(message)
        symbol = data["s"].lower()
        price = float(data["c"])
        volume = float(data["v"])
        price_change = float(data["P"])

        # Update latest prices
        latest_prices[symbol.upper()] = {
            "price": price,
            "volume": volume,
            "change": price_change,
        }

        # Emit updated price via Socket.io to frontend
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
    """
    WebSocket open handler, subscribes to the symbols.
    """
    print("### WebSocket opened ###")
    params = [f"{symbol}@ticker" for symbol in allowed_symbols]
    subscribe_message = {"method": "SUBSCRIBE", "params": params, "id": 1}
    ws.send(json.dumps(subscribe_message))

def start_websocket():
    """
    Start the WebSocket connection to Binance for real-time data.
    """
    websocket.enableTrace(True)
    ws = websocket.WebSocketApp(
        "wss://stream.binance.com:9443/ws",
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
    )
    ws.on_open = on_open
    ws.run_forever()

# Run WebSocket connection in a separate thread
ws_thread = threading.Thread(target=start_websocket)
ws_thread.daemon = True
ws_thread.start()

@app.route("/convert", methods=["GET"])
def convert_currency():
    """
    Converts a given amount from one currency to another.
    """
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

@app.route("/login", methods=["GET", "POST"])
def login():
    """
    Login route with session handling.
    """
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        with sqlite3.connect("users.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT password FROM users WHERE username = ?", (username,))
            user = cursor.fetchone()

        if user and check_password_hash(user[0], password):
            session["username"] = username
            return redirect(url_for("index"))
        else:
            return render_template("login.html", error="Invalid credentials")

    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    """
    User registration route.
    """
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        hashed_password = generate_password_hash(password)

        try:
            with sqlite3.connect("users.db") as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
                conn.commit()
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            return render_template("register.html", error="Username already exists")

    return render_template("register.html")

@app.route("/")
def index():
    """
    Main route to render the homepage.
    """
    if "username" not in session:
        return redirect(url_for("login"))

    return render_template("index.html", allowed_symbols=allowed_symbols, username=session["username"])

@app.route("/logout")
def logout():
    """
    Logout route to clear the session.
    """
    session.pop("username", None)
    return redirect(url_for("login"))

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
