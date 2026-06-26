# צומת השרון – Telegram News Agent

סוכן חדשות מקומיות לקבוצת Telegram פרטית.

## קבצים
- `agent.py` – כל קוד הסוכן
- `requirements.txt` – ספריות Python
- `render.yaml` – הגדרות Render

## מה הסוכן עושה
- מחפש ב-Google News RSS לפי מילות חיפוש מקומיות.
- מחפש באתרים ארציים רק עם מילות חיפוש מקומיות.
- מסנן רעש.
- שולח לקבוצת Telegram.
- מונע כפילויות.
- שולח סיכום יומי.

## משתני סביבה ב-Render
- TELEGRAM_BOT_TOKEN
- TELEGRAM_CHAT_ID

## בדיקה
אחרי הפריסה אפשר להריץ:
python agent.py test
