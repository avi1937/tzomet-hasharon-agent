# -*- coding: utf-8 -*-
"""
Tzomet Hasharon Telegram News Agent
סוכן חדשות מקומיות לקבוצת Telegram פרטית.

הרצה:
python agent.py test
python agent.py hourly
python agent.py daily
"""

import os
import sys
import time
import json
import html
import re
import sqlite3
import hashlib
from datetime import datetime, timezone, timedelta
from urllib.parse import quote_plus, urlparse, urlencode, parse_qs, urlunparse

import feedparser
import requests


# =====================
# SETTINGS
# =====================

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

MIN_SCORE = int(os.getenv("MIN_SCORE", "6"))
MAX_ITEMS_PER_RUN = int(os.getenv("MAX_ITEMS_PER_RUN", "20"))
MAX_QUERIES_PER_RUN = int(os.getenv("MAX_QUERIES_PER_RUN", "200"))
GOOGLE_NEWS_DAYS_BACK = int(os.getenv("GOOGLE_NEWS_DAYS_BACK", "2"))
SEND_EMPTY_REPORT = os.getenv("SEND_EMPTY_REPORT", "false").lower() == "true"
SQLITE_PATH = os.getenv("SQLITE_PATH", "agent_state.sqlite3")
MAX_AGE_HOURS = int(os.getenv("MAX_AGE_HOURS", "16"))


# =====================
# KEYWORDS
# =====================

CORE_AREAS = [
    "רעננה", "כפר סבא", "הרצליה", "הרצליה פיתוח",
    "מועצה אזורית דרום השרון", "דרום השרון", "השרון"
]

CITIES = ["רעננה", "כפר סבא", "הרצליה"]

PEOPLE = [
    "חיים ברוידא", "רפי סער", "יריב פישר", "נפתלי בנט", "גדי אייזנקוט",
    "עיריית רעננה", "עיריית כפר סבא", "עיריית הרצליה",
    "מועצת העיר רעננה", "מועצת העיר כפר סבא", "מועצת העיר הרצליה"
]

PLACES = [
    "אחוזה", "ויצמן רעננה", "ירושלים רעננה", "הפארק רעננה", "קריית שרת",
    "ויצמן כפר סבא", "רוטשילד כפר סבא", "טשרניחובסקי", "בן יהודה כפר סבא",
    "סוקולוב הרצליה", "בן גוריון הרצליה", "אבא אבן", "מדינת היהודים",
    "שנקר הרצליה", "גלי תכלת",
    "לב הפארק", "נווה זמר", "קריית גנים", "כפר סבא הירוקה",
    "יוספטל כפר סבא", "קפלן כפר סבא", "הדרים כפר סבא", "אלי כהן כפר סבא",
    "נוף ים", "גליל ים", "הרצליה הצעירה", "נווה עמל", "שביב", "הרצליה ב",
    "קרית אתגרים רעננה", "פארק עסקים רעננה", "אזור התעשייה כפר סבא",
    "עתיר ידע כפר סבא", "פארק הייטק הרצליה"
]

BODIES_AND_INSTITUTIONS = [
    "החברה הכלכלית רעננה", "החברה הכלכלית כפר סבא",
    "החברה לפיתוח תיירות הרצליה", "תאגיד מי רעננה", "פלגי השרון",
    "אגף החינוך רעננה", "אגף החינוך כפר סבא", "אגף החינוך הרצליה",
    "אגף ההנדסה רעננה", "אגף ההנדסה כפר סבא", "אגף ההנדסה הרצליה",
    "תיכון מטרווסט", "תיכון אביב", "אוסטרובסקי", "היובל רעננה",
    "כצנלסון", "הרצוג", "בר לב", "אוניברסיטת רייכמן",
    "המרכז הבינתחומי", "מכללת בית ברל", "הראשונים הרצליה", "הנדסאים הרצליה"
]

