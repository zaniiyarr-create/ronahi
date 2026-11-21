import secrets
import sys
import practice
import plus_shop
import subprocess
import ronahi_ai as ai
from urllib.parse import urlencode
import json
import os
import re
import sqlite3
from datetime import datetime, timezone, timedelta
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

MENU = [["دووعا", "زیکر"], ["قورئانا پیرۆز", "هاریکاری"]]
DUAS = {
    "دووعایا زانینێ": "رَبِّ زِدْنِي عِلْمًا\n\nخودایێ من، زانینا من زێدە بکە.\nبەشەک ژ ئایەتا ١١٤، سوورەتا طه\nhttps://quran.com/20/114",
    "خێرا دنیایێ و ئاخرەتێ": "رَبَّنَا آتِنَا فِي الدُّنْيَا حَسَنَةً وَفِي الْآخِرَةِ حَسَنَةً وَقِنَا عَذَابَ النَّارِ\n\nخودایێ مە، ل دنیایێ و ل ئاخرەتێ خێرێ بدە مە و مە ژ عەذابا ئاگری بپارێزە.\nبەشەک ژ ئایەتا ٢٠١، سوورەتا البقرة\nhttps://quran.com/2/201",
}
BACK = "زڤڕین بۆ مینیویا سەرەکی"
DUA_MENU = [[title] for title in DUAS] + [[BACK]]


def reply(text):
    value = text.strip()
    if value.startswith("/"):
        value = value.split()[0].split("@")[0].lower()
    if value in ("/start", "/menu", BACK):
        return "سەلام علیکم، بخێر هاتی بۆ ڕووناهی. پرسیارا خۆ بنڤیسە، دەنگەکێ بنێرە یان بەشەکێ هەلبژێرە. بۆ هاریکاریا AI، نامە و دەنگ بۆ خزمەتگوزارێ AI دهێنە هنارتن.", MENU
    if value in ("دووعا", "/dua"):
        return "دووعایەکێ هەلبژێرە.", DUA_MENU
    if value in DUAS:
        return DUAS[value], DUA_MENU
    if value in ("زیکر", "/dhikr"):
        return ("سُبْحَانَ اللَّهِ\nپاک و بێ‌کێماسییە خودێ.\n\n"
                "الْحَمْدُ لِلَّهِ\nهەمی ستایش بۆ خودێیە.\n\n"
                "اللَّهُ أَكْبَرُ\nخودێ ژ هەمی تشتان مەزنترە."), MENU
    if value in ("قورئانا پیرۆز", "/quran"):
        return "ژ بۆ خواندن و گوهداریکرنێ سوورەتەکێ ڤەکە.\n\nالفاتحة\nhttps://quran.com/1\n\nالكهف\nhttps://quran.com/18\n\nيس\nhttps://quran.com/36", MENU
    if value in ("هاریکاری", "/help"):
        return "دوگمەیەکێ هەلبژێرە، یان /dua، /dhikr یان /quran بنێرە. ب /menu تو دزڤڕی بۆ مینیویا سەرەکی.", MENU
    return "تکایە ژ مینیویێ هەلبژێرە یان /help بنێرە.", MENU


SURAHS = """الفاتحة البقرة آل_عمران النساء المائدة الأنعام الأعراف الأنفال التوبة يونس هود يوسف الرعد إبراهيم الحجر النحل الإسراء الكهف مريم طه الأنبياء الحج المؤمنون النور الفرقان الشعراء النمل القصص العنكبوت الروم لقمان السجدة الأحزاب سبأ فاطر يس الصافات ص الزمر غافر فصلت الشورى الزخرف الدخان الجاثية الأحقاف محمد الفتح الحجرات ق الذاريات الطور النجم القمر الرحمن الواقعة الحديد المجادلة الحشر الممتحنة الصف الجمعة المنافقون التغابن الطلاق التحريم الملك القلم الحاقة المعارج نوح الجن المزمل المدثر القيامة الإنسان المرسلات النبأ النازعات عبس التكوير الانفطار المطففين الانشقاق البروج الطارق الأعلى الغاشية الفجر البلد الشمس الليل الضحى الشرح التين العلق القدر البينة الزلزلة العاديات القارعة التكاثر العصر الهمزة الفيل قريش الماعون الكوثر الكافرون النصر المسد الإخلاص الفلق الناس""".replace("آل_عمران","آل‌عمران").split()
DAILY = [
    ("إِنَّ مَعَ الْعُسْرِ يُسْرًا", "ب ڕاستی، دگەل تەنگاڤیێ ئاسانی هەیە.", "94/6"),
    ("قُلْ هُوَ اللَّهُ أَحَدٌ", "بێژە، ئەو خودایە و ئێکە.", "112/1"),
    ("وَالْعَصْرِ", "سوێند ب دەمی.", "103/1"),
]
QUIZ = [
    ("ئێکەم سوورەتا قورئانێ کیژە؟", ["الفاتحة", "البقرة", "الناس"], "الفاتحة", "1"),
    ("قورئان چەند سوورەت هەنە؟", ["٣٠", "١١٤", "٦٠"], "١١٤", "114"),
    ("دووعایا «رَبِّ زِدْنِي عِلْمًا» د کیژ سوورەتێ دایە؟", ["مريم", "يس", "طه"], "طه", "20/114"),
    ("دوماهیک سوورەتا قورئانێ کیژە؟", ["الفلق", "الناس", "الإخلاص"], "الناس", "114"),
    ("«إِنَّ مَعَ الْعُسْرِ يُسْرًا» د کیژ سوورەتێ دایە؟", ["الشرح", "الضحى", "العصر"], "الشرح", "94/6"),
]
QURAN, AYAH, COUNTER, QUIZ_BTN = "قورئانا پیرۆز", "ئایەتا ئەڤڕۆ", "تەسبیح", "تاقیکرنەوە"
SAVE, MARKS, PROFILE = "نیشان بکە", "سوورەتێن من", "پێشکەفتنا من"
MENU = [[QURAN, AYAH], ["دووعا", "زیکر"], [COUNTER, QUIZ_BTN], [MARKS, PROFILE], ["هاریکاری"]]
COUNTS = [["+١", "+١٠"], [BACK]]

def normalize(value):
    value = value.translate(str.maketrans("أإآىةکێی", "ااايهكيي"))
    return re.sub(r"[\s\u200c\u064b-\u065fـ]", "", value)

RESUME = "بەردەوام بە"
BOOKMARK = "جهێ خواندنێ دیار بکە"
DONE = "من ئەڤ ئایەتە خواند"
REMINDER = "یادئینانا خواندنێ"
STOP = "یادئینانێ بوەستینە"
IRAQ = timezone(timedelta(hours=3))
LENGTHS = tuple(map(int, """7 286 200 176 120 165 206 75 129 109 123 111 43 52 99 128 111 110 98 135 112 78 118 64 77 227 93 88 69 60 34 30 73 54 45 83 182 88 75 85 54 53 89 59 37 35 38 29 18 45 60 49 62 55 78 96 29 22 24 13 14 11 11 18 12 12 30 52 52 44 28 28 20 56 40 31 50 40 46 42 29 19 36 25 22 17 19 26 30 20 15 21 11 8 8 19 5 8 8 11 11 8 3 9 5 4 7 3 6 3 5 4 5 6""".split()))
MENU.insert(0, [RESUME, REMINDER])
READ_MENU = [[DONE, BOOKMARK], [REMINDER, BACK]]
TIME_MENU = [["08:00", "18:00", "21:00"], [STOP, BACK]]

def reading_card(s):
    s["mode"] = "reading"
    chapter, verse = s.get("next_verse", [1, 1])
    if chapter > len(LENGTHS):
        return "تە خواندنا قورئانێ تەمام کر. بۆ دەستپێکرنا دووبارە، جهەکێ هەلبژێرە.", [[BOOKMARK, BACK]]
    return (f"نۆکا خواندنا تە\n{SURAHS[chapter-1]} · ئایەتا {verse}\n"
            f"https://quran.com/{chapter}/{verse}\n{goal_line(s)}\n\nپشتی خواندنێ، دوگمەیا «{DONE}» لێ بدە."), READ_MENU

def reading_action(text, s):
    v = text.strip()
    mode = s.get("mode")
    if v in (RESUME, "/resume"):
        return reading_card(s)
    if v == BOOKMARK:
        s["mode"] = "position"
        return "ژمارا سوورەتێ و ئایەتا تو دڤێی بخوینی بنێرە، وەک ١٨:١١.", [[BACK]]
    if v == DONE and mode == "reading":
        c, a = s.get("next_verse", [1, 1])
        if c <= len(LENGTHS):
            day = datetime.now(IRAQ).date().isoformat()
            s["read_count"] = 1 + (s.get("read_count",0) if day == s.get("read_day") else 0)
            s["read_day"] = day
            s["next_verse"] = [c, a+1] if a < LENGTHS[c-1] else [c+1, 1]
        return reading_card(s)
    if v == STOP:
        s.pop("reminder_time", None)
        s["mode"] = None
        return "یادئینانا تە هاتە وەستاندن.", MENU
    if v in (REMINDER, "/reminder"):
        s["mode"] = "reminder"
        current = s.get("reminder_time", "ناچالاک")
        return f"یادئینانا ڕۆژانە • {current}\nدەمەکێ ب دەمێ عێراقێ هەلبژێرە یان بنێرە، وەک ٢٠:٣٠.", TIME_MENU
    if v in {b for row in MENU for b in row} or v == BACK or v.startswith("/"):
        return None
    if mode == "position":
        m = re.fullmatch(r"(\d{1,3})\s*[:：/]\s*(\d{1,3})", v)
        if m:
            c, a = map(int, m.groups())
            if 1 <= c <= 114 and 1 <= a <= LENGTHS[c-1]:
                s["next_verse"] = [c, a]
                return reading_card(s)
        return "ژمارا سوورەتێ و ئایەتێ بپشکنە. نموونە ١٨:١١", [[BACK]]
    if mode == "reminder":
        m = re.fullmatch(r"(\d{1,2}):(\d{2})", v)
        if m:
            h, mins = map(int, m.groups())
            if h < 24 and mins < 60:
                clock = f"{h:02}:{mins:02}"
                s.update(reminder_time=clock, mode=None)
                return f"هەر ڕۆژ د {clock} ب دەمێ عێراقێ یادئینان دێ بۆ تە هێت.", MENU
        return "دەمژمێرێ ژ ٠٠:٠٠ تا ٢٣:٥٩ بنێرە.", TIME_MENU

