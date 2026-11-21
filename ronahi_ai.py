import base64
import json
import os
import re
import subprocess
import time
from urllib.error import HTTPError
import unicodedata
from bisect import bisect_right
from difflib import SequenceMatcher
from urllib.request import Request, urlopen

BUTTON = "هاریکارێ زیرەک"
YES = "بەلێ، یادئینانێ چالاک بکە"
HELP = ("ب خۆڕەتی ب بادینی دگەل من باخڤە. تو دشێی پرسیارەکێ بکەی، وەرگێڕانەکێ بخوازی یان پارچەیەک ژ ئایەتێ بنێری.\n\n"
        "نامە و دەنگ و چەند نامەیێن دوماهیێ بۆ خزمەتگوزارێ AI دهێنە هنارتن. بۆ دەستپێکرنا ئاخفتنەکا نوی /new بنێرە.")
PROMPT = """You are Ronahi, a conversational assistant. Respond across topics, including science, technology, schoolwork and everyday questions. Admit uncertainty when facts are unclear. Answer general questions on any topic, tutoring, translation, writing,
religion and casual conversation. Use natural Kurdish Badini in Arabic script by default and follow the user's language request.
If the user says "یا باش وی بکە", "چ تشتێ باش بیت بکە", "you choose", or "continue", use the preceding conversation, pick a reasonable next step and actually do it in this reply. In tutoring, give one concrete lesson or worked example and an exercise. Do not repeat your options or ask the user to choose again. Start with a brief clarifying question only if essential information is missing. Delegating a choice never confirms a payment or sensitive action.
Use earlier turns to resolve follow-ups. For ordinary conversation reply directly in plain text. Deliver the requested work in this reply:
draft the letter, write the plan, translate the passage, solve the problem, or begin the lesson. Use useful detail for the task.
For a spoken question you may return {"action":"chat","answer":"...","heard":"..."} to preserve the user's words.
When the user delegates a choice, select a sensible approach and proceed. Do not claim external actions you cannot perform.
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


def provider_for(voice=False):
    if voice:
        return "gemini"
    selected = os.getenv("AI_PROVIDER", "").strip().lower()
    if selected and selected != "auto":
        return {"anthropic": "claude", "chatgpt": "openai"}.get(selected, selected)
    return next((name for name, var in PROVIDER_KEYS.items() if os.getenv(var, "").strip()), "gemini")

PROVIDER_KEYS = {"gemini":"GEMINI_API_KEY","openai":"OPENAI_API_KEY","claude":"ANTHROPIC_API_KEY"}

def decode_reply(raw, conversational=True):
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("Empty model response")
    raw = raw.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", raw, re.S | re.I)
    candidate = fenced.group(1) if fenced else raw
    try:
        result = json.loads(candidate)
    except json.JSONDecodeError:
        if conversational:
            return {"action": "chat", "answer": raw}
        raise
    if not conversational:
        if not isinstance(result, dict):
            raise ValueError("Expected a JSON object")
        return result
    if isinstance(result, dict):
        if isinstance(result.get("action"), str):
            return result
        if isinstance(result.get("answer"), str) and result["answer"].strip():
            return {"action": "chat", "answer": result["answer"]}
    return {"action": "chat", "answer": result if isinstance(result, str) and result.strip() else raw}


def request_json(request):
    for attempt in range(2):
        try:
            with urlopen(request, timeout=40) as response:
                return json.load(response)
        except HTTPError as err:
            if attempt or err.code not in (502, 503, 504):
                raise
        except (TimeoutError, ConnectionResetError):
            if attempt:
                raise
        time.sleep(0.5)


def text_intent(provider, text, key, history, prompt):
    messages = []
    for question, answer in history:
        messages.extend([{"role":"user","content":question},{"role":"assistant","content":answer}])
    messages.append({"role":"user","content":text})
    headers = {"Content-Type":"application/json"}
    if provider == "openai":
        url = "https://api.openai.com/v1/chat/completions"
        headers["Authorization"] = "Bearer "+key
        body = {"model":os.environ.get("OPENAI_MODEL","gpt-4.1-mini"),
                "messages":[{"role":"system","content":prompt}, *messages]}
    else:
        url = "https://api.anthropic.com/v1/messages"
        headers.update({"x-api-key":key,"anthropic-version":"2023-06-01"})
        body = {"model":os.environ.get("ANTHROPIC_MODEL","claude-sonnet-4-6"),
                "system":prompt,"messages":messages,"max_tokens":3500}
    request = Request(url,data=json.dumps(body).encode(),headers=headers)
    result = request_json(request)
    raw = result["choices"][0]["message"]["content"] if provider=="openai" else "".join(
        item["text"] for item in result["content"] if item.get("type")=="text")
    return decode_reply(raw)

def generate(parts, key, history, prompt, conversational):
    model = os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite")
    if not re.fullmatch(r"[a-zA-Z0-9._-]+", model):
        raise ValueError("model")
    contents = []
    for question, answer in history:
        contents.extend([{"role":"user","parts":[{"text":question}]},
                         {"role":"model","parts":[{"text":answer}]}])
    contents.append({"role":"user","parts":parts})
    body = {"systemInstruction": {"parts": [{"text": prompt}]}, "contents": contents,
            "generationConfig": {"responseMimeType":"application/json","temperature":0}}
    if conversational:
        body["generationConfig"] = {"temperature": 0.7}
    req = Request(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                  data=json.dumps(body).encode(), headers={"Content-Type":"application/json","x-goog-api-key":key})
    parts = request_json(req)["candidates"][0]["content"]["parts"]
    answer = "".join(p.get("text", "") for p in parts if not p.get("thought")).strip()
    if not answer:
        raise ValueError("No model text")
    return answer


def interpret(part, key, history=(), prompt=PROMPT, conversational=None):
    if conversational is None:
        conversational = prompt.startswith(PROMPT)
    return decode_reply(generate([part], key, history, prompt, conversational), conversational)


def photo_part(token, photos, telegram):
    limit = 4 * 1024 * 1024
    photo = max((p for p in photos if p.get("file_size", 0) <= limit),
                key=lambda p: p["width"] * p["height"], default=None)
    if not photo:
        raise ValueError("Photo too large")
    path = telegram(token, "getFile", file_id=photo["file_id"])["file_path"]
    if not re.fullmatch(r"[\w/-]+\.[\w]+", path):
        raise ValueError("Invalid photo path")
    with urlopen(f"https://api.telegram.org/file/bot{token}/{path}", timeout=12) as response:
        data = response.read(limit + 1)
    if len(data) > limit or not data.startswith(b"\xff\xd8"):
        raise ValueError("Unsupported photo")
    return {"inlineData": {"mimeType": "image/jpeg", "data": base64.b64encode(data).decode()}}


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
