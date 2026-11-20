import os
import re
import secrets
import subprocess
import unicodedata
import ronahi_ai as ai

HUB = "ڕاهێنان و خەتم"
COACH, WORDS, HADITH, GROUP, TEST = "مامۆستایێ حەفزێ", "مانایا پەیڤێ", "فەرموودەیێ بپشکنە", "خەتما هەڤالان", "ئەڤڕۆ چ فێر بووم؟"
SECTIONS = [[COACH, WORDS], [HADITH, GROUP], [TEST]]
NEW, BOARD, FINISH = "خەتمەکا نوی چێکە", "دۆخێ خەتمێ نوێ بکە", "جوزێ من تەمام بوو"
READY = "ئامادەم ب ژبەر بخوینم"
GLOSS = {
    "الصَّمَدُ": ("112:2", "خودایێ هەمی ئافراندی د پێدڤیێن خۆ دا بەرێ خۆ ددەنێ."),
    "الْفَلَقِ": ("113:1", "سپێدە، دەمێ ڕووناهییا ڕۆژێ دەردکەڤیت."),
    "أَعُوذُ": ("113:1", "ئەز پەنا دبەم و پاراستنێ دخوازم."),
    "الْخَنَّاسِ": ("114:4", "ئەوێ وسوەسێ دکەت و دەمێ مرۆڤ خودێ ب بیر دئینیت، پاشڤە دکێشیت."),
    "الصِّرَاطَ": ("1:6", "ڕێک. د ڤێ ئایەتێ دا داخوازی ژ خودێیە کو مە بەری ڕێکا ڕاست ببەت."),
}
# Arabic excerpts and companion narrators, indexed by the cited collection identifier.
REPORTS = [
    ("إنما الأعمال بالنيات وإنما لكل امرئ ما نوى","نیەت و کار","عومەرێ کورێ خەتتاب","bukhari:1"),
    ("لا يؤمن أحدكم حتى يحب لأخيه ما يحب لنفسه","خێر خواستن بۆ برای","ئەنەسێ کورێ مالک","bukhari:13"),
    ("المسلم من سلم المسلمون من لسانه ويده","پاراستن ژ زیانێ دەست و ئەزمانی","عەبدوللایێ کورێ عەمر","bukhari:10"),
    ("من كان يؤمن بالله واليوم الآخر فليقل خيرا أو ليصمت","پەیڤا باش و بێدەنگی","ئەبو هورەیرە","bukhari:6018"),
    ("الدين النصيحة","دین شیرەتە","تەمیمێ داری","muslim:55a"),
    ("من أحدث في أمرنا هذا ما ليس منه فهو رد","بیدعە د دینێ دا","عائیشە","muslim:1718a"),
]
CASES = [
    ("ڕاستگۆیی د بازرگانیێ دا","تو مۆبایلەکێ دفرۆشی و دزانی پاترییا وێ زوو دخەلصیت. تو دێ چ کەی؟","عەیبێ وێ بێژم","عەیبێ وێ ڤەشێرم","کریار ب زانینا عەیبێ دشێت بریارێ بدەت.","https://sunnah.com/bukhari:2079"),
    ("بەری بڵاڤکرنێ","نووچەیەک بێ ژێدەر گەهشتە گرووپێ تە. پێشێ چ دکەی؟","ژێدەرێ دپشکنم","هەما دهنێرم","پشکنین دپارێزیت کو ب نەزانی زیان ب کەسەکی نەگەهیت.","https://quran.com/49/6"),
    ("مافێ جیرانی","سەیارەیا تە ڕێکا دەرگەهێ جیرانی دگریت. چ دکەی؟","سەیارەیێ دگوهێزم","ل وێرێ دهێلم","ڤەکرنا ڕێکێ جیرانی ژ زیانێ دپارێزیت.","https://sunnah.com/bukhari:6018"),
    ("کێش و پێڤانا دروست","کریارەکی بهایێ کیلۆیەکێ دا، بەڵێ تە کێم کێشا. چ دکەی؟","کێشێ تەمام دکەم","هەر وەسا ددەمێ","پێڤانا تەمام مافێ کریارییە.","https://quran.com/17/35"),
]
def norm(s):
    s = unicodedata.normalize("NFKD",s).translate(str.maketrans("ٱىیک","اييك"))
    return "".join(c for c in s if c.isalnum())

def setup(db):
    db.execute("CREATE TABLE IF NOT EXISTS khatm_groups(code TEXT PRIMARY KEY)")
    db.execute("CREATE TABLE IF NOT EXISTS khatm_members(code TEXT, chat INTEGER, PRIMARY KEY(code,chat))")
    db.execute("CREATE TABLE IF NOT EXISTS khatm_parts(code TEXT, juz INTEGER, chat INTEGER, done INTEGER DEFAULT 0, PRIMARY KEY(code,juz))")
    db.execute("CREATE UNIQUE INDEX IF NOT EXISTS one_open_juz ON khatm_parts(code,chat) WHERE done=0")

