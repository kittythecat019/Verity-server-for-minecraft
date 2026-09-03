from flask import Flask, request, jsonify
import os

app = Flask(__name__)


@app.get("/")
def home():
    return "Verity AI Server is running!"


@app.post("/test")
def test():
    data = request.get_json(silent=True) or {}

    return jsonify({
        "ok": True,
        "message": data.get("message", "")
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(
        host="0.0.0.0",
        port=port
    )