def reminders(db, token):
    now = datetime.now(IRAQ)
    day, clock = now.date().isoformat(), now.strftime("%H:%M")
    # Keep a short delivery window for restarts without sending old notifications.
    floor = max(0, now.hour * 60 + now.minute - 4)
    earliest = f"{floor//60:02}:{floor%60:02}"
    due = db.execute("SELECT chat FROM reminders WHERE clock BETWEEN ? AND ? AND last_day != ? LIMIT 20",
                     (earliest, clock, day)).fetchall()
    for (chat,) in due:
        with db:
            db.execute("UPDATE reminders SET last_day=? WHERE chat=?", (day,chat))
        try:
            api(token, "sendMessage", chat_id=chat, text="دەمێ خواندنا تەیە. بۆ زڤڕینێ بۆ ئایەتا خۆ، «بەردەوام بە» هەلبژێرە.",
                reply_markup={"keyboard":[[RESUME, STOP],[BACK]], "resize_keyboard":True})
        except TelegramError as err:
            with db:
                if err.code == 403:
                    db.execute("DELETE FROM reminders WHERE chat=?", (chat,))
                    row = db.execute("SELECT state FROM users WHERE chat=?", (chat,)).fetchone()
                    if row:
                        state = json.loads(row[0])
                        state.pop("reminder_time", None)
                        db.execute("UPDATE users SET state=? WHERE chat=?", (json.dumps(state),chat))
                elif err.code == 429 or err.code >= 500:
                    db.execute("UPDATE reminders SET last_day='' WHERE chat=?", (chat,))
            if err.code not in (400,403):
                raise


GOAL = "ئامانجا خواندنێ"
PRAYER = "دەمێن نڤێژان"
CITY = "باژێرێ من"
ALERTS = "یادئینانێن نڤێژان"
CITIES = {"زاخۆ":"Zaxo","دهۆک":"Duhok","هەولێر":"Hawler","سلێمانی":"Slemany"}
PRAYERS = ["سپێدێ","نیڤرو","عەسر","مەغرەب","عەیشا"]
with open(os.path.join(os.path.dirname(__file__), "prayers.json"), encoding="utf-8") as timetable:
    TIMES = json.load(timetable)
MENU.insert(1, [GOAL, PRAYER])
GOAL_MENU = [["٣","٥","١٠","٢٠"], [BACK]]
def goal_line(s):
    today = datetime.now(IRAQ).date().isoformat()
    count = s.get("read_count", 0) if today == s.get("read_day") else 0
    target = s.get("goal")
    if not target:
        return f"ئەڤڕۆ تە {count} ئایەت خواندین."
    left = max(0, target-count)
    return f"خواندنا ئەڤڕۆ • {count} / {target}\n" + (f"{left} ئایەت مانە." if left else "تە ئامانجا ئەڤڕۆ تەمام کر.")

DUAS.update({
    "سپێدێ": "اللَّهُمَّ بِكَ أَصْبَحْنَا وَبِكَ أَمْسَيْنَا وَبِكَ نَحْيَا وَبِكَ نَمُوتُ وَإِلَيْكَ النُّشُورُ\n\nخودایێ مە، ب تە ئەم دگەهینە سپێدێ و ئێڤارێ، ب تە ئەم دژین و دمرین، و ڤەژینا مە بەرەڤ تەیە.\nسنن أبي داود ٥٠٦٨\nhttps://sunnah.com/abudawud:5068",
    "ئێڤارێ": "اللَّهُمَّ بِكَ أَمْسَيْنَا وَبِكَ نَحْيَا وَبِكَ نَمُوتُ وَإِلَيْكَ النُّشُورُ\n\nخودایێ مە، ب تە ئەم گەهشتینە ئێڤارێ، ب تە ئەم دژین و دمرین، و ڤەژینا مە بەرەڤ تەیە.\nسنن أبي داود ٥٠٦٨\nhttps://sunnah.com/abudawud:5068",
    "بەری نڤستنێ": "بِاسْمِكَ اللَّهُمَّ أَمُوتُ وَأَحْيَا\n\nخودایێ من، ب ناڤێ تە ئەز دمرم و دژیم.\nصحيح البخاري ٦٣٢٤\nhttps://sunnah.com/bukhari:6324",
    "پشتی ڕابوونێ": "الْحَمْدُ لِلَّهِ الَّذِي أَحْيَانَا بَعْدَ مَا أَمَاتَنَا وَإِلَيْهِ النُّشُورُ\n\nستایش بۆ خودێ یە کو پشتی مرنێ ژیان دا مە، و ڤەژینا مە بەرەڤ وی یە.\nصحيح البخاري ٦٣٢٤\nhttps://sunnah.com/bukhari:6324",
})
MY_DUAS = "دووعایێن من"
DUA_MENU = [["سپێدێ","ئێڤارێ"],["بەری نڤستنێ","پشتی ڕابوونێ"],list(DUAS)[:2],[MY_DUAS,BACK]]
DUA_ADD, DUA_DEL = "دووعایێ هەلگرە", "دووعایێ ژ لیستێ ڕابکە"

TOPICS = ["ڕیزا سوورەتان","ژمارا ئایەتان","قورئان و دووعا"]
REVIEW = "دووبارەکرنا خەلەتیان"
NEXT = "پرسیارا دی"
QUIZ_MENU = [[TOPICS[0], TOPICS[1]],[TOPICS[2], REVIEW],[BACK]]
EXPLANATIONS = ["ل موصحەفێ، الفاتحة سوورەتا ئێکێیە.", "سوورەتا الناس ژمارا ١١٤یە و ل دوماهییا موصحەفێ یە.", "ل ئایەتا ١١٤ ژ طه، داخوازا زێدەبوونا زانینێ هاتیە کرن.", "الناس پشتی الفلق دهێت و دوماهیک سوورەتە.", "ئایەتا شەشێ ژ الشرح بەحسێ ئاسانیێ دگەل تەنگاڤیێ دکەت."]
def question(topic, index):
    if topic == TOPICS[2]:
        i = index % len(QUIZ)
        q, opts, answer, ref = QUIZ[i]
        return q, opts, answer, EXPLANATIONS[i], ref
    n = (index * 37) % 114 + 1
    name, length = SURAHS[n-1], LENGTHS[n-1]
    if topic == TOPICS[0]:
        answer = name
        opts = [answer, SURAHS[n%114], SURAHS[(n+16)%114]]
        prompt = f"سوورەتا ژمارە {n} کیژە؟"
    else:
        answer = str(length)
        opts = [answer, str(length+1), str(length+3)]
        prompt = f"سوورەتا {name} چەند ئایەت هەنە؟"
    k = index % 3
    return prompt, opts[k:]+opts[:k], answer, f"{name} سوورەتا ژمارە {n}یە و {length} ئایەت هەنە.", str(n)

def quiz_action(v,s):
    if v in (QUIZ_BTN,"/quiz"):
        s["mode"] = "quiz_topics"
        return "بابەتەکێ هەلبژێرە.", QUIZ_MENU
    if v in TOPICS or v in (NEXT,REVIEW):
        topic = s.get("quiz_topic",TOPICS[0]) if v == NEXT else v
        s["quiz_topic"] = topic
        if topic == REVIEW:
            if not s.get("mistakes"):
                return "هەمی پرسیارێن خەلەت هاتنە دووبارەکرن یان هێشتا چ خەلەتی نینن.", QUIZ_MENU
            key = s["mistakes"][0]
        else:
            key = [topic,s.get("quiz_progress",{}).get(topic,0)]
        s.update(mode="question", question_key=key)
        prompt, opts, *_ = question(*key)
        return prompt, [[o] for o in opts]+[[BACK]]
    if s.get("mode") == "question":
        key = s["question_key"]
        _, opts, answer, why, ref = question(*key)
        if v.isdecimal() and len(v)<=4:
            v = next((o for o in opts if o.isdecimal() and int(o)==int(v)), v)
        if v not in opts:
            return None
        correct = v == answer
        mistakes = s.setdefault("mistakes",[])
        if key in mistakes:
            mistakes.remove(key)
        if not correct:
            mistakes.append(key)
        topic, i = key
        if s["quiz_topic"] != REVIEW:
            length = len(QUIZ) if topic == TOPICS[2] else 114
            s.setdefault("quiz_progress",{})[topic] = (i+1)%length
        s["answered"] = s.get("answered",0)+1
        s["right"] = s.get("right",0)+int(correct)
        s["mode"] = None
        return ("بەرسڤا تە دروستە." if correct else f"بەرسڤا دروست • {answer}") + f"\n{why}\nhttps://quran.com/{ref}", [[NEXT,QUIZ_BTN],[REVIEW,BACK]]