def group(db,s,chat,user,text,back):
    code = s.get("group_code","")
    invite = re.fullmatch(r"/start k_([A-Za-z0-9_-]{12})",text)
    if invite:
        code = invite[1]
        if not db.execute("SELECT 1 FROM khatm_groups WHERE code=?",(code,)).fetchone():
            return "ئەڤ لینکە نەهاتە ناسین.", [[GROUP,back]]
    if text == NEW:
        code = secrets.token_urlsafe(9)
        db.execute("INSERT INTO khatm_groups VALUES (?)",(code,))
    if invite or text == NEW:
        db.execute("INSERT OR IGNORE INTO khatm_members VALUES (?,?)",(code,chat))
        s["group_code"] = code
    s["mode"] = "p_group"
    if not db.execute("SELECT 1 FROM khatm_members WHERE code=? AND chat=?",(code,chat)).fetchone():
        return "خەتمەکێ چێکە یان لینکێ هەڤالەکێ ڤەکە.", [[NEW],[HUB,back]]
    notices = []
    if text == FINISH:
        db.execute("UPDATE khatm_parts SET done=1 WHERE code=? AND chat=? AND done=0",(code,chat))
    if text.isdecimal() and len(text)<=2 and 1<=int(text)<=30:
        if not db.execute("INSERT OR IGNORE INTO khatm_parts(code,juz,chat) VALUES (?,?,?)",(code,int(text),chat)).rowcount:
            notices.append("ئەڤ جوزە نەهاتە وەرگرتن. جوزێ خۆ یێ ڤەکری تەمام بکە یان جوزەکێ بەردەست هەلبژێرە.")
    parts = {j:(who,done) for j,who,done in db.execute("SELECT juz,chat,done FROM khatm_parts WHERE code=?",(code,))}
    free = [str(j) for j in range(1,31) if j not in parts]
    mine = [j for j,(who,done) in parts.items() if who==chat and not done]
    completed = sum(done for _,done in parts.values())
    notices.extend([f"خەتما هەڤالان • {completed}/30", "جوزێن بەردەست • "+("، ".join(free) or "٠")])
    if mine: notices.append(f"جوزێ تە • {mine[0]}")
    if user: notices.append(f"لینکێ ڤەخواندنێ\nhttps://t.me/{user}?start=k_{code}")
    buttons = [[FINISH]] if mine else [free[i:i+5] for i in range(0,len(free),5)]
    return "\n\n".join(notices), buttons+[[BOARD,NEW],[HUB,back]]

def ask_case(s,i,back):
    title,q,yes,no,_,_ = CASES[i]
    s.update(mode="p_case", case_index=i)
    return title+"\n\n"+q, [[no,yes] if i%2==0 else [yes,no],[TEST,back]]

