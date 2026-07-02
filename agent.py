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

MIN_SCORE = int(os.getenv("MIN_SCORE", "4"))
MAX_ITEMS_PER_RUN = int(os.getenv("MAX_ITEMS_PER_RUN", "20"))
MAX_QUERIES_PER_RUN = int(os.getenv("MAX_QUERIES_PER_RUN", "200"))
GOOGLE_NEWS_DAYS_BACK = int(os.getenv("GOOGLE_NEWS_DAYS_BACK", "2"))
SEND_EMPTY_REPORT = os.getenv("SEND_EMPTY_REPORT", "false").lower() == "true"
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip()
MAX_AGE_HOURS = int(os.getenv("MAX_AGE_HOURS", "16"))
MIN_LOCAL_HITS = int(os.getenv("MIN_LOCAL_HITS", "4"))

TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


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
    "המרכז הבינתחומי", "מכללת בית ברל", "הראשונים הרצליה", "הנדסאים הרצליה",
    "רייכמן", "אוניברסיטת רייכמן הרצליה", "כנס הרצליה", "בועז גנור"
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
    "hasharon-post.co.il", "sharonline.co.il", "inhasharon.co.il", "hoha.co.il",
    "kfarsaba.news", "raanana.news", "herzlia.news", "kfarsabanews.com",
    "raanana.muni.il", "kfar-saba.muni.il", "herzliya.muni.il",
    "hamal.co.il",
    "runi.ac.il"
]

BLOCKED_URL_PATTERNS = [
    "tzomet-hasharon", "tzomethasharon",
    "tzomet-hrz", "tzomet-ran", "tzomet-kfs", "tzomet-ha",
    "צומת-השרון", "צומתהשרון"
]

# אתרי ספורט שלא רוצים בכלל (ערוץ 5 / ספורט 5, ONE, ספורט 1)
BLOCKED_SPORT_DOMAINS = [
    "sport5.co.il",
    "one.co.il",
    "sport1.co.il",
]

# שמות המקורות כפי שהם מופיעים ב-Google News (גיבוי לחסימה לפי דומיין)
BLOCKED_SPORT_SOURCE_NAMES = [
    "sport5", "sport 5", "ספורט 5", "ערוץ הספורט", "ערוץ 5",
    "one", "וואן",
    "sport1", "sport 1", "ספורט 1",
]

BLOCKED_TITLE_PATTERNS = [
    "צומת השרון הרצליה", "צומת השרון כפר סבא", "צומת השרון רעננה",
    "tzomet hasharon", "tzomet-hasharon"
]

BLOCKED_TERMS = [
    "sponsored", "פרסומת", "תוכן שיווקי", "תוכן ממומן",
    "קידום מכירות", "שיתוף פעולה פרסומי", "advertorial"
]

OPINION_TERMS = [
    "מאמר דעה", "טור דעה", "דעה:", "פרשנות:", "ניתוח:",
    "מבט על", "כותב:", "עמדה:"
]

