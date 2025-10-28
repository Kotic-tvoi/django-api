import os, time, requests
from datetime import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from wb_coeff_storage.models import TgSubscriber

WB_API = "https://supplies-api.wildberries.ru/api/v1/acceptance/coefficients"
ISO_FMT = "%Y-%m-%dT%H:%M:%SZ"

def env_list(name: str):
    raw = os.getenv(name, "")
    return [x.strip() for x in raw.split(",") if x.strip()]

def env_ids(name: str):
    out = []
    for s in env_list(name):
        try: out.append(int(s))
        except: pass
    return out

# ---------- Telegram ----------
def tg_send_one(chat_id: int, text: str) -> bool:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("⚠️ TELEGRAM_BOT_TOKEN не задан.")
        return False
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "disable_web_page_preview": True},
            timeout=20,
        )
        r.raise_for_status()
        return True
    except requests.RequestException as e:
        print(f"❌ Telegram send error to {chat_id}: {e}")
        return False

def tg_get_updates(offset=None):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        return {"ok": False, "result": []}
    params = {"timeout": 0}
    if offset is not None:
        params["offset"] = offset
    try:
        return requests.get(
            f"https://api.telegram.org/bot{token}/getUpdates",
            params=params,
            timeout=20,
        ).json()
    except requests.RequestException as e:
        print(f"❌ getUpdates error: {e}")
        return {"ok": False, "result": []}

def handle_subscriptions(state):
    """
    /start => active=True (добавить/включить),
    /stop  => active=False (отписать).
    Любое личное сообщение — создаёт подписку (active=True).
    """
    last_id = state.get("last_update_id")
    resp = tg_get_updates(offset=last_id + 1 if last_id else None)
    if not resp.get("ok"):
        return
    for upd in resp.get("result", []):
        state["last_update_id"] = upd["update_id"]
        msg = upd.get("message") or upd.get("edited_message")
        if not msg:
            continue
        chat = msg.get("chat") or {}
        if chat.get("type") != "private":
            continue  # работаем только с личкой

        cid = chat.get("id")
        if cid is None:
            continue
        text = (msg.get("text") or "").strip().lower()

        user = msg.get("from") or {}
        first_name = user.get("first_name")
        last_name  = user.get("last_name")
        username   = user.get("username")

        sub, created = TgSubscriber.objects.get_or_create(
            chat_id=cid,
            defaults={"first_name": first_name, "last_name": last_name, "username": username, "active": True},
        )

        changed = False
        for f, v in (("first_name", first_name), ("last_name", last_name), ("username", username)):
            if v is not None and getattr(sub, f) != v:
                setattr(sub, f, v); changed = True

        if text in ("/start", "start"):
            if not sub.active:
                sub.active = True; changed = True
            tg_send_one(cid, "✅ Подписка оформлена. Вы будете получать уведомления о слотах WB.")
        elif text in ("/stop", "stop"):
            if sub.active:
                sub.active = False; changed = True
            tg_send_one(cid, "🔕 Уведомления выключены.")
        else:
            if created:
                tg_send_one(cid, "✅ Подписка оформлена. (Подсказки: /stop для отключения)")

        if changed or created:
            sub.save()

def tg_broadcast(text: str):
    qs = TgSubscriber.objects.filter(active=True).only("chat_id")
    count = 0
    for sub in qs.iterator():
        ok = tg_send_one(sub.chat_id, text)
        print(("✅ отправлено" if ok else "⛔ не отправлено"), "→", sub.chat_id)
        count += 1
    if count == 0:
        print("ℹ️ Нет активных подписчиков. Напишите боту /start из лички.")

# ---------- WB ----------
def fetch_wb():
    token = os.getenv("WB_API_TOKEN")
    if not token:
        raise RuntimeError("WB_API_TOKEN не задан")
    headers = {"Authorization": token, "Content-Type": "application/json"}

    ids = env_ids("WB_WAREHOUSE_IDS")
    params = {}
    if ids:
        params["warehouseIDs"] = ",".join(map(str, ids))  # WB ждёт строку

    r = requests.get(WB_API, headers=headers, params=params, timeout=30)
    r.raise_for_status()
    return r.json()

def pick_available_slots(items):
    """
    Строго по правилам приёмки:
    - allowUnload == True
    - coefficient ∈ {0, 1}
    Фильтры: по ID (если заданы), иначе по подстроке имени (если заданы).
    """
    ids = set(env_ids("WB_WAREHOUSE_IDS"))
    names = env_list("WB_WAREHOUSE_NAMES")

    out = []
    for it in items:
        if not it.get("allowUnload", False):
            continue
        try:
            coef = float(it.get("coefficient", -1))
        except Exception:
            continue
        if coef not in (0.0, 1.0):
            continue

        wh_id_raw = it.get("warehouseID") or it.get("warehouseId")  # у WB ключ с большой 'D'
        wh_name = (it.get("warehouseName") or "")
        date_iso = it.get("date")
        if wh_id_raw is None or not date_iso:
            continue
        try:
            wh_id = int(wh_id_raw)
        except Exception:
            continue

        if ids and wh_id not in ids:
            continue
        if not ids and names:
            name_l = wh_name.lower()
            if not any(n.lower() in name_l for n in names):
                continue

        out.append({"warehouseId": wh_id, "warehouseName": wh_name, "date": date_iso})

    out.sort(key=lambda x: (x["warehouseName"], x["date"]))
    return out

def format_message(slots):
    if not slots:
        return ""
    lines = ["Найдены слоты WB (allowUnload=true, coef∈{0,1}):"]
    cur = None
    for s in slots:
        if s["warehouseName"] != cur:
            cur = s["warehouseName"]
            lines.append(f"\n📦 {cur}:")
        lines.append(f"• {s['date']}")  # ISO UTC
    return "\n".join(lines)

# ---------- Команда ----------
class Command(BaseCommand):
    help = "WB-бот без TELEGRAM_CHAT_ID: шлёт всем, кто нажал /start (подписался)."

    def handle(self, *args, **opts):
        # На всякий отключим webhook, чтобы getUpdates работал
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        if token:
            try:
                requests.get(f"https://api.telegram.org/bot{token}/setWebhook", params={"url": ""}, timeout=10)
            except Exception:
                pass

        interval = int(os.getenv("WB_POLL_INTERVAL_SEC", "120"))
        state = {"last_update_id": None}

        tg_broadcast("🚀 WB-бот запущен. Напишите /start, чтобы подписаться.")

        # Первый проход + приём подписок
        handle_subscriptions(state)
        try:
            data = fetch_wb()
            slots = pick_available_slots(data)
            if slots:
                tg_broadcast(format_message(slots))
            else:
                print("ℹ️ Пока подходящих слотов нет.")
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Ошибка первого прохода: {e}"))

        # Цикл
        while True:
            try:
                time.sleep(interval)
                handle_subscriptions(state)

                data = fetch_wb()
                slots = pick_available_slots(data)
                if slots:
                    tg_broadcast(format_message(slots))
                else:
                    print("ℹ️ Нет слотов на этом цикле.")
            except KeyboardInterrupt:
                tg_broadcast("🛑 WB-бот остановлен.")
                break
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Ошибка: {e}"))
                time.sleep(10)