def handle(db,s,msg,user,token,bot):
    t = msg.get("text","").strip()
    mode = s.get("mode") or ""
    back = bot.BACK
    nav = [[HUB,back]]
    if t in (HUB,"/practice"):
        s["mode"]="p_menu"
        return "بەشەکێ هەلبژێرە.", SECTIONS+[[back]]
    if t in (GROUP,"/khatm") or t.startswith("/start k_"):
        return group(db,s,msg["chat"]["id"],user,t,back)
    if t == COACH:
        s["mode"]="p_verse"
        return "سوورەت و ئایەتێ بنێرە، وەک ١١٢:٢.", [["112:2","1:2"],*nav]
    if t == WORDS:
        s["mode"]="p_words"
        return "پەیڤەکێ هەلبژێرە داکو مانایا وێ د ئایەتێ دا ببینی.", [[w] for w in GLOSS]+nav
    if t == HADITH:
        s["mode"]="p_hadith"
        return "دەقێ عەرەبی یێ فەرموودەیێ یان پارچەیەکێ بنێرە. گەڕیان د ٦ دەقێن هەلبژارتی دایە.", [["إنما الأعمال بالنيات"],*nav]
    if t == TEST:
        if mode=="lessons":
            for i,case in enumerate(CASES):
                if case[0]==s.get("last_lesson"):
                    return ask_case(s,i,back)
        s["mode"]="p_topics"
        return "ڕوودانەکێ هەلبژێرە.", [[a[0]] for a in CASES]+nav
    if not mode.startswith("p_"):
        return None
    if t==back or t.startswith("/") or any(t in row for row in bot.MENU):
        s["mode"]=None
        return None
    if mode=="p_group":
        return group(db,s,msg["chat"]["id"],user,t,back)
    if mode=="p_topics":
        for i,case in enumerate(CASES):
            if t==case[0]: return ask_case(s,i,back)
        return "بابەتەکێ هەلبژێرە.", [[a[0]] for a in CASES]+nav
    if mode=="p_case":
        title,q,yes,no,why,url=CASES[s["case_index"]]
        if t not in (yes,no): return ask_case(s,s["case_index"],back)
        s["mode"]="p_menu"
        return ("بەرسڤا تە دروستە." if t==yes else "بەرسڤا دروست • "+yes)+"\n"+why+"\n"+url, [[TEST],*nav]
    if mode=="p_words":
        for word,(ref,meaning) in GLOSS.items():
            if norm(t)==norm(word):
                c,v=ref.split(":")
                return f"{word} • {bot.verse_name(ref)}\n{bot.VERSE_TEXT[ref]}\n\n{meaning}\nتفسیر السعدي\nhttps://quran.ksu.edu.sa/tafseer/saadi/sura{c}-aya{v}.html", [[WORDS],*nav]
        return "پەیڤەکێ ژ لیستێ هەلبژێرە.", [[w] for w in GLOSS]+nav
    if mode=="p_hadith":
        query=norm(t)
        hits=[]
        for arabic,title,narrator,ref in REPORTS:
            phrase=norm(arabic)
            if len(query)>=8 and (query in phrase or phrase in query or query==norm(title)):
                collection,num=ref.split(":")
                book="صحیح البخاري" if collection=="bukhari" else "صحیح مسلم"
                hits.append(f"{title}\nژ دەقێ فەرموودەیێ • {arabic}\nڤەگوهێز • {narrator}\n{book} • {num}\nhttps://sunnah.com/{ref}")
        return ("\n\n".join(hits) or "من د ژێدەرێن خۆ دا نەدیت. پارچەیەکا دی ژ دەقێ عەرەبی بنێرە."), [[HADITH],*nav]
    if mode=="p_verse":
        pair=re.fullmatch(r"(\d{1,3})\s*[:/]\s*(\d{1,3})",t)
        ref=":".join(str(int(x)) for x in pair.groups()) if pair else ""
        if ref not in bot.VERSE_TEXT: return "ئایەت نەهاتە دیتن. نموونە ١١٢:٢", nav
        s.update(mode="p_listen",train_ref=ref)
        return bot.verse_body(ref), [[READY],*nav]
    if mode=="p_listen":
        if t!=READY: return "پشتی گوهداریکرنێ دوگمەیێ لێ بدە.", [[READY],*nav]
        s["mode"]="p_recall"
        return "نوکە ژبەر بخوینە. دەنگێ تە بۆ Gemini دهێتە هنارتن، یان پەیڤان ژبەر بنڤیسە.", nav
    if mode=="p_recall":
        reference=bot.VERSE_TEXT[s["train_ref"]]
        heard=t
        if msg.get("voice"):
            key=os.environ.get("GEMINI_API_KEY")
            if not key: return "بۆ دەنگی GEMINI_API_KEY پێدڤییە. تو دشێی ژبەر بنڤیسی.", nav
            try:
                part=ai.voice_part(token,msg["voice"],bot.api)
                result=ai.interpret(part,key,prompt='Transcribe exactly the audible Arabic words without restoring a familiar verse or filling gaps. For unclear, incomplete audio quality or silence return {"unclear":true}. Otherwise return {"transcript":"..."} only.')
                heard=result.get("transcript","") if isinstance(result,dict) and not result.get("unclear") else ""
            except (OSError,ValueError,KeyError,IndexError,TypeError,subprocess.SubprocessError,bot.TelegramError):
                heard=""
        if not isinstance(heard,str) or not re.search(r"[ء-ي]",heard):
            return "پەیڤ ڕوون نەبوون. دووبارە ب دەنگ یان ب نڤیسین بنێرە.", nav
        words=reference.split()
        standard=ai.compact_arabic
        target=[standard(w) for w in words if standard(w)]
        spoken=[standard(w) for w in heard.split() if standard(w)]
        if target==spoken: feedback="پەیڤێن ناسکری دگەل ڕیزا ئایەتێ گونجان."
        else:
            feedback="دووبارە گوهداریێ بکە و پەیڤان ب ڕیز بخوینە."
        return f"{feedback}\n\nپەیڤێن ناسکری • {heard[:1300]}\n\nدەقێ ئایەتێ • {reference}\n\nدوبارە بنێرە یان ئایەتەکا دی هەلبژێرە.", [[COACH],*nav]
    return "بەشەکێ هەلبژێرە.", SECTIONS+[[back]]
