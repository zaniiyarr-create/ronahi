import bisect
import itertools
import os
import re
import secrets
import time
from datetime import date, timedelta

PLUS = "ڕووناهی Plus"
AGREE = "مەرج من خواندن و ئەز ڕازیم"
PLAN = "پلانا خەتمێ چێکە"

DONATE = "Donation | پشتەڤانی"
FIB = "FIB"
STARS = "Telegram Stars"
AMOUNTS = (10, 25, 50, 100)

def donation(db,s,msg,token,bot):
    chat=msg["chat"]["id"]
    text=msg.get("text","").strip()
    pay=msg.get("successful_payment") or msg.get("refunded_payment")
    if pay and pay.get("invoice_payload","").startswith("tip:"):
        payload=pay["invoice_payload"]
        order=db.execute("SELECT amount FROM tip_orders WHERE payload=? AND chat=?",(payload,chat)).fetchone()
        if order!=(pay["total_amount"],) or pay["currency"]!="XTR":
            return "تکایە ژ بۆ پشکنینا وەسلێ /paysupport بنێرە.",bot.MENU
        refunded=int("refunded_payment" in msg)
        db.execute("""INSERT INTO tip_receipts VALUES (?,?,?)
            ON CONFLICT(charge) DO UPDATE SET refunded=MAX(refunded,excluded.refunded)""",
            (pay["telegram_payment_charge_id"],payload,refunded))
        s["mode"]=None
        return ("ستێرکێن پشتەڤانیێ هاتنە زڤڕاندن." if refunded else f"سوپاس بۆ پشتەڤانیا تە یا {order[0]} ستێرکان بۆ ڕووناهی."),bot.MENU
    if text in (DONATE,"/donate"):
        s["mode"]="tip_method"
        return "ئەگەر تو ب دلێ خۆ دڤێی پشتەڤانیا ڕووناهی بکەی، ڕێکەکێ هەلبژێرە. پشتەڤانی ئارەزوومەندانەیە.",[[STARS,FIB],[bot.BACK]]
    if s.get("mode")=="tip_method" and text==FIB:
        return "پشتەڤانی ب FIB\n\n0750 604 5491\n\nژمارێ ل ئەپێ FIB بنڤیسە و بەری پشتڕاستکرنا ڤەگوهاستنێ ناڤێ وەرگری بپشکنە.",{"inline_keyboard":[[{"text":"کۆپیکرنا ژمارێ","copy_text":{"text":"07506045491"}}]]}
    if s.get("mode")=="tip_method" and text==STARS:
        if not contact() or not os.environ.get("RAILWAY_VOLUME_MOUNT_PATH"):
            return "پشتەڤانیا Stars هێشتا نەهاتیە چالاککرن.",[[FIB,DONATE],[bot.BACK]]
        s["mode"]="tip_amount"
        return "چەند ستێرکان دڤێی ببەخشی؟ هەر پشتەڤانی ئێک پارەدانە.",[[f"{n} ⭐" for n in AMOUNTS],[DONATE,bot.BACK]]
    if s.get("mode")=="tip_amount" and text in {f"{n} ⭐" for n in AMOUNTS}:
        amount=int(text.split()[0])
        payload="tip:"+secrets.token_urlsafe(24)
        link=bot.api(token,"createInvoiceLink",title="Ronahi • پشتەڤانی",description="پشتەڤانیا ئارەزوومەندانە بۆ ڕووناهی",payload=payload,currency="XTR",provider_token="",prices=[{"label":DONATE,"amount":amount}])
        db.execute("INSERT INTO tip_orders(payload,chat,amount) VALUES (?,?,?)",(payload,chat,amount))
        return f"بۆ پشتڕاستکرنا پشتەڤانیا {amount} ستێرکان، فاتوورێ ڤەکە.",{"inline_keyboard":[[{"text":text,"url":link}]]}
    if s.get("mode") in ("tip_method","tip_amount"):
        s["mode"]=None
    return None


