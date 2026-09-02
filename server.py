import os
import requests

from flask import Flask
from flask_sock import Sock

app = Flask(__name__)
sock = Sock(app)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
FISH_API_KEY = os.environ.get("FISH_API_KEY")
FISH_MODEL_ID = os.environ.get("FISH_MODEL_ID")

@app.route("/")
def home():
    return "Verity server is running"


@sock.route("/verity")
def verity(ws):

    while True:

        data = ws.receive()

        if data is None:
            break

        print("Received:", data)

        # TODO:
        # Đây là nơi xử lý packet của Verity.
        # Sau khi xác định protocol của addon,
        # phần này sẽ chuyển chat -> Groq -> FishAudio.

        ws.send(data)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port)