def prayer_card(s):
    city = s.get("city")
    if city not in CITIES:
        s["mode"] = "city"
        return "باژێرێ خۆ هەلبژێرە.", [list(CITIES)[:2], list(CITIES)[2:], [BACK]]
    now = datetime.now(IRAQ)
    times = TIMES[CITIES[city]][now.strftime("%m-%d")]
    s["mode"] = None
    lines = [f"{name}   {clock}" for name,clock in zip(PRAYERS,times)]
    return f"{city} · {now.date()} · دەمێ عێراقێ\n\n"+"\n".join(lines)+"\n\nژێدەر • بانگ\nhttps://bang-kurdistan.github.io/", [[ALERTS,CITY],[BACK]]

def additions(v,s):
    mode = s.get("mode")
    if v in (GOAL,"/goal"):
        s["mode"]="goal"
        return goal_line(s)+"\nئامانجا خۆ بنێرە (١–٦٢٣٦ ئایەت).", GOAL_MENU
    if mode=="goal" and v.isdecimal() and len(v)<=4 and 1<=int(v)<=6236:
        s.update(goal=int(v),mode=None)
        return goal_line(s), [[RESUME,GOAL],[BACK]]
    if v in (PRAYER,"/prayer"):
        return prayer_card(s)
    if v == CITY:
        s["mode"]="city"
        return "باژێرێ خۆ هەلبژێرە.", [list(CITIES)[:2],list(CITIES)[2:],[BACK]]
    if mode=="city" and v in CITIES:
        s["city"]=v
        return prayer_card(s)
    if v==ALERTS or mode=="alerts" and v.removeprefix("✓ ") in PRAYERS:
        if not s.get("city"):
            return prayer_card(s)
        selected=s.setdefault("alerts",[])
        name=v.removeprefix("✓ ")
        if name in PRAYERS:
            if name in selected: selected.remove(name)
            else: selected.append(name)
        s["mode"]="alerts"
        buttons=[("✓ " if n in selected else "")+n for n in PRAYERS]
        return "نڤێژەکێ لێ بدە بۆ چالاککرن یان وەستاندنێ. نیشانا ✓ واتە چالاکە.\n"+s["city"], [buttons[:2],buttons[2:4],buttons[4:],[PRAYER,BACK]]
    if v in ("دووعا","/dua","زیکر","/dhikr"):
        s["mode"]="dua"
        if v in ("زیکر","/dhikr"):
            return reply("زیکر")[0]+"\nhttps://sunnah.com/muslim:2137a\n\nبۆ زیکرێن دەمان، دەمەکێ هەلبژێرە.", DUA_MENU
        return "دووعایەکێ هەلبژێرە.", DUA_MENU
    if v==MY_DUAS:
        s["mode"]="dua"
        return "دووعایێن تە یێن هەلگرتی" if s.get("dua_marks") else "هێشتا دووعایەک نەهاتیە هەلگرتن.", [[k] for k in s.get("dua_marks",[])]+[["دووعا",BACK]]
    if v in DUAS and mode in ("dua","dua_card",None):
        s.update(mode="dua_card",dua_title=v)
        return DUAS[v], [[DUA_DEL if v in s.get("dua_marks",[]) else DUA_ADD,MY_DUAS],["دووعا",BACK]]
    if mode=="dua_card" and v in (DUA_ADD,DUA_DEL):
        marks=s.setdefault("dua_marks",[])
        k=s["dua_title"]
        if v==DUA_ADD and k not in marks: marks.append(k)
        if v==DUA_DEL and k in marks: marks.remove(k)
        return additions(k,s)
    if mode=="goal" and v not in {k for row in MENU for k in row} and v!=BACK and not v.startswith("/"):
        return "ژمارەیەکێ ژ ١ تا ٦٢٣٦ بنێرە.", GOAL_MENU
    return quiz_action(v,s)

def prayer_alerts(db,token):
    now=datetime.now(IRAQ)
    today=now.date().isoformat()
    minute=now.hour*60+now.minute
    for city, in db.execute("SELECT DISTINCT city FROM prayer_subs").fetchall():
        for name, clock in zip(PRAYERS,TIMES[CITIES[city]][now.strftime("%m-%d")]):
            h,m=map(int,clock.split(":"))
            if not 0<=minute-(60*h+m)<=4:
                continue
            rows=db.execute("SELECT chat FROM prayer_subs WHERE city=? AND name=? AND day<>? LIMIT 40",(city,name,today)).fetchall()
            for chat, in rows:
                with db:
                    claimed=db.execute("UPDATE prayer_subs SET day=? WHERE chat=? AND name=? AND day<>?",(today,chat,name,today)).rowcount
                if not claimed: continue
                try:
                    api(token,"sendMessage",chat_id=chat,text=f"دەمێ نڤێژا {name} • {city} • {clock}\nژێدەر • بانگ",reply_markup={"keyboard":[[ALERTS,PRAYER],[BACK]],"resize_keyboard":True})
                except TelegramError as e:
                    if e.code==403:
                        with db:
                            db.execute("DELETE FROM prayer_subs WHERE chat=?",(chat,))
                            row=db.execute("SELECT state FROM users WHERE chat=?",(chat,)).fetchone()
                            if row:
                                state=json.loads(row[0])
                                state["alerts"]=[]
                                db.execute("UPDATE users SET state=? WHERE chat=?",(json.dumps(state),chat))
                    elif e.code==429 or e.code>=500:
                        with db: db.execute("UPDATE prayer_subs SET day='' WHERE chat=? AND name=?",(chat,name))
                        raise
                    elif e.code!=400: raise

JUZ = "جوزێن قورئانێ"
HIFZ = "حەفز و دووبارەکرن"
ADD_VERSE = "ئایەتەکێ زێدە بکە"
REVIEW_DAY = "دووبارەکرنا ئەڤڕۆ"
REVEAL = "ئایەتێ نیشان بدە"
AGAIN = "پێدڤی ب ڕاهێنانێ هەیە"
REMEMBERED = "من ژبەر گوت"
REMOVE_VERSE = "ژ حەفزێ ڕابکە"
HIFZ_MENU = [[REVIEW_DAY, ADD_VERSE], [BACK]]
MENU.insert(2, [JUZ, HIFZ])
JUZ_STARTS = [[1, 1], [2, 142], [2, 253], [3, 93], [4, 24], [4, 148], [5, 82], [6, 111], [7, 88], [8, 41], [9, 93], [11, 6], [12, 53], [15, 1], [17, 1], [18, 75], [21, 1], [23, 1], [25, 21], [27, 56], [29, 46], [33, 31], [36, 28], [39, 32], [41, 47], [46, 1], [51, 31], [58, 1], [67, 1], [78, 1]]
HIFZ_GAPS = (1, 3, 7, 14, 30)

def load_verse_text():
    verses = {}
    filename = os.path.join(os.path.dirname(__file__), "web", "quran.txt")
    with open(filename, encoding="utf-8") as source:
        for line in source:
            parts = line.rstrip("\r\n").split("|", 2)
            if len(parts) == 3 and parts[0].isdecimal():
                verses[parts[0] + ":" + parts[1]] = parts[2]
    return verses

VERSE_TEXT = load_verse_text()

def verse_name(key):
    c, v = map(int, key.split(":"))
    return f"{SURAHS[c-1]} · ئایەتا {v}"

def verse_body(key):
    c, v = map(int,key.split(":"))
    return (f"{verse_name(key)}\n\n{VERSE_TEXT[key]}\n\n"
            f"خواندن • https://quran.com/{c}/{v}\n"
            f"گوهداری • https://everyayah.com/data/Alafasy_128kbps/{c:03}{v:03}.mp3")