PR_TERMS = [
    "הודעה לעיתונות", "יחסי ציבור", "בשיתוף", "בתמיכת",
    "באדיבות", "בחסות"
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

SPECIFIC_LOCAL = list(dict.fromkeys(
    PLACES + BODIES_AND_INSTITUTIONS + CULTURE_ATTRACTIONS +
    COMMERCE_SPORT_HEALTH + TRANSPORT + PEOPLE
))

BROAD_TERMS = list(dict.fromkeys(
    TOPICS + COMPANIES + ["נפתלי בנט", "גדי אייזנקוט", "NICE", "נייס", "NVIDIA", "אנבידיה"]
))

ALL_EVENT_TERMS = list(dict.fromkeys(
    CULTURE_EVENTS + SPORT_EVENTS + COMMUNITY_EVENTS + NATURE_EVENTS + SPECIAL_DAYS
))


# =====================
# URL NORMALIZATION
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

def title_key(title):
    # מפתח יציב לפי הכותרת בלבד — תופס כפילויות של אותה ידיעה גם כשהקישור משתנה
    return hashlib.sha256(norm(title).encode("utf-8")).hexdigest()

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

def is_blocked_url(url):
    url_lower = url.lower()
    return any(p in url_lower for p in BLOCKED_URL_PATTERNS)

def is_sport_source(source_name, source_url):
    """← חוסם ידיעות שמגיעות מאתרי ספורט (לפי דומיין המקור או שם המקור)."""
    if source_url:
        try:
            host = urlparse(source_url).netloc.lower()
            if host.startswith("www."):
                host = host[4:]
            if any(host == d or host.endswith("." + d) for d in BLOCKED_SPORT_DOMAINS):
                return True
        except Exception:
            pass
    s = " " + norm(source_name) + " "
    for name in BLOCKED_SPORT_SOURCE_NAMES:
        if (" " + norm(name) + " ") in s:
            return True
    return False

def is_blocked_title(title):
    title_lower = norm(title)
    return any(norm(p) in title_lower for p in BLOCKED_TITLE_PATTERNS)

def is_national_source(link):
    return any(site in link.lower() for site in NATIONAL_SITES)

def count_specific_local_hits(text):
    return len(hits(text, SPECIFIC_LOCAL))


# =====================
# TITLE DEDUPLICATION
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
# DATE FILTERING
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
# DATABASE (Supabase)
# =====================

# =====================
# DATABASE (Supabase דרך REST ישיר — HTTP/1.1, יציב)
# =====================
# הערה: אנחנו לא משתמשים בספריית supabase-py כי היא פותחת חיבור HTTP/2
# שסביבת Render מפילה (StreamReset). במקום זה קוראים ישירות ל-PostgREST
# עם requests (HTTP/1.1) — יציב לגמרי.

def _sb_headers(extra=None):
    h = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Connection": "close",  # לא לשמור חיבור פתוח — מונע נפילות
    }
    if extra:
        h.update(extra)
    return h

def _sb_url(path):
    base = SUPABASE_URL.rstrip("/")
    return f"{base}/rest/v1/{path}"

def _sb_request(method, path, what, params=None, json_body=None, headers=None, attempts=4):
    """קריאת REST ל-Supabase עם ניסיונות חוזרים. מחזיר Response או None."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_KEY")
    delay = 0.5
    for i in range(attempts):
        try:
            resp = requests.request(
                method,
                _sb_url(path),
                headers=_sb_headers(headers),
                params=params,
                json=json_body,
                timeout=30,
            )
            if resp.status_code >= 400:
                # שגיאת שרת/נתונים — לא ננסה שוב סתם, נדפיס ונחזיר
                print(f"{what} HTTP {resp.status_code}:", resp.text[:300])
                if resp.status_code in (500, 502, 503, 504) and i < attempts - 1:
                    time.sleep(delay); delay = min(delay * 2, 4); continue
                return None
            return resp
        except Exception as e:
            msg = str(e)
            if i == attempts - 1:
                print(f"{what} failed (after {attempts} tries):", msg)
                return None
            time.sleep(delay)
            delay = min(delay * 2, 4)
    return None

def db():
    """נשמר לתאימות — כבר לא צריך client אמיתי, אבל קוד ישן קורא לזה."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_KEY")
    return True

