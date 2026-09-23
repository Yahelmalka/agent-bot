import os
from dotenv import load_dotenv
from openai import OpenAI
from langchain.agents import create_agent
from langchain.tools import tool
from langchain_openai import ChatOpenAI
from rag import search_knowledge
from external_agent_runner import run_external_agent

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
llm = ChatOpenAI(model="gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"), temperature=0.3)


FORMAT_GUIDELINES = """
כללי עיצוב לתשובה — חובה לפעול לפיהם, גם אם זה סותר הרגלים רגילים:
- אסור להשתמש בכותרות עם # או ## — הן לא נתמכות ומוצגות כטקסט גולמי.
- אסור להשתמש בקווי הפרדה כמו --- או ___ או קווים חוזרים בכל צורה.
- להדגשה: כוכבית בודדת בלבד — *כך* (לא כוכביים כפולים).
- להטיה: קו תחתון בודד — _כך_.
- קוד: שלוש גרשיים בלבד, בלי ציון שפה.
- לארגון ויזואלי, משתמשים באימוג'י קצר בתחילת נקודה/פסקה במקום כותרת (למשל 🔧 להסבר טכני, 💡 לטיפ, ⚠️ לאזהרה).
- רשימות: נקודה (•) או מספר ונקודה, לא מקפים.
- פסקאות קצרות עם רווח ביניהן, במקום קווי הפרדה.
"""


def run_agent(system_prompt, user_text):
    full_system_prompt = f"{system_prompt}\n\n{FORMAT_GUIDELINES}"
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": full_system_prompt},
            {"role": "user", "content": user_text}
        ],
        temperature=0.3
    )
    return response.choices[0].message.content


def run_architect(user_text):
    system_prompt = """את/ה ארכיטקט/ית תוכנה מנוסה.
כשמקבלים בקשה, מתכננים ארכיטקטורה: אילו רכיבים צריך, איך הם מתקשרים,
אילו טכנולוגיות מתאימות. תני תשובה מסודרת, לא קוד מלא — רק תכנון."""
    return run_agent(system_prompt, user_text)


def run_builder(user_text):
    system_prompt = """את/ה מפתח/ת תוכנה. כשמקבלים בקשה, כותבים קוד עובד ותמציתי,
עם הסבר קצר לפני הקוד."""
    return run_agent(system_prompt, user_text)


def run_debugger(user_text):
    relevant_docs = search_knowledge(user_text)
    context_text = "\n".join(relevant_docs)

    system_prompt = f"""את/ה מומחה/ית לאיתור באגים. כשמקבלים תיאור בעיה או קוד שגוי,
מזהים את הבעיה, מסבירים למה היא קורית, ונותנים תיקון מדויק.

מידע רלוונטי מהפרויקט שכדאי להתחשב בו:
{context_text}"""
    return run_agent(system_prompt, user_text)


def run_general(user_text):
    system_prompt = """את/ה עוזר/ת כללי/ת וידידותי/ת.
עני/ה על כל שאלה שאינה קשורה ישירות לתכנון ארכיטקטורה, כתיבת קוד, או תיקון באגים —
כולל שיחת חולין, שאלות כלליות, מידע כללי ככל שאת/ה יודע/ת."""
    return run_agent(system_prompt, user_text)


@tool
def Architect(user_text: str) -> str:
    """שימושי כשצריך לתכנן ארכיטקטורת תוכנה, לעצב מבנה מערכת, להחליט אילו רכיבים וטכנולוגיות להשתמש"""
    return run_architect(user_text)


@tool
def Builder(user_text: str) -> str:
    """שימושי כשצריך לכתוב קוד חדש, ליישם פונקציה, לבנות פיצ'ר"""
    return run_builder(user_text)


@tool
def Debugger(user_text: str) -> str:
    """שימושי כשיש שגיאה, באג, קוד שלא עובד, ומבקשים לתקן אותו"""
    return run_debugger(user_text)


@tool
def ExternalAgent(user_text: str) -> str:
    """שימושי כשצריך להריץ כלי חיצוני (OpenClaw, Grok Bot, Instinct) על משימה"""
    return run_external_agent(user_text)


@tool
def General(user_text: str) -> str:
    """שימושי לכל שאלה כללית שלא קשורה לתכנון תוכנה, כתיבת קוד, תיקון באגים, או כלים חיצוניים — שיחת חולין, מידע כללי, שאלות יומיומיות"""
    return run_general(user_text)


tools = [Architect, Builder, Debugger, ExternalAgent, General]

agent = create_agent(
    model=llm,
    tools=tools,
    system_prompt="כשאת/ה מקבל/ת תשובה מכלי (tool), החזר/י אותה בדיוק כפי שהיא, מילה במילה, בלי לשכתב, לסכם או לקצר אותה."
)


def run_agent_system(user_text, history=None, user_name=None):
    history = history or []

    messages = list(history) + [{"role": "user", "content": user_text}]
    if user_name:
        messages = [{"role": "system", "content": f"שם המשתמש/ת הוא {user_name}. אפשר לפנות אליו/ה בשם הזה בפתיחת התשובה, בלי לשכתב את שאר התוכן."}] + messages

    result = agent.invoke({"messages": messages})

    agent_name = None
    for msg in result["messages"]:
        if type(msg).__name__ == "ToolMessage":
            agent_name = getattr(msg, "name", None)

    final_content = result["messages"][-1].content
    return final_content, agent_name