def study_action(v, s):
    mode = s.get("mode")
    today = datetime.now(IRAQ).date()
    if v in (JUZ,"/juz"):
        s["mode"] = "juz"
        buttons = [str(n) for n in range(1,31)]
        return "جوزەکێ ژ ١ تا ٣٠ هەلبژێرە.", [buttons[n:n+5] for n in range(0,30,5)]+[[BACK]]
    if v.startswith("/juz ") or mode=="juz" and v.isdecimal():
        number = v.split()[-1]
        if len(number)>2 or not number.isdecimal() or not 1<=int(number)<=30:
            return "ژمارا جوزێ ژ ١ تا ٣٠ بنێرە.", [[JUZ,BACK]]
        n = int(number)
        c, a = JUZ_STARTS[n-1]
        return f"جوز {n}\n\n{verse_body(f'{c}:{a}')}", [[JUZ,HIFZ],[BACK]]
    if v in (HIFZ, "/hifz", REVIEW_DAY):
        deck = s.get("hifz",{})
        due = sorted((item["due"],key) for key,item in deck.items() if item["due"]<=today.isoformat())
        s["mode"]="hifz"
        if v==REVIEW_DAY and due:
            key = due[0][1]
            s.update(mode="recall", hifz_key=key)
            return f"{verse_name(key)}\n\nجارەکێ ژبەر بێژە، پاشی ئایەتێ ڤەکە.", [[REVEAL],[HIFZ,BACK]]
        next_day = min((item["due"] for item in deck.values()), default=None)
        summary = f"ئایەتێن من • {len(deck)}\nبۆ دووبارەکرنا ئەڤڕۆ • {len(due)}"
        if next_day and not due:
            summary += f"\nدووبارەکرنا داهاتی • {next_day}"
        return summary,HIFZ_MENU
    if v==ADD_VERSE:
        s["mode"]="hifz_add"
        return "سوورەت و ئایەتێ بنێرە، وەک ١٨:١٠.", [[HIFZ,BACK]]
    if mode=="hifz_add" and not v.startswith("/") and v not in {b for row in MENU for b in row} and v!=BACK:
        pair=re.fullmatch(r"(\d{1,3})\s*[:/]\s*(\d{1,3})",v)
        key=":".join(str(int(n)) for n in pair.groups()) if pair else ""
        if key not in VERSE_TEXT:
            return "ئایەت نەهاتە دیتن. ژماران بپشکنە، وەک ١٨:١٠.", [[HIFZ,BACK]]
        deck=s.setdefault("hifz",{})
        deck.setdefault(key,{"due":today.isoformat(),"level":0})
        s.update(mode="study_card",hifz_key=key)
        return verse_body(key),[[REVIEW_DAY,ADD_VERSE],[REMOVE_VERSE,HIFZ],[BACK]]
    key=s.get("hifz_key")
    if key not in s.get("hifz",{}):
        return None
    if mode=="recall" and v==REVEAL:
        s["mode"]="grade"
        return verse_body(key),[[REMEMBERED,AGAIN],[REMOVE_VERSE,HIFZ],[BACK]]
    if mode=="grade" and v in (REMEMBERED,AGAIN):
        item=s["hifz"][key]
        level=item["level"] if v==REMEMBERED else 0
        item["due"]=(today+timedelta(days=HIFZ_GAPS[level])).isoformat()
        item["level"]=min(level+1,len(HIFZ_GAPS)-1) if v==REMEMBERED else 0
        s["mode"]="hifz"
        return f"{verse_name(key)}\nدووبارەکرنا داهاتی • {item['due']}", HIFZ_MENU
    if mode in ("grade","study_card") and v==REMOVE_VERSE:
        del s["hifz"][key]
        s["mode"]="hifz"
        return "ئایەت ژ لیستا حەفزا تە هاتە ڕاکرن.", HIFZ_MENU


LESSONS = "پەرتووکخانا دینی"
LESSON_TOPICS = {
    "فەرموودێن پێغەمبەری ﷺ": {
        "نیەت و کار": "«إِنَّمَا الأَعْمَالُ بِالنِّيَّاتِ»\nمانا • بهایێ کاری گرێدای نیەتا مرۆڤییە.\nڤەگوهێز • عومەرێ کورێ خەتتاب\nژێدەر • صحیح البخاري، ١\nhttps://sunnah.com/bukhari:1",
        "پەیڤا باش و مێهڤانداری": "«فَلْيَقُلْ خَيْرًا أَوْ لِيَصْمُتْ»\nمانا • پەیڤا خێرێ بێژە یان بێدەنگ بمینە. د هەمان فەرموودەیێ دا ڕێزگرتنا مێهڤانی و زیان نەگەهاندنا جیرانی ژی هاتیە باسکرن.\nڤەگوهێز • ئەبو هورەیرە\nژێدەر • صحیح البخاري، ٦٠١٨\nhttps://sunnah.com/bukhari:6018",
        "ڕاستگۆیی د بازرگانیێ دا": "کورتەمانا • ئەگەر کریار و فرۆشیار ڕاستیێ بێژن و عەیبێن کالایێ دیار بکەن، بەرەکەت د مامەڵەیا وان دا دهێتە دانان.\nڤەگوهێز • حەکیمێ کورێ حیزام\nژێدەر • صحیح البخاري، ٢٠٧٩\nhttps://sunnah.com/bukhari:2079",
    },
    "خوارن و ڤەخوارن": {
        "خوارن و ڤەخوارنێن حەلال": "ئاو، میوە و سەوزەیێن پاک نموونەیێن خوارن و ڤەخوارنا حەلالن. قورئان بانگەوازێ دکەت کو مرۆڤ ژ تشتێن حەلال و پاک بخۆت.\nالبقرة · ١٦٨\nhttps://quran.com/2/168",
        "خوارنێن حەرام و ناچاری": "گوشتێ بەرازی و ئاژەلێ ب خۆ مری ژ نموونەیێن قەدەغەکرینە. هەمان ئایەت حوکمێ ناچارییێ ژی باس دکەت، ب مەرجێ مرۆڤ ژ پێدڤییێ دەرنەچیت.\nالبقرة · ١٧٣\nhttps://quran.com/2/173",
        "ڤەخوارنێن سەرخۆشکەر": "د قورئانێ دا فەرمان هاتیە دان کو باوەردار ژ خەمرێ دویر بکەڤن. شەراب ژ نموونەیێن وێیە.\nالمائدة · ٩٠\nhttps://quran.com/5/90",
    },
    "کار و داهات": {
        "بازرگانیا حەلال": "کرین و فرۆتنا کالایەکا حەلال ب ڕەزامەندیا هەردوو لایان ڕێپێدایە. بۆ نموونە، د مارکێتێ دا نرخ و کێشا کالایێ ب ڕوونی ب کریاری بدە زانین.\nالنساء · ٢٩\nhttps://quran.com/4/29",
        "کێش و پێڤانا دروست": "ئەگەر تە ئێک کیلۆ فرۆت، ئێک کیلۆیا تەمام بدە. قورئان فەرمانێ ب تەمامکرنا پێڤانێ و کێشانا ب دادپەروەری دکەت.\nالإسراء · ٣٥\nhttps://quran.com/17/35",
        "ڕیبا": "د قورئانێ دا بازرگانی حەلال و ڕیبا حەرام هاتیە دانان. بۆ زانینا حوکمێ گرێبەستەکا دیارکری، مەرجێن گرێبەستێ پێدڤینە.\nالبقرة · ٢٧٥\nhttps://quran.com/2/275",
    },
    "بیدعە": {
        "بیدعە د عیبادەتێ دا": "کورتەمانایا فەرموودەیێ • هەر کەس تشتەکی بخەتە ناڤ دینێ مە کو ژ وی نینە، ئەو تشتە دهێتە ڕەتکرن.\nڤەگوهێز • عائیشە، دایکا باوەداران\nژێدەر • صحیح مسلم، ١٧١٨a\nhttps://sunnah.com/muslim:1718a",
        "نموونە و جوداهیا بۆچوونان": "نموونە • ئەگەر کەسەک بێژیت نڤێژەکا شەشێ ل هەر موسلمانەکی هەر ڕۆژ فەرزە، وی فەرزەکا نوی بێ بەڵگە دانایە. زانا د پێناسەیا بیدعە و سەپاندنا وێ ل سەر هندەک کاران دا جودا دبن. بۆ کارەکێ دیارکری، بەڵگە و شروڤەیا زانایان بپرسە.\nhttps://sunnah.com/muslim:1718a",
    },
    "کارێن مەکرووهـ": {
        "مەکرووهـ چ مانایە؟": "د بەکارهێنانا گشتی یا فقهێ دا، مەکرووهـ کارەکە کو بهێلن باشترە. د فقهێ حەنەفی دا جوداهی د ناڤبەرا مەکرووهێ تەحریمی و تەنیزیهی دا هەیە، لەوما پلەیا حوکمی ژی گرنگە.\nنموونە ژ فەرموودەیێ\nhttps://sunnah.com/bukhari:568",
        "نڤستن بەری نڤێژا عەیشایێ": "ئەبو بەرزەی ڤەگوهێرایە کو پێغەمبەر ﷺ حەز ژ نڤستنێ بەری نڤێژا عەیشایێ و ئاخفتنێ پشتی وێ نەدکر. نموونەیەکا ڕۆژانە ئەوە کو مرۆڤ ب گفتوگۆیەکا بێ پێدڤی شەڤێ درێژ بکەت.\nژێدەر • صحیح البخاري، ٥٦٨\nhttps://sunnah.com/bukhari:568",
    },
    "کارێن ب زیان": {
        "قومار و دوژمنایەتی": "قورئان باس دکەت کو خەمر و قومار دبنە ئەگەرێ دوژمنایەتی و کینێ و مرۆڤی ژ زیکر و نڤێژێ دویر دکەن.\nالمائدة · ٩١\nhttps://quran.com/5/91",
        "غیبەت و سیخوڕی": "ل عەیبێن ڤەشارتی یێن خەلکی نەگەڕە و ل پشت کەسەکی ئاخفتنا خراب ل سەر وی نەکە. ئایەت هەردوو کاران باس دکەت.\nالحجرات · ١٢\nhttps://quran.com/49/12",
    },
    "مافێن دایک و باب و جیرانان": {
        "جوانی دگەل دایک و بابی": "دەمێ دایک یان باب پیر دبن، ب نەرماتی دگەل وان باخڤە. ئایەت هەتا ژ گوتنا «ئوف» ب وان ژی نەهی دکەت.\nالإسراء · ٢٣\nhttps://quran.com/17/23",
        "مافێ جیرانی": "کورتەمانا • پێغەمبەر ﷺ شیرەت کریە کو مرۆڤ زیانێ نەگەهینیتە جیرانێ خۆ. بۆ نموونە، ڕێکا دەرگەهێ وی ڤەکری بهێلە.\nڤەگوهێز • ئەبو هورەیرە\nصحیح البخاري، ٦٠١٨\nhttps://sunnah.com/bukhari:6018",
    },
    "ئەدەبێ سۆشیال میدیایێ": {
        "بەری بڵاڤکرنێ": "ئەگەر نووچەیەکا گومانلێکری گەهشتە تە، بەری هنارتنا وێ بۆ گرووپێ، ژێدەرێ بپشکنە. ئایەت ئاگەهداریێ ددەت کو مرۆڤ ب نەزانی زیانێ نەگەهینیتە خەلکی.\nالحجرات · ٦\nhttps://quran.com/49/6",
        "ڕێز د کومێنتان دا": "گاڵتەیێ ب خەلکی نەکە و ناڤێن کرێت ل وان مەکە. ئەڤ ئەدەبە د کومێنت و گرووپێن تێلیگرامێ دا ژی دهێتە بکارئینان.\nالحجرات · ١١\nhttps://quran.com/49/11",
    },
}

