import os
import json
import requests
import pypdf
from io import BytesIO
from flask import Flask, request
from dotenv import load_dotenv
from agents import run_agent_system

load_dotenv()

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")

WHATSAPP_STATE_FILE = "/data/whatsapp_state.json"

AGENT_ICONS = {
    "Architect": "🏗️ *ארכיטקט*",
    "Builder": "💻 *בילדר*",
    "Debugger": "🐛 *דיבאגר*",
    "ExternalAgent": "🔌 *סוכן חיצוני*",
    "General": "💬 *עוזר כללי*",
}

app = Flask(__name__)


def load_whatsapp_state():
    if os.path.exists(WHATSAPP_STATE_FILE):
        with open(WHATSAPP_STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_whatsapp_state():
    with open(WHATSAPP_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(WHATSAPP_STATE, f, ensure_ascii=False)


WHATSAPP_STATE = load_whatsapp_state()


def get_state(phone_number):
    state = WHATSAPP_STATE.setdefault(
        phone_number,
        {"name": None, "history": [], "awaiting_name": True, "asked_name": False}
    )
    save_whatsapp_state()
    return state


def format_response(agent_name, text):
    icon = AGENT_ICONS.get(agent_name, "🤖 *תשובה*")
    return f"{icon}\n\n{text}"


def extract_pdf_text(media_url):
    response = requests.get(media_url, auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN))
    reader = pypdf.PdfReader(BytesIO(response.content))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def build_twiml_response(text):
    escaped = (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    return f'<?xml version="1.0" encoding="UTF-8"?><Response><Message>{escaped}</Message></Response>', 200, {"Content-Type": "text/xml"}


@app.route("/whatsapp", methods=["POST"])
def whatsapp_webhook():
    from_number = request.form.get("From", "")
    body = request.form.get("Body", "").strip()
    num_media = int(request.form.get("NumMedia", 0))

    state = get_state(from_number)

    if state["awaiting_name"]:
        if not state["asked_name"]:
            state["asked_name"] = True
            save_whatsapp_state()
            return build_twiml_response("שלום! 👋 לפני שנתחיל — איך קוראים לך?")

        state["name"] = body
        state["awaiting_name"] = False
        save_whatsapp_state()
        return build_twiml_response(f"נעים להכיר, {state['name']}! 😊 במה אפשר לעזור?")

    if num_media > 0:
        media_url = request.form.get("MediaUrl0", "")
        content_type = request.form.get("MediaContentType0", "")

        if "pdf" not in content_type.lower():
            return build_twiml_response("כרגע אני יודעת לקרוא רק קבצי PDF 📄")

        extracted_text = extract_pdf_text(media_url)
        caption = body or "תעביר את הקובץ הזה לסוכן המתאים ועזור לי איתו"
        combined_text = f"{caption}\n\n--- תוכן הקובץ ---\n{extracted_text}"

        result_text, agent_name = run_agent_system(combined_text, state["history"], state["name"])
        state["history"].append({"role": "user", "content": "[קובץ PDF]"})
    else:
        result_text, agent_name = run_agent_system(body, state["history"], state["name"])
        state["history"].append({"role": "user", "content": body})

    state["history"].append({"role": "assistant", "content": result_text})
    save_whatsapp_state()

    return build_twiml_response(format_response(agent_name, result_text))


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)