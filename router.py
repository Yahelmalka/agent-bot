import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()  # קורא את קובץ ה-.env
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

CATEGORIES = ["architect", "builder", "debugger", "external_agent", "unclear"]

def classify_message(text):
    prompt = f"""את/ה מסווג/ת הודעות למערכת ניהול סוכני AI.
קטגוריות אפשריות: {', '.join(CATEGORIES)}

architect = תכנון/עיצוב ארכיטקטורה של תוכנה
builder = בקשה לבנות/לכתוב קוד
debugger = בקשה לתקן באג/שגיאה
external_agent = משימה שדורשת כלי חיצוני (OpenClaw, Grok Bot, Instinct)
unclear = לא ברור מספיק

הודעה: "{text}"

החזר/החזירי אך ורק את שם הקטגוריה, בלי שום טקסט נוסף."""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    category = response.choices[0].message.content.strip().lower()
    return category if category in CATEGORIES else "unclear"