MENU.insert(0, [LESSONS, practice.HUB])


def lesson_action(text, state):
    if text in (LESSONS, "/learn"):
        state.update(mode="lessons", lesson_topic=None)
        names = list(LESSON_TOPICS)
        return "تو دڤێی دەربارەی چ بخوینی؟", [names[i:i+2] for i in range(0, len(names), 2)] + [[BACK]]
    if state.get("mode") != "lessons":
        return None
    if text in LESSON_TOPICS:
        state["lesson_topic"] = text
        return text + "\nبابەتەکێ هەلبژێرە.", [[name] for name in LESSON_TOPICS[text]] + [[LESSONS, BACK]]
    topic = LESSON_TOPICS.get(state.get("lesson_topic"), {})
    if text in topic:
        state["last_lesson"] = text
        extra = [[practice.TEST]] if any(case[0] == text for case in practice.CASES) else []
        return text + "\n\n" + topic[text], extra + [[name] for name in topic] + [[LESSONS, BACK]]
    if text.startswith("/") or text == BACK or any(text in row for row in MENU):
        state["mode"] = None
        return None
    return lesson_action(LESSONS, state)


def route(text, s):
    lesson = lesson_action(text.strip(), s)
    if lesson is not None:
        return lesson
    result = study_action(text.strip(),s)
    if result is not None:
        return result
    result = additions(text.strip(),s)
    if result is not None:
        return result
    result = reading_action(text, s)
    if result is not None:
        return result
    v = text.strip()
    cmd, _, arg = v.partition(" ")
    cmd = cmd.split("@")[0].lower()
    mode = s.get("mode")
    s["mode"] = None
    if cmd == "/quran" or v == QURAN:
        mode = "quran"
        v = arg.strip() if cmd == "/quran" else ""
    if v in (AYAH, "/ayah"):
        day = datetime.now(timezone(timedelta(hours=3))).date()
        a, k, ref = DAILY[day.toordinal() % len(DAILY)]
        return f"{AYAH} · {day}\n\n{a}\n\n{k}\nhttps://quran.com/{ref}", MENU
    if v in (COUNTER, "/tasbih") or mode == "count" and v in COUNTS[0]:
        s["mode"] = "count"
        s["count"] = s.get("count", 0) + {"+١": 1, "+١٠": 10}.get(v, 0)
        return f"تەسبیح\nژمارا زیکرێن تە • {s['count']}\nپشتی زیکرێ دوگمەیەکێ هەلبژێرە.", COUNTS
    if v in (PROFILE, "/profile"):
        return f"پێشکەفتنا تە\n{goal_line(s)}\n\nتەسبیح • {s.get('count', 0)}\nبەرسڤێن دروست • {s.get('right', 0)} / {s.get('answered', 0)}\nسوورەتێن نیشانکری • {len(s.get('marks', []))}", MENU
    if v in (QUIZ_BTN, "/quiz") or mode == "quiz" and v in QUIZ[s.get("answered",0) % len(QUIZ)][1]:
        i = s.get("answered", 0)
        q, opts, answer, ref = QUIZ[i % len(QUIZ)]
        if mode == "quiz" and v in opts:
            correct = v == answer
            s["answered"] = i + 1
            s["right"] = s.get("right", 0) + int(correct)
            result = "بەرسڤا تە دروستە." if correct else "بەرسڤا دروست • " + answer
            return f"{result}\nhttps://quran.com/{ref}", [[QUIZ_BTN], [BACK]]
        s["mode"] = "quiz"
        return q, [[o] for o in opts] + [[BACK]]
    if v in (MARKS, "/saved"):
        marks = s.get("marks", [])
        if not marks:
            return "هێشتا چ سوورەت نیشان نەکرینە. سوورەتەکێ ڤەکە و «نیشان بکە» هەلبژێرە.", [[QURAN], [BACK]]
        s["mode"] = "quran"
        return "سوورەتەکێ هەلبژێرە.", [[SURAHS[n-1]] for n in marks] + [[BACK]]
    if mode == "surah" and v in (SAVE, "نیشانێ ڕابکە"):
        n = s["surah"]
        marks = s.setdefault("marks", [])
        if v == SAVE and n not in marks: marks.append(n)
        if v != SAVE and n in marks: marks.remove(n)
        return "لیستا تە هاتە نوێکرن.", [[MARKS, QURAN], [BACK]]
    if mode == "quran" and v not in {k for row in MENU for k in row} and v != BACK and not v.startswith("/"):
        s["mode"] = "quran"
        matches = [i for i,name in enumerate(SURAHS,1) if normalize(name) == normalize(v)]
        number = int(v) if v.isdecimal() and len(v)<=3 else next(iter(matches),0)
        if 1 <= number <= len(SURAHS):
            s.update(mode="surah", surah=number)
            action = "نیشانێ ڕابکە" if number in s.get("marks",[]) else SAVE
            return f"سوورەتا {SURAHS[number-1]} · {number}\n\nخواندن و گوهداریکرن\nhttps://quran.com/{number}", [[action, QURAN], [BACK]]
        return "ناڤێ سوورەتێ ب عەرەبی یان ژمارەیەکێ ژ ١ تا ١١٤ بنێرە.", [["الفاتحة", "الكهف", "يس"], [BACK]]
    return reply(text)

INVITE = "ڕووناهی ب هەڤالان بناسینە"
MENU.append([INVITE])
CHANNELS = {"friend":"تێلیگرام","snap":"سنەپچات","insta":"ئینستاگرام"}
def invite_card(db,chat,username):
    row = db.execute("SELECT code FROM invite_links WHERE chat=?", (chat,)).fetchone()
    if row:
        code = row[0]
    else:
        code = secrets.token_hex(10)
        db.execute("INSERT INTO invite_links VALUES (?,?)", (chat,code))
    totals = dict(db.execute("SELECT source,count(*) FROM joins WHERE code=? GROUP BY source",(code,)))
    lines = ["لینکێ هەر شوێنەکێ ل هەمان شوێن بڵاڤ بکە. ژمارە کەسێن نوی نیشان ددەت کو ب لینکێ تە دەست پێ کرین."]
    for source, label in CHANNELS.items():
        link = f"https://t.me/{username}?start=r_{code}_{source}"
        lines.append(f"{label} • {totals.get(source,0)}\n{link}")
    share = "https://t.me/share/url?" + urlencode({"url":f"https://t.me/{username}?start=r_{code}_friend","text":"ڕووناهی • دەمێن نڤێژان و خواندنا قورئانێ ب کوردیا بادینی"})
    return "\n\n".join(lines), {"inline_keyboard":[[{"text":"بۆ هەڤالەکێ بنێرە","url":share}]]}

def track_join(db,chat,text):
    match = re.fullmatch(r"/start(?:@\w+)?\s+r_([a-f0-9]{20})_(friend|snap|insta)",text.strip())
    if match:
        code,source = match.groups()
        db.execute("INSERT OR IGNORE INTO joins(chat,code,source) SELECT ?,code,? FROM invite_links WHERE code=? AND chat<>?",(chat,source,code,chat))


GEMINI_CHAT = "چاتا Gemini"
MENU.insert(0, [ai.BUTTON, plus_shop.PLUS])
MENU.insert(0, [GEMINI_CHAT])


PASSAGES = ai.passage_index(VERSE_TEXT)

def remember_exchange(state, question, answer):
    state["ai_history"] = (state.get("ai_history", []) + [[question[:4096], answer if len(answer)<=4800 else answer[:1800]+" […] "+answer[-3000:]]])[-8:]


