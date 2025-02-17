This is a simple remote control application for macOS that allows users to control the mouse cursor, perform mouse clicks, and send keyboard inputs through a web interface. Ensure both devices are on the same network and that the firewall is disabled on the Mac.
```
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
python3 app.py

```
To access the web interface, scan the generated QR code with your mobile device. The URL will contain a secret parameter, which will be used by the server to verify all API and socket calls. This secret is randomly generated and can only be accessed by scanning the QR code.
