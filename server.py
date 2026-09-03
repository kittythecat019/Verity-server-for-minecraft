from flask import Flask, request, jsonify
import os
import httpx
import base64

app = Flask(__name__)

# =========================
# GROQ
# =========================

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "openai/gpt-oss-20b"


# =========================
# FISH AUDIO
# =========================

FISH_URL = "https://api.fish.audio/v1/tts"


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

    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    fish_key = os.getenv("FISH_API_KEY", "").strip()
    fish_model_id = os.getenv("FISH_MODEL_ID", "").strip()

    if not groq_key:
        return jsonify({
            "ok": False,
            "error": "GROQ_API_KEY is not configured"
        }), 500

    if not fish_key:
        return jsonify({
            "ok": False,
            "error": "FISH_API_KEY is not configured"
        }), 500

    if not fish_model_id:
        return jsonify({
            "ok": False,
            "error": "FISH_MODEL_ID is not configured"
        }), 500

    # =========================
    # 1. GROQ
    # =========================

    groq_payload = {
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
        groq_response = httpx.post(
            GROQ_URL,
            headers={
                "Authorization": f"Bearer {groq_key}",
                "Content-Type": "application/json"
            },
            json=groq_payload,
            timeout=90
        )

        if groq_response.status_code >= 400:
            return jsonify({
                "ok": False,
                "error": f"Groq HTTP {groq_response.status_code}",
                "details": groq_response.text[:500]
            }), 502

        groq_data = groq_response.json()

        reply = (
            groq_data
            .get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )

        reply = reply.strip()

        if not reply:
            return jsonify({
                "ok": False,
                "error": "Groq returned an empty reply"
            }), 502

    except Exception as e:
        return jsonify({
            "ok": False,
            "error": f"Groq error: {str(e)}"
        }), 500


    # =========================
    # 2. FISH AUDIO
    # =========================

    fish_payload = {
        "text": reply,
        "reference_id": fish_model_id,
        "format": "mp3",
        "latency": "balanced",
        "normalize": True
    }

    try:
        fish_response = httpx.post(
            FISH_URL,
            headers={
                "Authorization": f"Bearer {fish_key}",
                "Content-Type": "application/json",
                "model": "s2.1-pro-free"
            },
            json=fish_payload,
            timeout=90
        )

        if fish_response.status_code >= 400:
            return jsonify({
                "ok": False,
                "error": f"Fish Audio HTTP {fish_response.status_code}",
                "details": fish_response.text[:500]
            }), 502

        audio_base64 = base64.b64encode(
            fish_response.content
        ).decode("ascii")

    except Exception as e:
        return jsonify({
            "ok": False,
            "error": f"Fish Audio error: {str(e)}"
        }), 500


    # =========================
    # 3. RETURN
    # =========================

    return jsonify({
        "ok": True,
        "reply": reply,
        "audio": audio_base64,
        "format": "mp3"
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))

    app.run(
        host="0.0.0.0",
        port=port
    )
