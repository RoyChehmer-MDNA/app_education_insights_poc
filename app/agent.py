"""One focused user journey. Optional grounded Gemini narration; fixed data access."""
import os
from .data import get_attendance, summary

SYSTEM_PROMPT = """אתה אנליסט נתוני נוכחות עבור מפקחת חינוך. ענה בעברית ברורה וקצרה.
השתמש אך ורק בעובדות הנמסרות לך, אל תמציא נתונים, בתי ספר או מקורות.
הפרד בין ממצא עובדתי להמלצה. אל תציג קורלציה כסיבתיות.
אין לבצע פעולות Qlik או לשנות הרשאות. אל תחשוף נתוני תלמידים אישיים."""


def _gemini_answer(question: str, facts: str) -> str:
    from google import genai
    from google.genai import types
    client=genai.Client(vertexai=True, project=os.environ["GOOGLE_CLOUD_PROJECT"],
                             location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"))
    response=client.models.generate_content(
       model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
       contents=f"שאלה: {question}\n\nנתונים מאושרים בלבד:\n{facts}",
       config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT, temperature=0.2))
    return response.text or "לא התקבלה תשובה מהמודל."


def answer(question: str, user_id: str) -> dict:
    question=(question or "").strip()
    if not question or len(question)>800:
        raise ValueError("השאלה חייבת להכיל 1–800 תווים")
    rows=get_attendance(user_id)
    if not rows:
        raise PermissionError("No access to attendance dataset")
    stats=summary(rows)
    largest=sorted(rows, key=lambda r:r["previous"]-r["current"],reverse=True)[0]
    facts=(f"מספר מוסדות: {stats['schools']}; ממוצע נוכחות: {stats['average']}%; "
      f"שינוי ממוצע: {stats['decline']} נקודות אחוז; בתי ספר בירידה של לפחות 5 נקודות: {stats['flagged']}. "
      f"הירידה הגדולה ביותר: {largest['school']}, מ-{largest['previous']}% ל-{largest['current']}% "
      f"(שכבה {largest['grade']}).")
    mode=os.getenv("LLM_MODE", "demo").lower()
    if mode == "gemini":
        reply=_gemini_answer(question,facts)
        label="gemini"
    elif mode == "demo":
        reply=(f"**ממצא:** {facts}\n\n**המלצה:** לבדוק את נתוני הנוכחות לפי ימים וכיתות בבית הספר "
               f"{largest['school']}, ולאמת את הסיבות לירידה עם צוות בית הספר לפני קביעת פעולה.")
        label="demo"
    else:
        raise ValueError("Unsupported LLM_MODE")
    # A suggested command is NOT an applied Qlik selection.
    action={"type":"qlik.selection.proposal","app":"attendance","field":"school_id",
            "values":[largest['school_id']],"status":"not_executed",
            "description":f"הצג את בית הספר {largest['school']} ב־Qlik"}
    return {"answer":reply,"mode":label,"data_mode":os.getenv("DATA_MODE","demo"),
            "facts":stats,"rows":rows,"suggested_action":action,
            "source":"demo_data" if os.getenv("DATA_MODE","demo")=="demo" else "bigquery"}