def quoted_result(quote, state):
    hits = ai.find_passage(quote, PASSAGES)
    if not hits:
        return "جهێ ئەڤێ پارچەیێ ب دڵنیایی نەهاتە دیتن. چەند پەیڤێن دی ژ ئایەتێ بنێرە.", [[BACK]]
    if len(hits) > 1:
        links = [f"{verse_name(f'{c}:{v}')}  https://quran.com/{c}/{v}" for c,v,_ in hits]
        return "ئەڤ پارچەیە ل چەند جهان هاتیە دیتن. لینکەکێ ڤەکە یان چەند پەیڤێن دی بنێرە.\n\n" + "\n".join(links), [[BACK]]
    c, first, last = hits[0]
    state["mode"] = "ai"
    span = str(first) if first == last else f"{first}–{last}"
    lines = [VERSE_TEXT[f"{c}:{v}"] for v in range(first, min(first+4,last+1))]
    answer = f"سوورەتا {SURAHS[c-1]} · {span}\n\n" + "\n".join(lines) + f"\n\nخواندن • https://quran.com/{c}/{first}"
    remember_exchange(state, quote, answer)
    return answer, [[BACK]]


OCCASION = "دووعا لدویڤ بارودۆخی"
# title, Arabic text, Badini meaning, source, common phrases
OCCASIONS = {
    "travel": ("دەستپێکا سەفەرێ", "اللَّهُمَّ هَوِّنْ عَلَيْنَا سَفَرَنَا هَذَا وَاطْوِ عَنَّا بُعْدَهُ", "خودایێ مە، ئەڤ سەفەرە ل مە ئاسان بکە و دوورییا وێ بۆ مە کورت بکە. ئەڤە بەشەکە ژ دووعایا درێژ یا سەفەرێ.", "صحیح مسلم · ١٣٤٢\nhttps://sunnah.com/muslim:1342", ("ئەز دچمە سەفەرێ","دووعایا سەفەرێ","دعاء السفر","سەفەر")),
    "sleep": ("بەری نڤستنێ", "بِاسْمِكَ اللَّهُمَّ أَمُوتُ وَأَحْيَا", "خودایێ من، ب ناڤێ تە ئەز دمرم و دژیم.", "صحیح البخاري · ٦٣٢٤\nhttps://sunnah.com/bukhari:6324", ("بەری نڤستنێ چ بخوینم","ئەز دچمە نڤستنێ","دعاء النوم","پێش خەوتن")),
    "wake": ("پشتی هشیاربوونێ ژ خەوێ", "الْحَمْدُ لِلَّهِ الَّذِي أَحْيَانَا بَعْدَ مَا أَمَاتَنَا وَإِلَيْهِ النُّشُورُ", "هەمی ستایش بۆ خودێیە، ئەوێ پشتی مرنێ مە ساخ کرینەڤە، و ڕابوونا مە بەرەڤ وییە.", "صحیح البخاري · ٦٣٢٤\nhttps://sunnah.com/bukhari:6324", ("ئەز ژ خەوێ هشیار بووم","پشتی خەوێ","دعاء الاستيقاظ")),
    "mosque_in": ("چوونە ژوور یا مزگەفتێ", "اللَّهُمَّ افْتَحْ لِي أَبْوَابَ رَحْمَتِكَ", "خودایێ من، دەرگەهێن ڕەحما خۆ بۆ من ڤەکە.", "صحیح مسلم · ٧١٣a\nhttps://sunnah.com/muslim:713a", ("ئەز دچمە مزگەفتێ","دخول المسجد")),
    "mosque_out": ("دەرکەفتن ژ مزگەفتێ", "اللَّهُمَّ إِنِّي أَسْأَلُكَ مِنْ فَضْلِكَ", "خودایێ من، ئەز ژ قەنجی و فەزلا تە دخوازم.", "صحیح مسلم · ٧١٣a\nhttps://sunnah.com/muslim:713a", ("ئەز ژ مزگەفتێ دەردکەڤم","الخروج من المسجد")),
    "worry": ("دەمێ خەم و کەسەرێ", "اللَّهُمَّ إِنِّي أَعُوذُ بِكَ مِنَ الْهَمِّ وَالْحَزَنِ", "خودایێ من، ئەز ژ خەم و کەسەرێ پەنا ب تە دبەم. ئەڤە دەستپێکا دووعایێیە.", "صحیح البخاري · ٦٣٦٩\nhttps://sunnah.com/bukhari:6369", ("دووعایا خەمێ","ئەز خەمگینم","دعاء الهم")),
}
MENU.insert(1, [OCCASION, plus_shop.DONATE])


def occasion_menu():
    titles = [item[0] for item in OCCASIONS.values()]
    return "بارودۆخێ خۆ هەلبژێرە یان بنڤیسە، وەک «ئەز دچمە سەفەرێ».", [titles[i:i+2] for i in range(0,len(titles),2)] + [[BACK]]


def occasion_card(key, state, question):
    title, arabic, meaning, source, _ = OCCASIONS[key]
    body = f"{title}\n\n{arabic}\n\nمانا ب بادینی\n{meaning}\n\n{source}"
    if state.get("mode") == "ai":
        remember_exchange(state,question,body)
    return body, [[OCCASION,BACK]]


def occasion_action(text,state):
    if text in (OCCASION,"/duas"):
        state["mode"]="occasions"
        return occasion_menu()
    mode=state.get("mode")
    if mode not in (None,"ai","occasions") or not text:
        return None
    query=practice.norm(text)
    for key,(title,_,_,_,phrases) in OCCASIONS.items():
        if any(query==practice.norm(phrase) for phrase in (title,*phrases)):
            return occasion_card(key,state,text)
    if mode=="occasions":
        if text.startswith("/") or text==BACK or any(text in row for row in MENU):
            state["mode"]=None
        else:
            return occasion_menu()


def continue_fatiha(text,state):
    # During an outage, continue only a clearly established Al-Fatiha lesson.
    history=state.get("ai_history", [])
    phrases=("یا باش وی بکە","چ تشتێ باش بیت بکە","بەردەوام بە","تو هەلبژێرە")
    if practice.norm(text) not in {practice.norm(p) for p in phrases} or not history:
        return None
    last=history[-1][1]
    if "الفاتحة" not in last or not any(w in last for w in ("فێر","ئایەت","دەرس","تجوید","تجويد","مامۆستا")):
        return None
    n=1
    for i in range(1,8):
        if last.startswith(f"وانەیا الفاتحة · {i}\n"):
            n=i+1
            break
    if n>7:
        answer="تە هەر حەفت ئایەتێن الفاتحة خواندن. نوکە سوورەتێ ژبەر بخوینە و پاشی دگەل دەقی بەراورد بکە.\nhttps://quran.com/1"
    else:
        answer=f"وانەیا الفاتحة · {n}\n\n"+verse_body(f"1:{n}")+"\n\nپێشێ گوهداریێ بکە. پاشی ئایەتێ دوو جاران بخوینە و جارەکێ ژبەر بێژە. دەمێ ئامادە بی، بنڤیسە «یا باش وی بکە» بۆ هەنگاڤا دی."
    remember_exchange(state,text,answer)
    return answer, [[BACK]]


