from flask import Flask, request, jsonify, render_template_string
from flask_socketio import SocketIO, disconnect
from pynput.mouse import Controller as MouseController, Button
from pynput.keyboard import Controller as KeyboardController, Key
import pyautogui
import qrcode
import socket
import os
import secrets

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

mouse = MouseController()
keyboard = KeyboardController()

MOVE_AMOUNT = 25
SECRET_PASSWORD = secrets.token_urlsafe(32)  
PORT = 5004

def validate_password():
    password = request.headers.get("Authorization") 
    print(f"[INFO] password {password}")
    if password != SECRET_PASSWORD:
        print(f"[INFO] unauthorized")
        return jsonify({"status": "error", "message": "Unauthorized"}), 401


def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"  # Fallback if there's an issue
    finally:
        s.close()
    return ip

def generate_qr():
    local_ip = get_local_ip()
    url = f"http://{local_ip}:{PORT}/?secret={SECRET_PASSWORD}"
    qr = qrcode.make(url)
    qr.save("qrcode.png")
    print(f"[INFO] Scan this QR code to connect: {url}")
    os.system("open qrcode.png" if os.name == "posix" else "start qrcode.png")

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Remote Cursor</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        body {
            background: #121212;
            color: #ffffff;
            font-family: Arial, sans-serif;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 100vh;
        }
        button {
            width: 100px;
            height: 100px;
            font-size: 24px;
            margin: 10px;
            border: none;
            cursor: pointer;
            background: #1e1e1e;
            color: white;
            border-radius: 10px;
            box-shadow: 0 0 10px rgba(255, 255, 255, 0.2);
            transition: all 0.2s ease-in-out;
        }
        button:hover {
            box-shadow: 0 0 20px rgba(255, 255, 255, 0.4);
        }
        .controls {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 10px;
        }
        .click-buttons {
            margin-top: 20px;
            display: flex;
            gap: 20px;
        }
        input {
            background: #1e1e1e;
            color: white;
            border: 1px solid #ffffff55;
            padding: 10px;
            font-size: 18px;
            border-radius: 5px;
            text-align: center;
            width: 80%;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <h2>Remote Cursor Control</h2>
    <div class="controls">
        <div></div>
        <button onclick="moveCursor('up')">🔼</button>
        <div></div>
        <button onclick="moveCursor('left')">◀️</button>
        <div></div>
        <button onclick="moveCursor('right')">▶️</button>
        <div></div>
        <button onclick="moveCursor('down')">🔽</button>
        <div></div>
    </div>

    <div class="click-buttons">
        <button onclick="sendClick('left')">🖱️ Left Click</button>
        <button onclick="sendClick('right')">🖱️ Right Click</button>
    </div>
    <div class="scroll-buttons">
        <button onclick="sendKey('pageup')">⬆️ Page Up</button>
        <button onclick="sendKey('pagedown')">⬇️ Page Down</button>
    </div>
    
    <div class="keyboard-section">
        <input type="text" id="keyboardInput" placeholder="Type here..." autofocus />
    </div>
    
    <script>
        const socket = io();
        const inputField = document.getElementById("keyboardInput");
        
        function getSecretKey() {
            const urlParams = new URLSearchParams(window.location.search);
            const secret = urlParams.get("secret");
            if (secret) {
                localStorage.setItem("secretKey", secret);
            }
            return localStorage.getItem("secretKey");
        }
        const storedPassword = getSecretKey();
        document.addEventListener("DOMContentLoaded", function () {
            if (!storedPassword) {
                storedPassword = getSecretKey();
            }
            fetch("/validate-password", {
                method: "POST",
                headers: { "Content-Type": "application/json", "Authorization": storedPassword },
            })
            .then(response => response.json())
            .then(data => {
                if (data.status !== "success") {
                    console.log("[ERROR] Invalid password");
                    localStorage.removeItem("secret");
                    window.location.href = "/unauthorized";
                } else {
                    console.log("[INFO] Password is valid!");
                }
            })
            .catch(error => console.error("[ERROR] Validation failed:", error));
        });
        function sendClick(button) {
            fetch("/click", {
                method: "POST",
                headers: { "Content-Type": "application/json" , "Authorization": storedPassword },
                body: JSON.stringify({ button: button }),
            }).then(response => response.json())
              .then(data => console.log("[INFO] Clicked:", data.clicked));
        }
        function sendKey(key) {
            console.log("[INFO] Key Pressed:", key);
            fetch("/keypress", {
                method: "POST",
                headers: { "Content-Type": "application/json" , "Authorization": storedPassword },
                body: JSON.stringify({ key: key }),
            });
        }

        function moveCursor(direction) {
            console.log("[DEBUG] Moving:", direction);
            socket.emit("move_cursor", { direction: direction , password: storedPassword });
        }
    
        inputField.addEventListener("input", function (event) {
            let key = event.data;
            if (key) {
                console.log("[INFO] Letter Typed:", key);
                sendKey(key.toLowerCase());
                setTimeout(() => {
                    inputField.value = "";
                }, 200); 
            }
        });
    
        inputField.addEventListener("keydown", function (event) {
            if (event.key === "Enter" || event.key === "Backspace") {
                event.preventDefault();
                console.log("[INFO] Special Key:", event.key);
                sendKey(event.key);
            }
        });
    </script>
</body>
</html>"""

@app.route("/")
def index():
    return render_template_string(HTML_PAGE)

@app.route("/validate-password", methods=["POST"])
def validate_secret():
    auth = validate_password()
    if auth:
        return auth
    return jsonify({"status": "success", "message": "Valid password"})

### ✅ API for Mouse Clicks (Using pyautogui)
@app.route("/click", methods=["POST"])
def click():
    auth = validate_password()
    if auth:
        return auth
    data = request.json
    click_type = data.get("button")  # "left" or "right"

    if click_type == "left":
        pyautogui.click()
    elif click_type == "right":
        pyautogui.click(button="right")
    
    print(f"[INFO] Mouse Clicked: {click_type}")
    return jsonify({"status": "success", "clicked": click_type})

### ✅ API for Keyboard Input
@app.route("/keypress", methods=["POST"])
def keypress():
    auth = validate_password()
    if auth:
        return auth
    data = request.json
    key = data.get("key")

    if key:
        print(f"[INFO] Key Pressed: {key}")

        if key == "Enter":
            keyboard.press(Key.enter)
            keyboard.release(Key.enter)
        elif key == "Backspace":
            keyboard.press(Key.backspace)
            keyboard.release(Key.backspace)
        elif key == "pageup":
            keyboard.press(Key.page_up)
            keyboard.release(Key.page_up)
        elif key == "pagedown":
            keyboard.press(Key.page_down)
            keyboard.release(Key.page_down)
        else:
            keyboard.type(key)

    return jsonify({"status": "success", "key": key})

### ✅ WebSocket for Real-time Cursor Movement (Using pyautogui)
@socketio.on("move_cursor")
def move_cursor(data):
    password = data.get("password")  # Get password from client
    if password != SECRET_PASSWORD:
        print(f"[INFO] unauthorized")
        disconnect()
        return
    x, y = pyautogui.position()
    direction = data.get("direction", "")

    if direction == "up":
        pyautogui.moveTo(x, y - MOVE_AMOUNT)
    elif direction == "down":
        pyautogui.moveTo(x, y + MOVE_AMOUNT)
    elif direction == "left":
        pyautogui.moveTo(x - MOVE_AMOUNT, y)
    elif direction == "right":
        pyautogui.moveTo(x + MOVE_AMOUNT, y)

    print(f"[INFO] Moved {direction} to {pyautogui.position()}")



if __name__ == "__main__":
    generate_qr()
    socketio.run(app, host="0.0.0.0", port=PORT)