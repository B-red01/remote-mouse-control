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
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        :root {
            --primary: #444444;
            --primary-dark: #222222;
            --background: #0a0a0a;
            --card: #1a1a1a;
            --text: #f5f5f5;
            --text-secondary: #aaaaaa;
            --border: #333333;
            --accent: #888888;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            transition: all 0.2s ease;
        }
        
        body {
            background: var(--background);
            color: var(--text);
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: flex-start;
            min-height: 100vh;
            padding: 20px;
        }
        
        h2 {
            font-size: 1.5rem;
            font-weight: 600;
            margin-bottom: 1.5rem;
            color: var(--text);
            text-align: center;
        }
        
        button {
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 0.75rem;
            font-size: 1rem;
            font-weight: 500;
            border: none;
            cursor: pointer;
            background: var(--card);
            color: var(--text);
            border-radius: 0.5rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            transition: all 0.2s ease;
        }
        
        button:hover {
            background: var(--primary);
            transform: translateY(-2px);
        }
        
        button:active {
            transform: translateY(0);
            background: var(--primary-dark);
        }
        
        .section {
            background: var(--card);
            border-radius: 0.75rem;
            padding: 1rem;
            margin-bottom: 1.5rem;
            width: 100%;
            max-width: 480px;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
            border: 1px solid var(--border);
        }
        
        .section-title {
            font-size: 1rem;
            font-weight: 600;
            margin-bottom: 0.75rem;
            color: var(--text-secondary);
            display: flex;
            align-items: center;
        }
        
        .section-title i {
            margin-right: 0.5rem;
        }
        
        .trackpad {
            width: 100%;
            aspect-ratio: 4/3; /* Larger trackpad */
            background: var(--background);
            border: 1px solid var(--border);
            border-radius: 0.5rem;
            display: flex;
            align-items: center;
            justify-content: center;
            user-select: none;
            touch-action: none;
            position: relative;
            overflow: hidden;
        }
        
        .trackpad::after {
            content: '';
            position: absolute;
            width: 100%;
            height: 100%;
            background: radial-gradient(circle, transparent 60%, var(--background) 100%);
            pointer-events: none;
        }
        
        .trackpad-text {
            color: var(--text-secondary);
            font-size: 0.875rem;
            opacity: 0.6;
            pointer-events: none;
        }
        
        .button-group {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 0.75rem;
            width: 100%;
        }
        
        .control-button {
            width: 100%;
            height: 3.5rem;
        }
        
        .playback-controls {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 0.75rem;
        }
        
        input {
            background: var(--background);
            color: var(--text);
            border: 1px solid var(--border);
            padding: 0.75rem;
            font-size: 1rem;
            border-radius: 0.5rem;
            width: 100%;
            outline: none;
        }
        
        input:focus {
            border-color: var(--accent);
            box-shadow: 0 0 0 2px rgba(100, 100, 100, 0.2);
        }
        
        /* Cursor visualization */
        .cursor-visual {
            width: 12px;
            height: 12px;
            background-color: var(--accent);
            border-radius: 50%;
            position: absolute;
            transform: translate(-50%, -50%);
            opacity: 0;
            pointer-events: none;
        }
        
        /* Make trackpad section larger */
        .trackpad-section {
            max-width: 560px;
        }
        
        @media (max-width: 480px) {
            .section {
                padding: 0.75rem;
            }
            
            button {
                padding: 0.5rem;
            }
        }
    </style>
</head>

