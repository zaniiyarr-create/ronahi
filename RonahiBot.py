import json
import os
import re
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
        return "سەلام علیکم، بخێر هاتی بۆ ڕووناهی. تو دڤێی چ بخوینی؟", MENU
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


class TelegramError(Exception):
    def __init__(self, code, delay=3):
        self.code = code
        self.delay = delay


def api(token, method, **payload):
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


def serve(token):
    offset = None
    while True:
        try:
            params = {"timeout": 30, "allowed_updates": ["message"]}
            if offset is not None:
                params["offset"] = offset
            for item in api(token, "getUpdates", **params):
                message = item.get("message", {})
                if message.get("chat", {}).get("type") == "private":
                    body, rows = reply(message.get("text", ""))
                    try:
                        api(token, "sendMessage", chat_id=message["chat"]["id"], text=body,
                            reply_markup={"keyboard": rows, "resize_keyboard": True},
                            link_preview_options={"is_disabled": True})
                    except TelegramError as err:
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
            time.sleep(5)


if __name__ == "__main__":
    secret = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not re.fullmatch(r"[0-9]+:[A-Za-z0-9_-]+", secret):
        raise SystemExit("Set TELEGRAM_BOT_TOKEN in Railway Variables, then deploy.")
    print("Ronahi worker starting.", flush=True)
    try:
        serve(secret)
    except KeyboardInterrupt:
        pass