CULTURE_ATTRACTIONS = [
    "היכל התרבות רעננה", "היכל התרבות כפר סבא", "היכל אמנויות הבמה הרצליה",
    "מוזיאון כפר סבא", "מוזיאון הרצליה", "אמפי פארק רעננה",
    "פארק רעננה", "פארק כפר סבא", "פארק הרצליה", "אגם רעננה",
    "אפולוניה", "חוף אכדיה", "מרינה הרצליה", "ארסוף",
    "גן לאומי אפולוניה", "חוף השרון", "חוף זבולון"
]

COMMERCE_SPORT_HEALTH = [
    "קניון רננים", "קניון ערים", "קניון שבעת הכוכבים", "שבעת הכוכבים",
    "ביג פאשן גלילות", "קניון G כפר סבא", "קניון כפר סבא הירוקה",
    "הפועל רעננה", "מכבי רעננה", "הפועל כפר סבא", "בני הרצליה",
    "אצטדיון לויטה", "אולם מטרווסט", "אולם היובל", "ארנה הרצליה",
    "אצטדיון הרצליה", "הפועל הרצליה",
    "בית חולים מאיר", "מרכז רפואי מאיר", "לוינשטיין",
    "בית לוינשטיין", "הרצליה מדיקל סנטר", "כללית שרון", "מכבי שרון הרצליה"
]

TRANSPORT = [
    "רכבת רעננה", "רכבת כפר סבא", "רכבת הרצליה", "כביש 531",
    "מחלף רעננה", "מחלף הסירה", "כביש 4 רעננה", "כביש 4 כפר סבא",
    "כביש 20 הרצליה", "כביש 2 הרצליה", "כביש 55 כפר סבא"
]

COMPANIES = [
    "NICE", "נייס", "Matrix", "מטריקס", "Microsoft Israel", "מיקרוסופט ישראל",
    "Apple Israel", "אפל ישראל", "אמדוקס", "Amdocs", "SolarEdge", "סולאראדג",
    "NCR", "Philips", "Mellanox", "NVIDIA", "אנבידיה"
]

TOPICS = [
    "פינוי בינוי", "תמא 38", "תמ״א 38", "תמ\"א 38", "התחדשות עירונית",
    "נדלן", "נדל״ן", "נדל\"ן", "תחבורה", "חינוך", "ארנונה",
    "ועדה מקומית", "ועדת תכנון ובנייה", "הפגנה", "תאונת דרכים",
    "שריפה", "פשיעה", "איכות הסביבה", "אירוע קהילתי", "פסטיבל",
    "מרוץ", "הופעה", "סגירת כבישים", "מכרז", "תקציב עירוני", "סייל"
]

# ← חדש שלב 4: נושאי אירועים
CULTURE_EVENTS = [
    "הופעה", "מופע", "תיאטרון", "הרצאה", "פסטיבל", "תערוכה",
    "סיור מודרך", "קונצרט", "סטנדאפ", "קומדיה", "מחול", "אופרה",
    "קולנוע", "ערב תרבות", "מוזיקה חיה", "להקה", "זמר"
]

SPORT_EVENTS = [
    "משחק", "אליפות", "טורניר", "מרוץ", "טריאתלון", "ריצה",
    "אופניים", "שחייה", "כדורגל", "כדורסל", "טניס", "התעמלות",
    "מרתון", "דו קרב", "גמר", "ליגה", "גביע"
]

COMMUNITY_EVENTS = [
    "כנס", "יריד", "שוק", "מפגש תושבים", "ערב פתוח", "יום פתוח",
    "סדנה", "קורס", "השתלמות", "התנדבות", "פעילות קהילתית"
]

NATURE_EVENTS = [
    "טיול", "סיור טבע", "פארק", "חוף", "פיקניק", "נטיעות"
]

SPECIAL_DAYS = [
    "הדלקה", "מצעד", "טקס", "חגיגות", "אירוע מיוחד", "השקה"
]

