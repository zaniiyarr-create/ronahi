import base64
import json
import os
import re
import subprocess
import unicodedata
from bisect import bisect_right
from difflib import SequenceMatcher
from urllib.request import Request, urlopen

BUTTON = "هاریکارێ زیرەک"
YES = "بەلێ، یادئینانێ چالاک بکە"
HELP = ("ب خۆڕەتی ب بادینی دگەل من باخڤە. تو دشێی پرسیارەکێ بکەی، وەرگێڕانەکێ بخوازی یان پارچەیەک ژ ئایەتێ بنێری.\n\n"
        "نامە و دەنگ و چەند نامەیێن دوماهیێ بۆ Gemini دهێنە هنارتن. بۆ دەستپێکرنا ئاخفتنەکا نوی /new بنێرە.")
PROMPT = """You are Ronahi, a conversational assistant. Respond across topics, including science, technology, schoolwork and everyday questions. Admit uncertainty when facts are unclear. Answer general questions on any topic, tutoring, translation, writing,
religion and casual conversation. Use natural Kurdish Badini in Arabic script by default and follow the user's language request.
Use earlier turns to resolve follow-ups. Return one JSON object. For conversation return
{"action":"chat","answer":"your actual helpful response","heard":"brief transcript of current user request if spoken"}.
Keep each reply within 3500 characters. Ask for clarification when needed. Do not claim unsupported external actions.
Only select a bot command when explicitly requested, using these actions:
If the request quotes or recites Quran to identify a passage, even across verses, always return {"action":"find_quote","quote":"Arabic words actually heard or typed"}; omit command framing, never guess a chapter or complete the quote.
For a supplication requested for travel, bedtime, waking, mosque entry, mosque exit or worry use {"action":"occasion","key":"travel"} with respective keys travel, sleep, wake, mosque_in, mosque_out, worry.
Read surah: {"action":"surah","chapter":18}. Read or listen to verse: {"action":"verse","chapter":18,"verse":10}.
Open juz: {"action":"juz","number":1}. Show today's prayer times for user's configured city: {"action":"prayer"}.
Other supported actions without parameters: dua, dhikr, resume, quiz, hifz, ayah (daily verse), profile.
Set daily reading reminder in Iraq time: {"action":"reminder","time":"20:00"}. Only use if daily reading reminder clearly intended
and time unambiguous. For unclear time return {"action":"ask_time"}. For unclear audio,
ask the user to repeat via chat. For unsupported actions explain available alternatives via chat.
Never invent verse references or claim certainty about unverified quotations. Numbers must be integers."""
LIMIT = 2 * 1024 * 1024


def voice_part(token, voice, telegram):
    if not 0 < voice.get("duration", 0) <= 60 or voice.get("file_size", 0) > LIMIT:
        raise ValueError("voice size")
    path = telegram(token, "getFile", file_id=voice["file_id"])["file_path"]
    if not re.fullmatch(r"[\w/-]+\.[\w]+", path):
        raise ValueError("voice path")
    with urlopen(f"https://api.telegram.org/file/bot{token}/{path}", timeout=10) as stream:
        data = stream.read(LIMIT + 1)
    if len(data) > LIMIT:
        raise ValueError("voice size")
    result = subprocess.run(["ffmpeg", "-v", "error", "-protocol_whitelist", "pipe", "-f", "ogg",
                             "-i", "pipe:0", "-t", "60", "-vn", "-ar", "16000", "-ac", "1",
                             "-f", "flac", "pipe:1"], input=data, capture_output=True, timeout=10, check=True)
    return {"inlineData": {"mimeType": "audio/flac", "data": base64.b64encode(result.stdout).decode()}}


def interpret(part, key, history=(), prompt=PROMPT):
    model = os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite")
    if not re.fullmatch(r"[a-zA-Z0-9._-]+", model):
        raise ValueError("model")
    contents = []
    for question, answer in history:
        contents.extend([{"role":"user","parts":[{"text":question}]},
                         {"role":"model","parts":[{"text":json.dumps({"action":"chat","answer":answer}, ensure_ascii=False)}]}])
    contents.append({"role":"user","parts":[part]})
    body = {"systemInstruction": {"parts": [{"text": prompt}]}, "contents": contents,
            "generationConfig": {"responseMimeType":"application/json","temperature":0}}
    req = Request(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                  data=json.dumps(body).encode(), headers={"Content-Type":"application/json","x-goog-api-key":key})
    with urlopen(req, timeout=18) as response:
        parts = json.load(response)["candidates"][0]["content"]["parts"]
    return json.loads("".join(p.get("text", "") for p in parts if not p.get("thought")))

def compact_arabic(text):
    text = unicodedata.normalize("NFKC", text).translate(str.maketrans("ٱأإآىیک", "ااااييك"))
    text = text.replace("ٰ", "ا")
    letters = "".join(c for c in text if "ء" <= c <= "ي" and c != "ـ")
    return letters.replace("الرحمان", "الرحمن").replace("اللاه", "الله")


def passage_index(verses):
    chapters = {}
    basmala = compact_arabic(verses["1:1"])
    for ref, words in verses.items():
        c, v = map(int, ref.split(":"))
        chars, starts = chapters.setdefault(c, ([], []))
        line = compact_arabic(words)
        if c != 1 and v == 1 and line.startswith(basmala):
            line = line[len(basmala):]
        starts.append((starts[-1] + len(chars[-1])) if starts else 0)
        chars.append(line)
    return [(c, "".join(chars), starts) for c, (chars, starts) in chapters.items()]


def find_passage(quote, chapters):
    query = compact_arabic(quote)
    if not 6 <= len(query) <= 240:
        return []
    def location(c, starts, pos, length):
        return c, bisect_right(starts, pos), bisect_right(starts, pos + length - 1)
    hits = []
    for c, chars, starts in chapters:
        pos = chars.find(query)
        while pos >= 0:
            hit = location(c, starts, pos, len(query))
            if hit not in hits:
                hits.append(hit)
            if len(hits) == 5:
                return hits
            pos = chars.find(query, pos + 1)
    if hits or len(query) < 12:
        return hits
    # Two intact fragments anchor candidates despite joined words and minor spelling errors.
    size = len(query)
    scores = {}
    for c, chars, starts in chapters:
        positions = set()
        for anchor in (0, size // 3, 2 * size // 3):
            fragment = query[anchor:anchor + max(4, size // 4)]
            i = chars.find(fragment)
            while i >= 0:
                positions.update(range(max(0, i-anchor-1), min(len(chars), i-anchor+2)))
                i = chars.find(fragment, i+1)
        for pos in positions:
            for length in range(size-1, size+2):
                sample = chars[pos:pos+length]
                score = SequenceMatcher(None, query, sample, autojunk=False).ratio()
                if len(sample) == length and score >= .92:
                    hit = location(c, starts, pos, length)
                    scores[hit] = max(scores.get(hit, 0), score)
    best = max(scores.values(), default=0)
    return [hit for hit in sorted(scores, key=scores.get, reverse=True) if scores[hit] >= best-.008][:5]
