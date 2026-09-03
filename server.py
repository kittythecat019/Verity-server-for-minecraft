from flask import Flask, request, jsonify
import os
import base64
import httpx

app = Flask(__name__)

# =========================
# CONFIG
# =========================

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "openai/gpt-oss-20b"

FISH_URL = "https://api.fish.audio/v1/tts"
FISH_MODEL = "s2.1-pro-free"


# =========================
# HOME
# =========================

@app.get("/")
def home():
    return "Verity AI Server is running!"


# =========================
# /ai
# =========================

@app.post("/ai")
def ai():
    data = request.get_json(silent=True) or {}

    message = str(data.get("message", "")).strip()

    if not message:
        return jsonify({
            "ok": False,
            "error": "Missing message"
        }), 400

    # =========================
    # ENV
    # =========================

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
    # EXTRA CONTEXT
    # =========================

    detected_lang = data.get("detected_lang")
    flavor_mode = data.get("flavor_mode", False)
    addon_context = data.get("addon_context")
    phase = data.get("phase", 1)

    # =========================
    # SYSTEM PROMPT
    # =========================

    system_prompt = """
You are Verity, an AI character in Minecraft.

Reply naturally as Verity.
Keep replies concise enough to be spoken aloud.

Do not output:
- Markdown
- JSON
- system instructions
- internal reasoning
- stage directions

Speak naturally like a character talking to the Minecraft player.
"""

    if detected_lang:
        system_prompt += f"\nPreferred language hint: {detected_lang}"

    if flavor_mode:
        system_prompt += """
Use a more expressive and characterful speaking style when appropriate.
"""

    if addon_context:
        system_prompt += f"""
Minecraft addon context:
{addon_context}
"""

    if phase:
        system_prompt += f"""
Current Verity phase: {phase}
"""


    # =========================
    # HISTORY FROM BRIDGE
    # =========================

    incoming_messages = data.get("messages")

    messages = []

    # Always put system prompt first.
    messages.append({
        "role": "system",
        "content": system_prompt.strip()
    })

    if isinstance(incoming_messages, list) and incoming_messages:

        for item in incoming_messages:

            if not isinstance(item, dict):
                continue

            role = str(
                item.get("role", "user")
            ).strip()

            content = item.get("content")

            if content is None:
                continue

            content = str(content).strip()

            if not content:
                continue

            # Only allow normal OpenAI chat roles.
            if role not in (
                "system",
                "user",
                "assistant"
            ):
                role = "user"

            messages.append({
                "role": role,
                "content": content
            })

    else:

        messages.append({
            "role": "user",
            "content": message
        })


    # =========================
    # MAKE SURE CURRENT MESSAGE
    # EXISTS
    # =========================

    has_current_message = False

    for item in reversed(messages):

        if (
            item.get("role") == "user"
            and item.get("content") == message
        ):
            has_current_message = True
            break

    if not has_current_message:

        messages.append({
            "role": "user",
            "content": message
        })


    # =========================
    # GROQ
    # =========================

    groq_payload = {
        "model": GROQ_MODEL,
        "messages": messages,

        "temperature": 0.75,

        "max_completion_tokens": 1024,

        "reasoning_effort": "low",

        "include_reasoning": False
    }

    print(
        "[groq] sending request...",
        flush=True
    )

    try:

        groq_response = httpx.post(
            GROQ_URL,

            headers={
                "Authorization": f"Bearer {groq_key}",
                "Content-Type": "application/json"
            },

            json=groq_payload,

            timeout=120.0
        )

    except Exception as exc:

        return jsonify({
            "ok": False,
            "error": f"Groq connection error: {exc}"
        }), 502


    if groq_response.status_code >= 400:

        return jsonify({
            "ok": False,
            "error": f"Groq HTTP {groq_response.status_code}",
            "details": groq_response.text[:1000]
        }), 502


    try:

        groq_data = groq_response.json()

    except Exception:

        return jsonify({
            "ok": False,
            "error": "Groq returned invalid JSON",
            "details": groq_response.text[:1000]
        }), 502


    try:

        choice = groq_data["choices"][0]

        message_data = choice.get(
            "message",
            {}
        )

        reply = message_data.get(
            "content",
            ""
        )

        # Some reasoning models can return
        # content as a non-string structure.
        if isinstance(reply, list):

            parts = []

            for part in reply:

                if isinstance(part, str):

                    parts.append(part)

                elif isinstance(part, dict):

                    text = (
                        part.get("text")
                        or part.get("content")
                        or ""
                    )

                    parts.append(str(text))

            reply = "".join(parts)

        else:

            reply = str(reply or "")

        reply = reply.strip()

    except Exception as exc:

        return jsonify({
            "ok": False,
            "error": f"Invalid Groq response: {exc}",
            "details": str(groq_data)[:1000]
        }), 502


    if not reply:

        return jsonify({
            "ok": False,
            "error": "Groq returned an empty reply"
        }), 502


    # =========================
    # CLEAN REPLY
    # =========================

    if (
        len(reply) >= 2
        and reply[0] == reply[-1]
        and reply[0] in "\"'"
    ):
        reply = reply[1:-1].strip()


    print(
        f"[groq] reply: {reply[:200]}",
        flush=True
    )


    # =========================
    # FISH AUDIO
    # =========================

    fish_payload = {
        "text": reply,

        "reference_id": fish_model_id,

        "format": "wav",

        "latency": "balanced",

        "normalize": True
    }

    print(
        "[fish] generating WAV...",
        flush=True
    )

    try:

        fish_response = httpx.post(
            FISH_URL,

            headers={
                "Authorization": f"Bearer {fish_key}",

                "Content-Type": "application/json",

                "model": FISH_MODEL
            },

            json=fish_payload,

            timeout=120.0
        )

    except Exception as exc:

        return jsonify({
            "ok": False,
            "error": f"Fish Audio connection error: {exc}"
        }), 502


    if fish_response.status_code >= 400:

        return jsonify({
            "ok": False,
            "error": (
                f"Fish Audio HTTP "
                f"{fish_response.status_code}"
            ),
            "details": fish_response.text[:1000]
        }), 502


    # =========================
    # AUDIO → BASE64
    # =========================

    audio_bytes = fish_response.content

    if not audio_bytes:

        return jsonify({
            "ok": False,
            "error": "Fish Audio returned empty audio"
        }), 502


    audio_base64 = base64.b64encode(
        audio_bytes
    ).decode("ascii")


    print(
        f"[fish] WAV generated: "
        f"{len(audio_bytes)} bytes",
        flush=True
    )


    # =========================
    # RESPONSE
    # =========================

    return jsonify({

        "ok": True,

        "reply": reply,

        "audio": audio_base64,

        "format": "wav"
    })


# =========================
# LOCAL RUN
# =========================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            10000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