NATIONAL_SITES = [
    "ynet.co.il", "haaretz.co.il", "themarker.com", "globes.co.il",
    "walla.co.il", "maariv.co.il", "srugim.co.il", "bhol.co.il"
]

LOCAL_SITES = [
    "tzomet-hrz.co.il", "hasharon-post.co.il", "sharonline.co.il", "mynet.co.il"
]

ALL_KEYWORDS = list(dict.fromkeys(
    CORE_AREAS + PEOPLE + PLACES + BODIES_AND_INSTITUTIONS +
    CULTURE_ATTRACTIONS + COMMERCE_SPORT_HEALTH + TRANSPORT + COMPANIES + TOPICS +
    CULTURE_EVENTS + SPORT_EVENTS + COMMUNITY_EVENTS + NATURE_EVENTS + SPECIAL_DAYS
))

LOCAL_ANCHORS = list(dict.fromkeys(
    CORE_AREAS + PEOPLE + PLACES + BODIES_AND_INSTITUTIONS +
    CULTURE_ATTRACTIONS + COMMERCE_SPORT_HEALTH + TRANSPORT
))

BROAD_TERMS = list(dict.fromkeys(
    TOPICS + COMPANIES + ["נפתלי בנט", "גדי אייזנקוט", "NICE", "נייס", "NVIDIA", "אנבידיה"]
))

ALL_EVENT_TERMS = list(dict.fromkeys(
    CULTURE_EVENTS + SPORT_EVENTS + COMMUNITY_EVENTS + NATURE_EVENTS + SPECIAL_DAYS
))


# =====================
# URL NORMALIZATION  ← שלב 2
# =====================

TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "msclkid", "mc_eid", "ref", "source",
    "_ga", "_gl", "igshid", "s", "cmpid"
}

def normalize_url(url):
    try:
        parsed = urlparse(url)
        params = parse_qs(parsed.query, keep_blank_values=False)
        clean_params = {k: v for k, v in params.items() if k.lower() not in TRACKING_PARAMS}
        clean_query = urlencode(clean_params, doseq=True)
        clean = urlunparse((
            parsed.scheme,
            parsed.netloc.lower(),
            parsed.path.rstrip("/"),
            parsed.params,
            clean_query,
            ""
        ))
        return clean
    except Exception:
        return url


# =====================
# HELPERS
# =====================

def clean(text):
    text = html.unescape(text or "")
    text = text.replace("״", '"').replace("׳", "'")
    return re.sub(r"\s+", " ", text).strip()

def norm(text):
    return clean(text).lower()

def contains(text, term):
    return norm(term) in norm(text)

def hits(text, terms):
    return list(dict.fromkeys([t for t in terms if contains(text, t)]))

def uid(title, link):
    return hashlib.sha256((title + "|" + normalize_url(link)).encode("utf-8")).hexdigest()

def quote(term):
    term = term.replace('"', "")
    return '"' + term + '"' if " " in term else term

def detect_city(text):
    if contains(text, "רעננה"):
        return "רעננה"
    if contains(text, "כפר סבא"):
        return "כפר סבא"
    if contains(text, "הרצליה"):
        return "הרצליה"
    if contains(text, "דרום השרון") or contains(text, "מועצה אזורית דרום השרון"):
        return "דרום השרון"
    return "אזור השרון"

def source_from_title(title):
    if " - " in title:
        return title.rsplit(" - ", 1)[-1]
    return "Google News"


# =====================
# TITLE DEDUPLICATION  ← שלב 3
# =====================

def title_similarity(a, b):
    a_words = set(norm(a).split())
    b_words = set(norm(b).split())
    if not a_words or not b_words:
        return 0.0
    shared = a_words & b_words
    return len(shared) / max(len(a_words), len(b_words))

def is_duplicate_title(title, seen_titles, threshold=0.9):
    for seen in seen_titles:
        if title_similarity(title, seen) >= threshold:
            return True
    return False


# =====================
# DATE FILTERING  ← שלב 1
# =====================

