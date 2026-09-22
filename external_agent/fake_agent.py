import sys

task = sys.argv[1] if len(sys.argv) > 1 else "לא התקבלה משימה"
print(f"[כלי חיצוני מדומה] קיבלתי משימה: {task}")
print("זו תשובה מזויפת - כשיהיה כלי אמיתי, כאן תהיה התשובה שלו")