def setup(db):
    db.execute("CREATE TABLE IF NOT EXISTS tip_orders(payload TEXT PRIMARY KEY, chat INTEGER, amount INTEGER, checkout TEXT, checked_at INTEGER DEFAULT 0)")
    db.execute("CREATE TABLE IF NOT EXISTS tip_receipts(charge TEXT PRIMARY KEY, payload TEXT, refunded INTEGER DEFAULT 0)")
    db.execute("""CREATE TABLE IF NOT EXISTS plus_orders(
        payload TEXT PRIMARY KEY, chat INTEGER NOT NULL, price INTEGER NOT NULL,
        checkout TEXT, checked_at INTEGER DEFAULT 0)""")
    db.execute("""CREATE TABLE IF NOT EXISTS plus_receipts(
        charge TEXT PRIMARY KEY, chat INTEGER NOT NULL, refunded INTEGER DEFAULT 0)""")

def contact():
    value=(os.environ.get("PLUS_SUPPORT") or "z_14x").strip().lstrip("@")
    return "@"+value if re.fullmatch(r"[A-Za-z0-9_]{5,32}",value) else ""

def price():
    value=os.environ.get("PLUS_STARS","50")
    return int(value) if re.fullmatch(r"[1-9][0-9]{0,3}",value) else 0

def selling():
    return bool(price() and contact() and os.environ.get("RAILWAY_VOLUME_MOUNT_PATH"))

def owned(db,chat):
    return bool(db.execute("SELECT 1 FROM plus_receipts WHERE chat=? AND refunded=0 LIMIT 1",(chat,)).fetchone())

def checkout(db,q):
    uid=q["from"]["id"]
    with db:
        if q.get("invoice_payload","").startswith("tip:"):
            if q.get("currency")!="XTR" or not contact() or not os.environ.get("RAILWAY_VOLUME_MOUNT_PATH"):
                return False
            return bool(db.execute("""UPDATE tip_orders SET checkout=?,checked_at=? WHERE payload=? AND chat=? AND amount=?
                AND (checkout IS NULL OR checkout=? OR checked_at<?)
                AND NOT EXISTS(SELECT 1 FROM tip_receipts WHERE payload=tip_orders.payload)""",
                (q["id"],int(time.time()),q["invoice_payload"],uid,q["total_amount"],q["id"],int(time.time())-1800)).rowcount)
        if q.get("currency")!="XTR" or owned(db,uid) or not selling():
            return False
        row=db.execute("SELECT checkout,checked_at FROM plus_orders WHERE chat=? AND checked_at>? ORDER BY checked_at DESC LIMIT 1",(uid,int(time.time())-1800)).fetchone()
        if row and row[0]!=q["id"]:
            return False
        return bool(db.execute("UPDATE plus_orders SET checkout=?, checked_at=? WHERE payload=? AND chat=? AND price=? AND price=?",
            (q["id"],int(time.time()),q["invoice_payload"],uid,q["total_amount"],price())).rowcount)