def parse_date(entry):
    for field in ("published_parsed", "updated_parsed"):
        val = getattr(entry, field, None)
        if val:
            try:
                return datetime(*val[:6], tzinfo=timezone.utc)
            except Exception:
                continue
    return None

def is_recent(entry, hours=None):
    if hours is None:
        hours = MAX_AGE_HOURS
    dt = parse_date(entry)
    if dt is None:
        return False
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    return dt >= cutoff


# =====================
# DATABASE
# =====================

def db():
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id TEXT PRIMARY KEY,
            title TEXT,
            link TEXT,
            source TEXT,
            score INTEGER,
            city TEXT,
            reasons TEXT,
            query TEXT,
            first_seen_at TEXT,
            sent_at TEXT
        )
    """)
    conn.commit()
    return conn

def already_sent(conn, article_id):
    row = conn.execute("SELECT 1 FROM articles WHERE id=? AND sent_at IS NOT NULL", (article_id,)).fetchone()
    return row is not None

def record_found(conn, item):
    conn.execute("""
        INSERT OR IGNORE INTO articles
        (id,title,link,source,score,city,reasons,query,first_seen_at)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, (
        item["id"], item["title"], item["link"], item["source"], item["score"],
        item["city"], json.dumps(item["reasons"], ensure_ascii=False),
        item["query"], datetime.now(timezone.utc).isoformat()
    ))
    conn.commit()

def mark_sent(conn, article_id):
    conn.execute("UPDATE articles SET sent_at=? WHERE id=?", (datetime.now(timezone.utc).isoformat(), article_id))
    conn.commit()


# =====================
# QUERIES AND FETCH  ← שלב 4: חיפושים חדשים
# =====================

def build_queries():
    queries = []

    # חיפושי בסיס — מילות מפתח מקומיות
    for term in LOCAL_ANCHORS:
        queries.append(f"{quote(term)} when:{GOOGLE_NEWS_DAYS_BACK}d")

    for area in CORE_AREAS:
        for topic in TOPICS:
            queries.append(f"{quote(area)} {quote(topic)} when:{GOOGLE_NEWS_DAYS_BACK}d")

    # חיפושי אתרים ארציים
    site_terms = list(dict.fromkeys(CORE_AREAS + LOCAL_ANCHORS + PEOPLE + COMMERCE_SPORT_HEALTH))
    for term in site_terms:
        for site in NATIONAL_SITES:
            queries.append(f"{quote(term)} site:{site} when:{GOOGLE_NEWS_DAYS_BACK}d")

    for area in CORE_AREAS:
        for site in LOCAL_SITES:
            queries.append(f"{quote(area)} site:{site} when:{GOOGLE_NEWS_DAYS_BACK}d")

    # ← חדש שלב 4: גופים רשמיים
    official_bodies = [
        "עיריית רעננה", "עיריית כפר סבא", "עיריית הרצליה",
        "משטרה רעננה", "משטרה כפר סבא", "משטרה הרצליה",
        "מד״א רעננה", "מד״א כפר סבא", "מד״א הרצליה",
        "כבאות רעננה", "כבאות כפר סבא", "כבאות הרצליה",
        "זק״א שרון", "הצלה רעננה", "הצלה כפר סבא",
    ]
    for body in official_bodies:
        queries.append(f"{quote(body)} when:1d")

    # ← חדש שלב 4: אירועי תרבות לפי עיר
    for city in CITIES:
        for event in CULTURE_EVENTS:
            queries.append(f"{quote(city)} {quote(event)} when:{GOOGLE_NEWS_DAYS_BACK}d")

    # ← חדש שלב 4: אירועי ספורט לפי עיר
    for city in CITIES:
        for event in SPORT_EVENTS:
            queries.append(f"{quote(city)} {quote(event)} when:{GOOGLE_NEWS_DAYS_BACK}d")

    # ← חדש שלב 4: אירועי קהילה לפי עיר
    for city in CITIES:
        for event in COMMUNITY_EVENTS:
            queries.append(f"{quote(city)} {quote(event)} when:{GOOGLE_NEWS_DAYS_BACK}d")

    # ← חדש שלב 4: טבע ופנאי לפי עיר
    for city in CITIES:
        for event in NATURE_EVENTS:
            queries.append(f"{quote(city)} {quote(event)} when:{GOOGLE_NEWS_DAYS_BACK}d")

    # ← חדש שלב 4: ימים מיוחדים לפי עיר
    for city in CITIES:
        for event in SPECIAL_DAYS:
            queries.append(f"{quote(city)} {quote(event)} when:{GOOGLE_NEWS_DAYS_BACK}d")

    return list(dict.fromkeys(queries))[:MAX_QUERIES_PER_RUN]