def assistant_action(message, state, token, targets=(), navigate=None, context="", keyboard=None, chat_followup=False):
    text = message.get("text", "").strip()
    mode = state.get("mode")
    if text == "/new":
        state.pop("ai_history", None)
    if text in (ai.BUTTON, "/ai", "/new"):
        state.pop("ai_clock", None)
        state["mode"] = "ai"
        return ai.HELP, [[BACK]]
    if mode == "ai_confirm":
        clock = state.pop("ai_clock", None)
        state["mode"] = None
        if text == ai.YES and clock:
            state["mode"] = "reminder"
            return reading_action(clock, state)
        if text == BACK or text.startswith("/"):
            return None
        # Free text cancels the pending change and continues the conversation.
        state["mode"] = "ai"
    if not chat_followup and (text.startswith("/") or text in {b for row in MENU for b in row} or text == BACK):
        state["mode"] = None
        return None
    if text and len(text) <= 1200:
        parts = re.split(r"(?:دبێژیت|دبێژت|دبێژێت|تقول|التي فيها|that says)\s*[:،]?", text, flags=re.I)
        if len(parts) > 1 and ai.find_passage(parts[-1], PASSAGES):
            return quoted_result(parts[-1], state)
        if re.fullmatch(r"[\u0600-\u06ff\s]+", text) and ai.find_passage(text, PASSAGES):
            return quoted_result(text, state)
    provider = ai.provider_for(bool(message.get("voice")))
    variable = ai.PROVIDER_KEYS.get(provider)
    key = os.environ.get(variable, "").strip() if variable else None
    if not key:
        return f"بۆ چالاککرنا هاریکاری {variable or 'AI_PROVIDER'} ل Railway بپشکنە.", keyboard or MENU
    voice = message.get("voice")
    if voice and (voice.get("duration", 0) > 60 or voice.get("file_size", 0) > ai.LIMIT):
        return "دەنگەکێ تا ٦٠ چرکە و ٢ مێگابایت بنێرە.", [[BACK]]
    if not voice and not 0 < len(text) <= 4096:
        return "فرمانەکا کورت بنڤیسە یان دەنگەکێ بنێرە.", [[BACK]]
    try:
        part = ai.voice_part(token, voice, api) if voice else {"text": text}
        prompt = ai.PROMPT + "\nFor an explicit request to open a bot feature or select a control, return {\"action\":\"navigate\",\"label\":\"exact available label\"}. Prefer specific structured verse, occasion and timed reminder actions when appropriate. For questions ABOUT a feature answer in chat. Available controls: " + json.dumps(targets,ensure_ascii=False)
        if context:
            prompt += "\nPrevious bot screen (reference only): "+json.dumps(context,ensure_ascii=False)
        history = state.get("ai_history", [])
        if provider == "gemini":
            intent = ai.interpret(part,key,history,prompt=prompt)
        else:
            intent = ai.text_intent(provider,text,key,history,prompt)
    except (OSError, ValueError, IndexError, TypeError, KeyError, TelegramError, subprocess.SubprocessError) as err:
        status=getattr(err,"code",None)
        print("AI request failed:",provider,type(err).__name__,status,flush=True)
        local=continue_fatiha(text,state)
        if local:
            return local
        if status==429:
            reason="خزمەتگوزارێ AI سنوورێ داخوازییان گەهشتییە. پشتی کەمەکێ دووبارە بنێرە."
        elif status in (401,403,404):
            reason="خزمەتگوزارێ AI ل ڤێ ڕێکخستنێ بەردەست نینە. خودانێ بۆتی کلیلا API و ناڤێ مۆدێلێ بپشکنیت."
        else:
            reason="بەرسڤا AI ڤێ جارێ نەگەهشت یان نەهاتە خواندن. ئاخفتنا تە هاتیە پاراستن؛ تو دشێی دووبارە بنێری."
        return reason, keyboard or MENU
    if not isinstance(intent, dict):
        intent = {}
    action = intent.get("action")
    c, v, n = (intent.get(k) for k in ("chapter", "verse", "number"))
    if action == "navigate" and navigate and intent.get("label") in targets:
        return navigate(intent["label"])
    if action == "chat" and isinstance(intent.get("answer"), str) and intent["answer"].strip():
        answer = intent["answer"].strip()
        heard = intent.get("heard")
        question = text or (heard if isinstance(heard, str) else "") or "پەیامەکا دەنگی"
        remember_exchange(state, question, answer)
        state["mode"] = "ai"
        return answer, [[BACK]]
    if action == "occasion" and isinstance(intent.get("key"),str) and intent["key"] in OCCASIONS:
        return occasion_card(intent["key"],state,text or OCCASIONS[intent["key"]][0])
    if action == "find_quote" and isinstance(intent.get("quote"), str):
        return quoted_result(intent["quote"][:600], state)
    if action == "reminder" and isinstance(intent.get("time"), str) and re.fullmatch(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]", intent["time"]):
        clock = intent["time"]
        state.update(mode="ai_confirm", ai_clock=clock)
        return f"هەر ڕۆژ د {clock} ب دەمێ عێراقێ یادا خواندنێ ب تە بینم؟", [[ai.YES], [BACK]]
    if action == "ask_time":
        return "فرمانێ دگەل دەمێ تەمام دووبارە بکە، وەک «هەر ڕۆژ د ٢٠:٠٠ یادا خواندنێ ب من بینە».", [[BACK]]
    if action == "verse" and type(c) is int and type(v) is int and f"{c}:{v}" in VERSE_TEXT:
        state["mode"] = None
        return verse_body(f"{c}:{v}"), MENU
    if action == "surah" and type(c) is int and 1 <= c <= 114:
        return route(f"/quran {c}", state)
    if action == "juz" and type(n) is int and 1 <= n <= 30:
        state["mode"] = None
        return route(f"/juz {n}", state)
    if action in ("prayer", "dua", "dhikr", "resume", "quiz", "hifz", "ayah", "profile"):
        state["mode"] = None
        return route("/" + action, state)
    # A provider may propose an unknown control. Ask for a direct answer once.
    if text:
        plain = "You are Ronahi. Reply directly in natural Badini Kurdish unless another language was requested. Use the conversation to answer the latest message. Give a useful plain-text answer. Do not emit command objects or claim to have performed external actions."
        try:
            if provider == "gemini":
                answer = ai.interpret({"text": text}, key, history, prompt=plain, conversational=True)
            else:
                answer = ai.text_intent(provider, text, key, history, plain)
            if answer.get("action") == "chat" and isinstance(answer.get("answer"), str) and answer["answer"].strip():
                remember_exchange(state, text, answer["answer"])
                state["mode"] = "ai"
                return answer["answer"], [[BACK]]
        except (OSError, ValueError, IndexError, TypeError, KeyError) as err:
            print("AI direct reply failed:", provider, type(err).__name__, getattr(err, "code", None), flush=True)
    return "من نەشیا داخوازیا تە تەمام بکەم. دەتوانی ب پەیڤێن دی بێژی؟", keyboard or MENU


def native_reply(db, message, state, username, token):
    text = message.get("text", "").strip()
    bot = sys.modules[__name__]
    response = plus_shop.handle(db,state,message,token,bot)
    if response is None:
        response = occasion_action(text,state)
    if response is None:
        response = practice.handle(db,state,message,username,token,bot)
    if response is not None:
        return response
    if text in (ai.BUTTON, "/ai", "/new") or state.get("mode") == "ai_confirm":
        response = assistant_action(message,state,token)
        if response is not None:
            return response
    if username and text in (INVITE, "/invite"):
        state["mode"] = None
        return invite_card(db,message["chat"]["id"],username)
    return route(text,state)


def options(rows):
    return [label for row in rows for label in row] if isinstance(rows,list) else []


def gemini_chat(message, state, token):
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        return "ژ بۆ چاتا Gemini، خودانێ بۆتی دڤێت GEMINI_API_KEY ل Railway دانێت.", [[BACK]]
    text = (message.get("text") or message.get("caption") or "").strip()
    parts = []
    try:
        if message.get("photo"):
            parts.append(ai.photo_part(token, message["photo"], api))
        if message.get("voice"):
            voice = message["voice"]
            if voice.get("duration", 0) > 60 or voice.get("file_size", 0) > ai.LIMIT:
                return "دەنگەکێ تا ٦٠ چرکە و ٢ مێگابایت بنێرە.", [[BACK]]
            parts.append(ai.voice_part(token, voice, api))
        if text:
            parts.append({"text": text})
        if not parts:
            return "پرسیارا خۆ بنڤیسە، وێنەیەکێ بنێرە یان ب دەنگ باخڤە.", [[BACK]]
        prompt = ("You are Ronahi, powered by Gemini, in a private Telegram chat. Answer naturally in Kurdish Badini "
                  "in Arabic script by default, or the requested language. Be a general assistant. Use earlier turns "
                  "to continue the topic. When the user delegates a choice, choose and do the work. Respond directly "
                  "to text, photos and voice notes. Be clear about uncertainty and actions you can actually perform.")
        history = state.get("gemini_history", [])
        answer = ai.generate(parts, key, history, prompt, True)
    except (OSError, ValueError, KeyError, TypeError, IndexError, TelegramError, subprocess.SubprocessError) as err:
        status = getattr(err, "code", None)
        print("Gemini chat failed:", type(err).__name__, status, flush=True)
        if status == 429:
            return "سنوورێ داخوازیێن Gemini گەهشتییە. پشتی کەمەکێ دووبارە بنێرە.", [[BACK]]
        if status in (400, 401, 403, 404):
            return "Gemini داخواز وەرنەگرت. خودانێ بۆتی کلیلا API و ناڤێ مۆدێلێ ل Railway بپشکنیت.", [[BACK]]
        return "بەرسڤ ڤێ جارێ نەگەهشت. تکایە نامەیێ دووبارە بنێرە.", [[BACK]]
    label = " [photo]" if message.get("photo") else " [voice]" if message.get("voice") else ""
    state["gemini_history"] = (history + [[text + label, answer[-6000:]]])[-12:]
    return answer, [[BACK]]


def smart_reply(db, message, state, username, token, previous):
    text = message.get("text","").strip()
    mode = state.get("mode")
    if not (message.get("successful_payment") or message.get("refunded_payment")):
        if text in (GEMINI_CHAT, "/gemini") or (mode == "gemini" and text == "/new"):
            if text == "/new":
                state.pop("gemini_history", None)
            state["mode"] = "gemini"
            return "چاتا Gemini. پرسیارا خۆ بنڤیسە، وێنە یان دەنگەکێ بنێرە. نامە بۆ Google Gemini دهێنە هنارتن. ژ بۆ ئاخفتنەکا نوو /new بنێرە.", [[BACK]]
        if mode == "gemini":
            if text != BACK and not text.startswith("/"):
                return gemini_chat(message, state, token)
            state["mode"] = None
    current = options(previous[1]) if previous else []
    global_buttons = options(MENU) + options(practice.SECTIONS) + [BACK]
    # The reader's Resume label is also an ordinary conversational follow-up.
    history = state.get("ai_history") or []
    chat_followup = bool(text == RESUME and history and previous and
                         (previous[0] == history[-1][1] or
                          (state.get("mode") == "ai" and previous[1] == [[BACK]])))
    direct = text.startswith("/") or (text in global_buttons + current and not chat_followup)
    form = (mode in ("p_recall","p_hadith") or
            mode=="p_words" and any(practice.norm(text)==practice.norm(w) for w in practice.GLOSS) or
            mode=="quran" and any(normalize(text)==normalize(name) for name in SURAHS) or
            mode in ("plus_days","p_group","p_verse","goal","reminder","hifz_add","position","quran","juz","count") and bool(re.fullmatch(r"[\d:：/ +]+",text)))
    if (direct or form or mode=="ai_confirm" or
        not (message.get("voice") or text) or
        message.get("successful_payment") or message.get("refunded_payment")):
        return native_reply(db,message,state,username,token)
    # Recognize curated local supplications before contacting the model.
    for key,(title,_,_,_,phrases) in OCCASIONS.items():
        if text and any(practice.norm(text)==practice.norm(p) for p in (title,*phrases)):
            return occasion_card(key,state,text)
    targets = list(dict.fromkeys(global_buttons+[plus_shop.FIB,plus_shop.STARS,"/paysupport"]+current))
    def navigate(label):
        if label in (plus_shop.FIB,plus_shop.STARS):
            state["mode"]="tip_method"
        elif label in global_buttons:
            state["mode"]=None
        elif label!="/paysupport":
            # User selects the actual control; financial consent and modifications stay explicit.
            return "ژ بۆ جێبەجێکرنێ ل ڤێ دوگمەیێ بدە.", [[label],[BACK]]
        return native_reply(db,{"chat":message["chat"],"text":label},state,username,token)
    context = (previous[0][:850] if previous and isinstance(previous[1],list)
               and not str(mode).startswith(("tip_","plus_")) else "")
    return assistant_action(message,state,token,targets,navigate,context,previous[1] if previous and isinstance(previous[1],list) else MENU, chat_followup=chat_followup)