<body>
    <h2>Remote Cursor Control</h2>
    
    <div class="section trackpad-section">
        <div class="section-title"><i class="fas fa-mouse-pointer"></i> Trackpad</div>
        <div id="trackpad" class="trackpad">
            <div class="cursor-visual" id="cursorVisual"></div>
            <span class="trackpad-text">Swipe to move | Tap to click | Double tap for right click</span>
        </div>
    </div>
    
    <div class="section">
        <div class="section-title"><i class="fas fa-arrow-up"></i> Scrolling</div>
        <div class="button-group">
            <button class="control-button" onclick="sendKey('pageup')">
                <i class="fas fa-arrow-up"></i>&nbsp; Page Up
            </button>
            <button class="control-button" onclick="sendKey('pagedown')">
                <i class="fas fa-arrow-down"></i>&nbsp; Page Down
            </button>
        </div>
    </div>
    
    <div class="section">
        <div class="section-title"><i class="fas fa-play"></i> Media Controls</div>
        <div class="playback-controls">
            <button class="control-button" onclick="sendKey('rewind')">
                <i class="fas fa-backward"></i>&nbsp; Rewind 5s
            </button>
            <button class="control-button" onclick="sendKey('forward')">
                <i class="fas fa-forward"></i>&nbsp; Forward 5s
            </button>
        </div>
    </div>
    
    <div class="section">
        <div class="section-title"><i class="fas fa-keyboard"></i> Keyboard Input</div>
        <input 
            type="text" 
            id="keyboardInput" 
            placeholder="Type here and press Enter to send..." 
            autofocus 
        />
    </div>
    
    <script>
        const socket = io();
        const inputField = document.getElementById("keyboardInput");
        const trackpad = document.getElementById("trackpad");
        const cursorVisual = document.getElementById("cursorVisual");
        
        // Smooth movement variables
        let lastX = 0, lastY = 0;
        let velocityX = 0, velocityY = 0;
        const friction = 0.8;
        const sensitivity = 1.5;
        let isMoving = false;
        let requestId = null;
        
        // Animation for smooth cursor
        function animateCursor() {
            if (Math.abs(velocityX) > 0.1 || Math.abs(velocityY) > 0.1) {
                // Apply friction
                velocityX *= friction;
                velocityY *= friction;
                
                // Move cursor with velocity
                socket.emit("move_cursor", { 
                    deltaX: velocityX, 
                    deltaY: velocityY, 
                    password: storedPassword 
                });
                
                requestId = requestAnimationFrame(animateCursor);
            } else {
                isMoving = false;
                velocityX = 0;
                velocityY = 0;
            }
        }
        
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
                headers: { 
                    "Content-Type": "application/json", 
                    "Authorization": storedPassword 
                },
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

        let lastTap = 0;
        let touchStartX = 0, touchStartY = 0;
        let isDragging = false;

        // Touch handling
        trackpad.addEventListener("touchstart", function (event) {
            event.preventDefault();
            
            let touch = event.touches[0];
            touchStartX = touch.clientX;
            touchStartY = touch.clientY;
            
            // Show visual feedback
            cursorVisual.style.opacity = "0.5";
            cursorVisual.style.left = `${touch.clientX}px`;
            cursorVisual.style.top = `${touch.clientY}px`;
            
            isDragging = false;
            isMoving = false;
            
            if (requestId) {
                cancelAnimationFrame(requestId);
            }
            
            velocityX = 0;
            velocityY = 0;
        });

        trackpad.addEventListener("touchmove", function (event) {
            event.preventDefault();
            let touch = event.touches[0];
            let deltaX = (touch.clientX - touchStartX) * sensitivity;
            let deltaY = (touch.clientY - touchStartY) * sensitivity;
            
            // Update cursor visual
            cursorVisual.style.left = `${touch.clientX}px`;
            cursorVisual.style.top = `${touch.clientY}px`;

            if (Math.abs(deltaX) > 3 || Math.abs(deltaY) > 3) {
                isDragging = true;
                
                // Update velocity
                velocityX = deltaX;
                velocityY = deltaY;
                
                if (!isMoving) {
                    isMoving = true;
                    animateCursor();
                }
                
                touchStartX = touch.clientX;
                touchStartY = touch.clientY;
            }
        });

        trackpad.addEventListener("touchend", function (event) {
            // Fade out the cursor visual
            cursorVisual.style.opacity = "0";
            
            if (isDragging) {
                console.log("[INFO] Drag detected");
                // Let inertia continue
                return;
            }
            
            let currentTime = new Date().getTime();
            let tapLength = currentTime - lastTap;

            if (tapLength < 300 && tapLength > 0) {
                console.log("[INFO] Double Click");
                sendClick('right');
            } else {
                setTimeout(() => {
                    if (new Date().getTime() - lastTap >= 300) {
                        console.log("[INFO] Single Click");
                        sendClick('left');
                    }
                }, 300);
            }

            lastTap = currentTime;
        });

        function sendClick(button) {
            // Add visual feedback
            cursorVisual.style.transform = "translate(-50%, -50%) scale(1.5)";
            setTimeout(() => {
                cursorVisual.style.transform = "translate(-50%, -50%) scale(1)";
            }, 150);
            
            fetch("/click", {
                method: "POST",
                headers: { 
                    "Content-Type": "application/json", 
                    "Authorization": storedPassword 
                },
                body: JSON.stringify({ button: button }),
            })
            .then(response => response.json())
            .then(data => console.log("[INFO] Clicked:", data.clicked));
        }
        
        function sendKey(key) {
            console.log("[INFO] Key Pressed:", key);
            fetch("/keypress", {
                method: "POST",
                headers: { 
                    "Content-Type": "application/json", 
                    "Authorization": storedPassword 
                },
                body: JSON.stringify({ key: key }),
            });
        }

        inputField.addEventListener("input", function (event) {
            let key = event.data;
            if (key) {
                console.log("[INFO] Letter Typed:", key);
                sendKey(key.toLowerCase());
                // Clear the input field immediately after sending the key
                setTimeout(() => {
                    inputField.value = "";
                }, 100);
            }
        });
    
        inputField.addEventListener("keydown", function (event) {
            if (event.key === "Enter") {
                event.preventDefault();
                console.log("[INFO] Special Key: Enter");
                sendKey("Enter");
                inputField.value = ""; // Clear after Enter
            } else if (event.key === "Backspace") {
                event.preventDefault();
                console.log("[INFO] Special Key: Backspace");
                sendKey("Backspace");
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
        elif key == "rewind":
            keyboard.press(Key.left)
            keyboard.release(Key.left)
        elif key == "forward":
            keyboard.press(Key.right)
            keyboard.release(Key.right)
        else:
            keyboard.type(key)

    return jsonify({"status": "success", "key": key})

@socketio.on("move_cursor")
def move_cursor(data):
    password = data.get("password")
    if password != SECRET_PASSWORD:
        print(f"[INFO] unauthorized")
        disconnect()
        return
    
    delta_x = data.get("deltaX", 0)
    delta_y = data.get("deltaY", 0)
    
    # Move mouse relative to current position
    pyautogui.move(delta_x, delta_y)
    print(f"Moved: {delta_x}, {delta_y}")

if __name__ == "__main__":
    generate_qr()
    socketio.run(app, host="0.0.0.0", port=PORT)