def fetch(query):
    url = "https://news.google.com/rss/search?q=" + quote_plus(query) + "&hl=he&gl=IL&ceid=IL:he"
    feed = feedparser.parse(url)
    items = []
    skipped_old = 0

    for entry in feed.entries[:10]:
        title = clean(getattr(entry, "title", ""))
        link = clean(getattr(entry, "link", ""))

        if not title or not link:
            continue

        if not is_recent(entry):
            skipped_old += 1
            continue

        published = clean(getattr(entry, "published", ""))

        items.append({
            "title": title,
            "link": normalize_url(link),
            "published": published,
            "source": source_from_title(title),
            "query": query
        })

    return items, skipped_old


# =====================
# RELEVANCE
# =====================

def score(raw):
    text = raw["title"] + " " + raw["link"] + " " + raw["query"]

    keyword_hits = hits(text, ALL_KEYWORDS)
    local_hits = hits(text, LOCAL_ANCHORS)
    core_hits = hits(text, CORE_AREAS)
    topic_hits = hits(text, TOPICS)
    broad_hits = hits(text, BROAD_TERMS)
    event_hits = hits(text, ALL_EVENT_TERMS)  # ← חדש

    if not keyword_hits:
        return None

    if broad_hits and not local_hits and not core_hits:
        return None

    score_value = 0
    reasons = []

    if core_hits:
        score_value += 5
        reasons.extend(core_hits[:3])

    if local_hits:
        score_value += min(4, len(local_hits))
        reasons.extend(local_hits[:4])

    if topic_hits:
        score_value += 2
        reasons.extend(topic_hits[:3])

    # ← חדש: בונוס לאירועים
    if event_hits and core_hits:
        score_value += 3
        reasons.extend(event_hits[:2])

    important = hits(text, [
        "עיריית", "מועצת העיר", "אגף ההנדסה", "ועדה מקומית", "מכרז",
        "תקציב", "פינוי בינוי", "התחדשות עירונית", "תאונת דרכים",
        "שריפה", "פשיעה", "הפגנה", "סגירת כבישים", "ארנונה"
    ])
    if important:
        score_value += 2
        reasons.extend(important[:3])

    score_value = min(score_value, 10)

    if score_value < MIN_SCORE:
        return None

    return {
        "id": uid(raw["title"], raw["link"]),
        "title": raw["title"],
        "link": raw["link"],
        "source": raw["source"],
        "query": raw["query"],
        "score": score_value,
        "city": detect_city(text),
        "reasons": list(dict.fromkeys(reasons))[:7],
    }


# =====================
# TELEGRAM
# =====================

def send_telegram(text):
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("Missing TELEGRAM_BOT_TOKEN")
    if not TELEGRAM_CHAT_ID:
        raise RuntimeError("Missing TELEGRAM_CHAT_ID")

    chunks = [text[i:i+3800] for i in range(0, len(text), 3800)]

    for chunk in chunks:
        r = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": chunk,
                "disable_web_page_preview": True
            },
            timeout=25
        )
        r.raise_for_status()
        time.sleep(0.4)


# =====================
# MESSAGES
# =====================