def page(s,bot):
    days,start=s["plus_plan"]
    pos=s["plus_page"]
    ends=list(itertools.accumulate(bot.LENGTHS))
    def ref(number):
        chapter=bisect.bisect_left(ends,number)
        return chapter+1,number-(ends[chapter-1] if chapter else 0)
    lines=[f"پلانا خەتمێ • {days} ڕۆژ"]
    for i in range(pos,min(pos+7,days)):
        c,v=ref(ends[-1]*i//days+1)
        d,w=ref(ends[-1]*(i+1)//days)
        day=date.fromisoformat(start)+timedelta(days=i)
        lines.append(f"{day} • {bot.SURAHS[c-1]} {v} — {bot.SURAHS[d-1]} {w}\nhttps://quran.com/{c}/{v}")
    nav=(["پەڕێ بەری"] if pos else [])+(["پەڕێ داهاتی"] if pos+7<days else [])
    return "\n\n".join(lines), ([nav] if nav else [])+[[PLAN,bot.BACK]]

def handle(db,s,msg,token,bot):
    result=donation(db,s,msg,token,bot)
    if result is not None:
        return result
    chat=msg["chat"]["id"]
    text=msg.get("text","").strip()
    support=contact() or "/paysupport"
    pay=msg.get("successful_payment")
    if pay:
        valid=db.execute("SELECT 1 FROM plus_orders WHERE payload=? AND chat=? AND price=?",(pay["invoice_payload"],chat,pay["total_amount"])).fetchone()
        if pay["currency"]!="XTR" or not valid:
            return "پێدڤی ب پشکنینا وەسلێ هەیە • "+support, bot.MENU
        db.execute("INSERT OR IGNORE INTO plus_receipts(charge,chat) VALUES (?,?)",(pay["telegram_payment_charge_id"],chat))
        return "سوپاس. بۆ ڤەکرنا پلانا خۆ /plus بنێرە.", [[PLUS,bot.BACK]]
    refund=msg.get("refunded_payment")
    if refund:
        db.execute("INSERT INTO plus_receipts VALUES (?,?,1) ON CONFLICT(charge) DO UPDATE SET refunded=1",(refund["telegram_payment_charge_id"],chat))
        return "ستێرک هاتنە زڤڕاندن.",bot.MENU
    if text in ("/paysupport","/support"):
        return ("بۆ هاریکاریا کرینێ، ژمارا وەسلا تێلیگرامێ بۆ خودانێ بۆتی بنێرە • "+support if contact() else "فرۆشتن هێشتا نەهاتیە چالاککرن."),bot.MENU
    mode=s.get("mode")
    if text in (PLUS,"/plus","/terms","/start plus"):
        if owned(db,chat) and text!="/terms":
            if s.get("plus_plan"):
                s["mode"]="plus_view"
                return page(s,bot)
            s["mode"]="plus_days"
            return "تو دڤێی خەتمێ د چەند ڕۆژان دا تەمام بکەی؟ (١–٣٦٥)", [["30","60","90"],[bot.BACK]]
        s["mode"]="plus_terms"
        body=f"ڕووناهی Plus • {price()} ⭐، ئێک پارەدان\nپلانا خەتمێ لدویڤ ژمارا ڕۆژان، دگەل مێژوو و لینکێ ئایەتێ بۆ هەر ڕۆژێ. تو دشێی پلانێ دووبارە چێکەی. هەمی بەشێن دی و AI بەڵاشن.\nهاریکاریا پارەدان و داخوازییا زڤڕاندنێ • {support}"
        return body+("" if selling() else "\nفرۆشتن هێشتا نەهاتیە چالاککرن."), ([[AGREE]] if selling() else [])+[[bot.BACK]]
    if text==AGREE and mode=="plus_terms" and selling() and not owned(db,chat):
        payload=secrets.token_urlsafe(24)
        url=bot.api(token,"createInvoiceLink",title="Ronahi Plus",description="پلانا خەتمێ یا کەسی • ئێک پارەدان",payload=payload,currency="XTR",provider_token="",prices=[{"label":"Ronahi Plus","amount":price()}])
        db.execute("INSERT INTO plus_orders(payload,chat,price) VALUES (?,?,?)",(payload,chat,price()))
        return "بۆ کرینێ فاتوورێ ڤەکە.",{"inline_keyboard":[[{"text":f"کرین • {price()} ⭐","url":url}]]}
    if mode in ("plus_days","plus_view") and owned(db,chat):
        if text==PLAN:
            s["mode"]="plus_days"
            return "ژمارا ڕۆژان ژ ١ تا ٣٦٥ بنێرە.", [["30","60","90"],[bot.BACK]]
        if mode=="plus_days" and text.isdecimal() and len(text)<=3 and 1<=int(text)<=365:
            s.update(plus_plan=[int(text),bot.datetime.now(bot.IRAQ).date().isoformat()],plus_page=0,mode="plus_view")
            return page(s,bot)
        if mode=="plus_view" and text in ("پەڕێ داهاتی","پەڕێ بەری"):
            s["plus_page"]=max(0,min((s["plus_plan"][0]-1)//7*7,s["plus_page"]+(7 if text=="پەڕێ داهاتی" else -7)))
            return page(s,bot)
    if isinstance(mode,str) and mode.startswith("plus_"):
        s["mode"]=None
    return None