def process(db, message, username=None, token=None):
    chat = message["chat"]["id"]
    mid = message["message_id"]
    with db:
        row = db.execute("SELECT state, mid, response FROM users WHERE chat=?", (chat,)).fetchone()
        if row and mid == row[1]:
            return json.loads(row[2])
        state = json.loads(row[0]) if row else {}
        old_alerts = set(state.get("alerts",[]))
        old_city = state.get("city")
        old_clock = state.get("reminder_time")
        text = message.get("text","")
        if row is None:
            track_join(db,chat,text)
        previous = json.loads(row[2]) if row else None
        response = smart_reply(db,message,state,username,token,previous)
        city = state.get("city")
        alerts = set(state.get("alerts",[]))
        if city != old_city or alerts != old_alerts:
            for name in old_alerts-alerts:
                db.execute("DELETE FROM prayer_subs WHERE chat=? AND name=?", (chat,name))
            for name in alerts:
                db.execute("INSERT INTO prayer_subs(chat,city,name) VALUES (?,?,?) ON CONFLICT(chat,name) DO UPDATE SET city=excluded.city", (chat,city,name))
        clock = state.get("reminder_time")
        if clock != old_clock:
            if clock:
                db.execute("INSERT INTO reminders(chat,clock) VALUES (?,?) ON CONFLICT(chat) DO UPDATE SET clock=excluded.clock", (chat,clock))
            else:
                db.execute("DELETE FROM reminders WHERE chat=?", (chat,))
        db.execute("INSERT OR REPLACE INTO users VALUES (?, ?, ?, ?)",
                   (chat, json.dumps(state), mid, json.dumps(response)))
    return response


class TelegramError(Exception):
    def __init__(self, code, delay=3):
        self.code = code
        self.delay = delay


def reader_links(text):
    base = "https://ronahi.up.railway.app"
    return text.replace("https://quran.com/", base + "/#")

def start_reader():
    from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
    from functools import partial
    from threading import Thread
    directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
    handler = partial(SimpleHTTPRequestHandler, directory=directory)
    server = ThreadingHTTPServer(("0.0.0.0",int(os.environ.get("PORT","8080"))),handler)
    Thread(target=server.serve_forever,daemon=True).start()

def api(token, method, **payload):
    if method == "sendMessage":
        payload["text"] = reader_links(payload["text"])
        rows = payload.get("reply_markup", {}).get("keyboard", [])
        if any(button.get("text") == practice.READY for row in rows for button in row):
            chunks = payload["text"].split("\n\n")
            if len(chunks) >= 3:
                length = lambda x: len(x.encode("utf-16-le")) // 2
                payload["entities"] = [{"type":"spoiler","offset":length(chunks[0])+2,"length":length(chunks[1])}]
    req = Request("https://api.telegram.org/bot" + token + "/" + method,
                  data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=45) as response:
            return json.load(response)["result"]
    except HTTPError as err:
        try:
            delay = json.load(err).get("parameters", {}).get("retry_after", 3)
        except ValueError:
            delay = 3
        raise TelegramError(err.code, delay) from None


def reply_parts(text):
    # Count non-BMP characters conservatively and prefer paragraph boundaries.
    while len(text.encode("utf-16-le")) > 8000:
        limit = 4000
        while len(text[:limit].encode("utf-16-le")) > 8000:
            limit -= 1
        cut = max(text.rfind("\n", limit//2, limit), text.rfind(" ", limit//2, limit)) + 1
        cut = cut or limit
        yield text[:cut]
        text = text[cut:]
    if text:
        yield text


def deliver(db,token,message,body,rows):
    chat,mid=message["chat"]["id"],message["message_id"]
    parts=list(reply_parts(reader_links(body)))
    saved=db.execute("SELECT mid,sent FROM delivery WHERE chat=?",(chat,)).fetchone()
    start=saved[1] if saved and saved[0]==mid else 0
    for index in range(start,len(parts)):
        args={"chat_id":chat,"text":parts[index],"link_preview_options":{"is_disabled":True}}
        if index==len(parts)-1:
            args["reply_markup"]=rows if isinstance(rows,dict) else {"keyboard":[[{"text":label} for label in row] for row in rows],"resize_keyboard":True}
        api(token,"sendMessage",**args)
        with db:
            db.execute("INSERT OR REPLACE INTO delivery VALUES (?,?,?)",(chat,mid,index+1))


def serve(token):
    folder = os.environ.get("RAILWAY_VOLUME_MOUNT_PATH", "/tmp")
    db = sqlite3.connect(os.path.join(folder, "ronahi.sqlite3"))
    db.execute("CREATE TABLE IF NOT EXISTS users(chat INTEGER PRIMARY KEY, state TEXT, mid INTEGER, response TEXT)")
    db.execute("CREATE TABLE IF NOT EXISTS reminders(chat INTEGER PRIMARY KEY, clock TEXT, last_day TEXT DEFAULT '')")
    db.execute("CREATE INDEX IF NOT EXISTS reminder_clock ON reminders(clock)")
    db.execute("CREATE TABLE IF NOT EXISTS prayer_subs(chat INTEGER, city TEXT, name TEXT, day TEXT DEFAULT '', PRIMARY KEY(chat,name))")
    db.execute("CREATE INDEX IF NOT EXISTS prayer_city ON prayer_subs(city,name,day)")
    db.execute("CREATE TABLE IF NOT EXISTS invite_links(chat INTEGER PRIMARY KEY, code TEXT UNIQUE)")
    db.execute("CREATE TABLE IF NOT EXISTS joins(chat INTEGER PRIMARY KEY, code TEXT, source TEXT)")
    db.execute("CREATE INDEX IF NOT EXISTS joins_source ON joins(code,source)")
    db.execute("CREATE TABLE IF NOT EXISTS delivery(chat INTEGER PRIMARY KEY,mid INTEGER,sent INTEGER)")
    practice.setup(db)
    plus_shop.setup(db)
    offset = None
    identified = False
    while True:
        try:
            if not identified:
                bot = api(token, "getMe")
                print("Connected as @" + bot["username"], flush=True)
                info = api(token, "getWebhookInfo")
                if info.get("url"):
                    raise SystemExit("Webhook active. Switch this bot to polling before restarting.")
                identified = True
            prayer_alerts(db, token)
            reminders(db, token)
            params = {"timeout": 20, "allowed_updates": ["message","pre_checkout_query"]}
            if offset is not None:
                params["offset"] = offset
            for item in api(token, "getUpdates", **params):
                if "pre_checkout_query" in item:
                    query = item["pre_checkout_query"]
                    ok = plus_shop.checkout(db,query)
                    try:
                        api(token,"answerPreCheckoutQuery",pre_checkout_query_id=query["id"],ok=ok,
                            **({} if ok else {"error_message":"فاتوورە بەردەست نینە. /plus ڤەکە."}))
                    except TelegramError as err:
                        if err.code != 400:
                            raise
                    offset=item["update_id"]+1
                    continue
                message = item.get("message", {})
                if message.get("chat", {}).get("type") == "private":
                    print("Private message received.", flush=True)
                    body, rows = process(db, message, bot["username"], token)
                    try:
                        deliver(db,token,message,body,rows)
                        print("Reply sent.", flush=True)
                    except TelegramError as err:
                        print("sendMessage failed: HTTP", err.code, flush=True)
                        if err.code not in (400, 403):
                            raise
                offset = item["update_id"] + 1
        except TelegramError as err:
            if err.code in (401, 404):
                raise SystemExit("Invalid token. Check the token from BotFather.")
            if err.code == 409:
                raise SystemExit("Polling conflict. Check for a second instance or an active webhook.")
            print("Telegram returned HTTP", err.code, "- retrying.", flush=True)
            time.sleep(max(3, err.delay))
        except (OSError, URLError):
            print("Network error reaching Telegram. Retrying.", flush=True)
            time.sleep(5)


if __name__ == "__main__":
    secret = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not re.fullmatch(r"[0-9]+:[A-Za-z0-9_-]+", secret):
        raise SystemExit("Set TELEGRAM_BOT_TOKEN in Railway Variables, then deploy.")
    start_reader()
    print("Ronahi Max worker starting.", flush=True)
    try:
        serve(secret)
    except KeyboardInterrupt:
        pass
