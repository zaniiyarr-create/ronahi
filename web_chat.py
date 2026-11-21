import base64
import json
import os
import time
from collections import deque
from http.server import SimpleHTTPRequestHandler
from threading import BoundedSemaphore, Lock
from urllib.error import HTTPError

import ronahi_ai as ai


class ReaderHandler(SimpleHTTPRequestHandler):
    slots = BoundedSemaphore(3)
    recent = deque()
    lock = Lock()
    media_types = {"image/jpeg", "image/png", "image/webp", "audio/mpeg", "audio/mp4", "audio/wav", "audio/ogg"}

    def reply_json(self, code, **result):
        data = json.dumps(result, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        if self.path != "/api/chat":
            return self.send_error(404)
        if self.headers.get_content_type() != "application/json":
            return self.reply_json(415, error="input")
        key = os.getenv("GEMINI_API_KEY", "").strip()
        if not key:
            return self.reply_json(503, error="configuration")
        if not self.slots.acquire(blocking=False):
            return self.reply_json(429, error="busy")
        try:
            self.connection.settimeout(15)
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 4_400_000:
                return self.reply_json(413, error="size")
            payload = json.loads(self.rfile.read(size))
            if not isinstance(payload, dict):
                raise ValueError()
            text = payload.get("text", "")
            history = payload.get("history", [])
            if not isinstance(text, str) or len(text) > 4096 or not isinstance(history, list) or len(history) > 12:
                raise ValueError()
            for turn in history:
                if not isinstance(turn, list) or len(turn) != 2 or not all(isinstance(v,str) and len(v)<=6000 for v in turn):
                    raise ValueError()
            parts = []
            media = payload.get("media")
            if media is not None:
                if not isinstance(media,dict) or media.get("mimeType") not in self.media_types:
                    raise ValueError()
                data = media.get("data")
                if not isinstance(data,str) or not 0 < len(base64.b64decode(data,validate=True)) <= 3_000_000:
                    raise ValueError()
                parts.append({"inlineData":{"mimeType":media["mimeType"],"data":data}})
            if text.strip():
                parts.append({"text":text.strip()})
            if not parts:
                raise ValueError()
            with self.lock:
                now = time.monotonic()
                while self.recent and self.recent[0] <= now - 60:
                    self.recent.popleft()
                if len(self.recent) >= 30:
                    return self.reply_json(429,error="busy")
                self.recent.append(now)
            try:
                answer = ai.generate(parts,key,history,ai.ISLAMIC_SCOPE,True)
            except HTTPError as err:
                print("Web Gemini HTTP",err.code,flush=True)
                return self.reply_json(429 if err.code==429 else 502,error="busy" if err.code==429 else "provider")
            except (OSError,ValueError,KeyError,IndexError,TypeError):
                return self.reply_json(502,error="provider")
            self.reply_json(200,answer=answer)
        except (ValueError,TypeError,RecursionError):
            self.reply_json(400,error="input")
        finally:
            self.slots.release()
