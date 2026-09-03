from flask import Flask, request, jsonify
import os
import httpx

app = Flask(__name__)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "openai/gpt-oss-20b"


@app.get("/")
def home():
    return "Verity AI Server is running!"


@app.post("/ai")
def ai():
    data = request.get_json(silent=True) or {}
    message = str(data.get("message", "")).strip()

    if not message:
        return jsonify({
            "ok": False,
            "error": "Missing message"
        }), 400

    api_key = os.getenv("GROQ_API_KEY", "").strip()

    if not api_key:
        return jsonify({
            "ok": False,
            "error": "GROQ_API_KEY is not configured"
        }), 500

    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are Verity, an AI character in Minecraft. "
                    "Reply naturally and concisely."
                )
            },
            {
                "role": "user",
                "content": message
            }
        ],
        "temperature": 0.75,
        "max_completion_tokens": 768,
        "reasoning_effort": "low",
        "include_reasoning": False
    }

    try:
        response = httpx.post(
            GROQ_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=90
        )

        if response.status_code >= 400:
            return jsonify({
                "ok": False,
                "error": f"Groq HTTP {response.status_code}",
                "details": response.text[:500]
            }), 502

        result = response.json()

        reply = (
            result
            .get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )

        return jsonify({
            "ok": True,
            "reply": reply.strip()
        })

    except Exception as e:
        return jsonify({
            "ok": False,
            "error": str(e)
        }), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