def hourly_message(items):
    now = datetime.now().strftime("%d/%m/%Y %H:%M")

    if not items:
        return f"🔎 צומת השרון | {now}\n\nלא נמצאו אייטמים חדשים שעברו סינון."

    lines = [
        "🔔 צומת השרון | סוכן חדשות מקומיות",
        now,
        "",
        f"נמצאו {len(items)} אייטמים חדשים:",
        ""
    ]

    for i, item in enumerate(items, 1):
        reasons = ", ".join(item["reasons"]) if item["reasons"] else "התאמה לרשימת החיפוש"
        lines.extend([
            f"{i}. ⭐ {item['score']}/10 | {item['city']}",
            item["title"],
            f"מקור: {item['source']}",
            f"למה נשלח: {reasons}",
            item["link"],
            ""
        ])

    return "\n".join(lines)

def daily_message(conn):
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    rows = conn.execute("""
        SELECT * FROM articles
        WHERE first_seen_at >= ?
        ORDER BY score DESC, first_seen_at DESC
        LIMIT 50
    """, (cutoff,)).fetchall()

    total = len(rows)
    high = len([r for r in rows if int(r["score"] or 0) >= 8])

    lines = [
        "📊 צומת השרון | סיכום יומי",
        datetime.now().strftime("%d/%m/%Y"),
        "",
        f"סה״כ אייטמים ב-24 שעות: {total}",
        f"אייטמים בציון 8 ומעלה: {high}",
        "",
        "האייטמים הבולטים:"
    ]

    for i, r in enumerate(rows[:20], 1):
        lines.extend([
            "",
            f"{i}. ⭐ {r['score']}/10 | {r['city']}",
            r["title"],
            f"מקור: {r['source']}",
            r["link"]
        ])

    return "\n".join(lines)


# =====================
# RUN MODES
# =====================

def run_hourly():
    conn = db()
    candidates = {}
    seen_titles = []

    stats = {
        "scanned": 0,
        "skipped_old": 0,
        "skipped_irrelevant": 0,
        "skipped_duplicate": 0,
        "sent": 0,
    }

    for query in build_queries():
        try:
            raw_items, skipped_old = fetch(query)
            stats["skipped_old"] += skipped_old
        except Exception as e:
            print("Fetch failed:", query, e)
            continue

        stats["scanned"] += len(raw_items)

        for raw in raw_items:
            item = score(raw)
            if not item:
                stats["skipped_irrelevant"] += 1
                continue

            record_found(conn, item)

            if already_sent(conn, item["id"]):
                stats["skipped_duplicate"] += 1
                continue

            if is_duplicate_title(item["title"], seen_titles):
                stats["skipped_duplicate"] += 1
                continue

            if item["id"] not in candidates or item["score"] > candidates[item["id"]]["score"]:
                candidates[item["id"]] = item
                seen_titles.append(item["title"])

        time.sleep(0.12)

    selected = sorted(candidates.values(), key=lambda x: x["score"], reverse=True)[:MAX_ITEMS_PER_RUN]
    stats["sent"] = len(selected)

    if selected or SEND_EMPTY_REPORT:
        send_telegram(hourly_message(selected))

    for item in selected:
        mark_sent(conn, item["id"])

    print("=" * 40)
    print(f"✅ סיכום ריצה | {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print(f"   נסרקו:        {stats['scanned']}")
    print(f"   נפסלו ישנים:  {stats['skipped_old']}")
    print(f"   לא רלוונטי:   {stats['skipped_irrelevant']}")
    print(f"   כפילויות:     {stats['skipped_duplicate']}")
    print(f"   נשלחו:        {stats['sent']}")
    print("=" * 40)

def run_daily():
    conn = db()
    send_telegram(daily_message(conn))
    print("Daily sent")

def run_test():
    send_telegram("✅ בדיקת סוכן צומת השרון\n\nהבוט מחובר ומוכן.")
    print("Test sent")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "hourly"

    if mode == "test":
        run_test()
    elif mode == "daily":
        run_daily()
    else:
        run_hourly()