def load_recent_sent(client=None, days=4):
    """טוען מ-Supabase את כל מה שכבר נשלח בימים האחרונים, כדי למנוע כפילויות."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    sent_ids, sent_tkeys = set(), set()

    resp = _sb_request(
        "GET", "articles", "load_recent_sent",
        params={
            "select": "id,title_key,sent_at",
            "first_seen_at": f"gte.{cutoff}",
            "sent_at": "not.is.null",
        },
    )
    if resp is not None:
        try:
            for row in resp.json():
                if row.get("sent_at"):
                    if row.get("id"):
                        sent_ids.add(row["id"])
                    if row.get("title_key"):
                        sent_tkeys.add(row["title_key"])
        except Exception as e:
            print("load_recent_sent parse failed:", e)
    return sent_ids, sent_tkeys

def _row_from_item(item, now):
    return {
        "id": item["id"],
        "title": item["title"],
        "link": item["link"],
        "source": item["source"],
        "city": item["city"],
        "reasons": json.dumps(item["reasons"], ensure_ascii=False),
        "query": item["query"],
        "title_key": item["title_key"],
        "first_seen_at": now,
        "status": "pending",
    }

def record_found(client, item):
    """שומר ידיעה שנמצאה. אם קיימת — מתעלם (ignore duplicates)."""
    now = datetime.now(timezone.utc).isoformat()
    _sb_request(
        "POST", "articles", "record_found",
        params={"on_conflict": "id"},
        json_body=_row_from_item(item, now),
        headers={"Prefer": "resolution=ignore-duplicates,return=minimal"},
    )

def record_found_bulk(client, items):
    """שומר קבוצת ידיעות בבקשה אחת (יציב ומהיר)."""
    if not items:
        return
    now = datetime.now(timezone.utc).isoformat()
    rows = [_row_from_item(it, now) for it in items]
    _sb_request(
        "POST", "articles", "record_found_bulk",
        params={"on_conflict": "id"},
        json_body=rows,
        headers={"Prefer": "resolution=ignore-duplicates,return=minimal"},
    )

def mark_sent(client, article_id, message_id=None):
    """מסמן ידיעה כ'נשלחה' כדי שלא תישלח שוב."""
    payload = {
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "telegram_message_id": str(message_id) if message_id else None,
        "status": "sent",
    }
    _sb_request(
        "PATCH", "articles", "mark_sent",
        params={"id": f"eq.{article_id}"},
        json_body=payload,
        headers={"Prefer": "return=minimal"},
    )



# =====================
# QUERIES AND FETCH
# =====================

def build_queries():
    queries = []

    for term in LOCAL_ANCHORS:
        queries.append(f"{quote(term)} when:{GOOGLE_NEWS_DAYS_BACK}d")

    for area in CORE_AREAS:
        for topic in TOPICS:
            queries.append(f"{quote(area)} {quote(topic)} when:{GOOGLE_NEWS_DAYS_BACK}d")

    site_terms = list(dict.fromkeys(CORE_AREAS + LOCAL_ANCHORS + PEOPLE + COMMERCE_SPORT_HEALTH))
    for term in site_terms:
        for site in NATIONAL_SITES:
            queries.append(f"{quote(term)} site:{site} when:{GOOGLE_NEWS_DAYS_BACK}d")

    for area in CORE_AREAS:
        for site in LOCAL_SITES:
            queries.append(f"{quote(area)} site:{site} when:{GOOGLE_NEWS_DAYS_BACK}d")

    official_bodies = [
        "עיריית רעננה", "עיריית כפר סבא", "עיריית הרצליה",
        "משטרה רעננה", "משטרה כפר סבא", "משטרה הרצליה",
        "מד״א רעננה", "מד״א כפר סבא", "מד״א הרצליה",
        "כבאות רעננה", "כבאות כפר סבא", "כבאות הרצליה",
        "זק״א שרון", "הצלה רעננה", "הצלה כפר סבא",
    ]
    for body in official_bodies:
        queries.append(f"{quote(body)} when:1d")

    for city in CITIES:
        for event in CULTURE_EVENTS + SPORT_EVENTS + COMMUNITY_EVENTS + NATURE_EVENTS + SPECIAL_DAYS:
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

        if is_blocked_url(link) or is_blocked_title(title):
            continue

        # ← זיהוי המקור (שם + דומיין) לצורך חסימת אתרי ספורט
        src_name = ""
        src_href = ""
        src = getattr(entry, "source", None)
        if src is not None:
            try:
                src_name = clean(getattr(src, "title", "") or "")
                src_href = getattr(src, "href", "") or ""
            except Exception:
                pass
        if not src_name:
            src_name = source_from_title(title)

        if is_sport_source(src_name, src_href):
            continue

        if not is_recent(entry):
            skipped_old += 1
            continue

        published = clean(getattr(entry, "published", ""))

        items.append({
            "title": title,
            "link": normalize_url(link),
            "published": published,
            "source": src_name or source_from_title(title),
            "query": query
        })

    return items, skipped_old


# =====================
# RELEVANCE + SCORING
# =====================

def score(raw):
    text = raw["title"] + " " + raw["link"] + " " + raw["query"]
    title = raw["title"]

    if hits(title, BLOCKED_TERMS):
        return None

    keyword_hits = hits(text, ALL_KEYWORDS)
    local_hits = hits(text, LOCAL_ANCHORS)
    core_hits = hits(text, CORE_AREAS)
    topic_hits = hits(text, TOPICS)
    broad_hits = hits(text, BROAD_TERMS)
    event_hits = hits(text, ALL_EVENT_TERMS)
    specific_count = count_specific_local_hits(text)

    if not keyword_hits:
        return None

    if broad_hits and not local_hits and not core_hits:
        return None

    # דרישה ריאלית: לפחות מילת מפתח ספציפית אחת (רחוב/מוסד/גוף) + שם עיר/אזור
    if specific_count < 1 or not core_hits:
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

    if event_hits and core_hits:
        score_value += 3
        reasons.extend(event_hits[:2])

    important = hits(text, [
        "עיריית", "מועצת העיר", "אגף ההנדסה", "ועדה מקומית", "מכרז",
        "תקציב", "פינוי בינוי", "התחדשות עירונית", "תאונת דרכים",
        "שריפה", "פשיעה", "הפגנה", "סגירת כבישים", "ארנונה",
        "משטרה", "מד״א", "כבאות", "זק״א"
    ])
    if important:
        score_value += 2
        reasons.extend(important[:3])

    if hits(title, OPINION_TERMS):
        score_value -= 3

    if hits(title, PR_TERMS):
        score_value -= 2

    if is_national_source(raw["link"]):
        specific_local = hits(text, PLACES + BODIES_AND_INSTITUTIONS + CULTURE_ATTRACTIONS + COMMERCE_SPORT_HEALTH)
        if not specific_local and len(core_hits) <= 1:
            return None

    score_value = max(0, min(score_value, 10))

    if score_value < MIN_SCORE:
        return None

    return {
        "id": uid(raw["title"], raw["link"]),
        "title_key": title_key(raw["title"]),
        "title": raw["title"],
        "link": raw["link"],
        "source": raw["source"],
        "query": raw["query"],
        "score": score_value,
        "city": detect_city(text),
        "reasons": list(dict.fromkeys(reasons))[:5],
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
            f"{TELEGRAM_API}/sendMessage",
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": chunk,
                "disable_web_page_preview": True
            },
            timeout=25
        )
        r.raise_for_status()
        time.sleep(0.4)

def send_article_with_buttons(item):
    """← שולח כתבה בודדת עם כפתורי שכתב/דלג."""
    text_lines = [
        f"📍 {item['city']}",
        "",
        item["title"],
        f"מקור: {item['source']}",
        item["link"]
    ]
    text = "\n".join(text_lines)

    # ← תיקון: callback_data מוגבל ל-64 בייטים בטלגרם. מקצרים את ה-id.
    short_id = item["id"][:16]

    reply_markup = {
        "inline_keyboard": [[
            {"text": "✏️ שכתב", "callback_data": f"rw:{short_id}"},
            {"text": "🗑️ דלג", "callback_data": f"dl:{short_id}"}
        ]]
    }

    try:
        r = requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": text,
                "disable_web_page_preview": True,
                "reply_markup": reply_markup
            },
            timeout=25
        )
        r.raise_for_status()
        data = r.json()
        return data.get("result", {}).get("message_id")
    except Exception as e:
        print("Send article failed:", e)
        return None


# =====================
# MESSAGES
# =====================

def daily_message(client=None):
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    rows = []
    resp = _sb_request(
        "GET", "articles", "daily_message",
        params={
            "select": "*",
            "first_seen_at": f"gte.{cutoff}",
            "order": "first_seen_at.desc",
            "limit": "50",
        },
    )
    if resp is not None:
        try:
            rows = resp.json() or []
        except Exception as e:
            print("daily_message parse failed:", e)
            rows = []

    total = len(rows)

    lines = [
        "📊 צומת השרון | סיכום יומי",
        datetime.now().strftime("%d/%m/%Y"),
        "",
        f"סה״כ ידיעות ב-24 שעות: {total}",
        "",
        "הידיעות האחרונות:"
    ]

    for i, r in enumerate(rows[:20], 1):
        lines.extend([
            "",
            f"{i}. 📍 {r['city']}",
            r["title"],
            f"מקור: {r['source']}",
            r["link"]
        ])

    return "\n".join(lines)


# =====================
# RUN MODES
# =====================

def run_hourly():
    client = db()
    sent_ids, sent_tkeys = load_recent_sent(client)
    candidates = {}
    seen_titles = []
    seen_tkeys = set()

    stats = {
        "scanned": 0,
        "skipped_old": 0,
        "skipped_irrelevant": 0,
        "skipped_duplicate": 0,
        "skipped_blocked": 0,
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
            if hits(raw["title"], BLOCKED_TERMS):
                stats["skipped_blocked"] += 1
                continue

            item = score(raw)
            if not item:
                stats["skipped_irrelevant"] += 1
                continue

            # כבר נשלח בעבר (נשמר ב-Supabase) — לפי מזהה או לפי כותרת
            if item["id"] in sent_ids or item["title_key"] in sent_tkeys:
                stats["skipped_duplicate"] += 1
                continue

            # כפילות בתוך אותה ריצה
            if item["title_key"] in seen_tkeys or is_duplicate_title(item["title"], seen_titles):
                stats["skipped_duplicate"] += 1
                continue

            if item["id"] not in candidates or item["score"] > candidates[item["id"]]["score"]:
                candidates[item["id"]] = item
                seen_titles.append(item["title"])
                seen_tkeys.add(item["title_key"])

        time.sleep(0.12)

    selected = sorted(candidates.values(), key=lambda x: x["score"], reverse=True)[:MAX_ITEMS_PER_RUN]
    stats["sent"] = len(selected)

    # שמירת כל הנבחרים ב-Supabase בבת אחת (בקשה אחת יציבה במקום עשרות)
    record_found_bulk(client, selected)

    # ← שולח כל כתבה בנפרד עם כפתורים, ומסמן מיד כ'נשלחה'
    for item in selected:
        message_id = send_article_with_buttons(item)
        mark_sent(client, item["id"], message_id)
        sent_ids.add(item["id"])
        sent_tkeys.add(item["title_key"])
        time.sleep(0.4)

    if not selected and SEND_EMPTY_REPORT:
        send_telegram(f"🔎 צומת השרון | {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\nלא נמצאו ידיעות חדשות שעברו סינון.")

    print("=" * 40)
    print(f"✅ סיכום ריצה | {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print(f"   נסרקו:        {stats['scanned']}")
    print(f"   נפסלו ישנים:  {stats['skipped_old']}")
    print(f"   חסומים:       {stats['skipped_blocked']}")
    print(f"   לא רלוונטי:   {stats['skipped_irrelevant']}")
    print(f"   כפילויות:     {stats['skipped_duplicate']}")
    print(f"   נשלחו:        {stats['sent']}")
    print("=" * 40)

def run_daily():
    client = db()
    send_telegram(daily_message(client))
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
