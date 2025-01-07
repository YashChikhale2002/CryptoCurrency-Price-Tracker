import websocket
import json
import threading

latest_prices = {}

allowed_symbols = ["dogeusdt"]

def on_message(ws, message):
    try:
        data = json.loads(message)
        symbol = data["s"].lower()
        price = float(data["c"])
        latest_prices[symbol.upper()] = price
        print(f"{symbol.upper()}: {price}")
    except Exception as e:
        print(f"Error processing message: {e}, message: {message}")

def on_error(ws, error):
    print(error)

def on_close(ws):
    print("### closed ###")

def on_open(ws):
    print("### opened ###")
    params = [f"{symbol}@ticker" for symbol in allowed_symbols]
    subscribe_message = {"method": "SUBSCRIBE", "params": params, "id": 1}
    ws.send(json.dumps(subscribe_message))

def start_websocket():
    websocket.enableTrace(True)
    ws = websocket.WebSocketApp(
        "wss://stream.binance.com:9443/ws",
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    ws.on_open = on_open
    ws.run_forever()

ws_thread = threading.Thread(target=start_websocket)
ws_thread.daemon = True
ws_thread.start()

try:
    while True:
        pass
except KeyboardInterrupt:
    print("Interrupted")
