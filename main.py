
import os
import random
import json
from pathlib import Path
from datetime import date

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

TOKEN = os.getenv("BOT_TOKEN", "")
DB = Path("players.json")
players = json.loads(DB.read_text(encoding="utf-8")) if DB.exists() else {}
games = {}


def save():
    DB.write_text(json.dumps(players, ensure_ascii=False), encoding="utf-8")


def player(user):
    key = str(user.id)
    if key not in players:
        players[key] = {
            "name": user.first_name or "Oyinchi",
            "score": 0,
            "wins": 0,
            "daily": ""
        }
    players[key]["name"] = user.first_name or "Oyinchi"
    return players[key]


def menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🟢 SONNI TOP", callback_data="guess"),
            InlineKeyboardButton("🔵 TOSH-QAYCHI", callback_data="rps")
        ],
        [
            InlineKeyboardButton("🔴 MATEMATIKA", callback_data="math"),
            InlineKeyboardButton("🏆 REYTING", callback_data="top")
        ],
        [
            InlineKeyboardButton("🎁 BONUS", callback_data="bonus"),
            InlineKeyboardButton("👤 PROFIL", callback_data="profile")
        ]
    ])


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    player(update.effective_user)
    save()
    await update.effective_message.reply_text(
        "🎮 SUMMON GAME\n"
        "🔴━━━━━━━━━━━━🔵\n\n"
        f"Salom, {update.effective_user.first_name}!\n\n"
        "🟢 Sonni top — yashirin sonni top.\n"
        "🔵 Tosh-qaychi — botga qarshi o‘yna.\n"
        "🔴 Matematika — misollarni yech.\n"
        "🏆 Reytingda yuqoriga ko‘taril!\n\n"
        "O‘yinni tanla 👇",
        reply_markup=menu()
    )


async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    p = player(q.from_user)
    uid = q.from_user.id
    data = q.data

    if data == "guess":
        games[uid] = {"type": "guess", "n": random.randint(1, 20), "tries": 0}
        return await q.edit_message_text(
            "🟢 SONNI TOP\n1 dan 20 gacha son o‘yladim.\nSonni chatga yoz!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 MENYU", callback_data="home")]
            ])
        )

    if data == "math":
        a, b = random.randint(2, 15), random.randint(2, 15)
        op = random.choice(["+", "-", "×"])
        ans = a + b if op == "+" else a - b if op == "-" else a * b
        games[uid] = {"type": "math", "ans": ans}
        return await q.edit_message_text(
            f"🔴 MATEMATIKA\n\nHisobla: {a} {op} {b} = ?\nJavobni raqam bilan yoz!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 MENYU", callback_data="home")]
            ])
        )

    if data == "rps":
        return await q.edit_message_text(
            "🔵 TOSH — QAYCHI — QOG‘OZ\nTanlovingni qil:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🪨 Tosh", callback_data="r:rock"),
                InlineKeyboardButton("📄 Qog‘oz", callback_data="r:paper"),
                InlineKeyboardButton("✂️ Qaychi", callback_data="r:scissors")
            ], [
                InlineKeyboardButton("🏠 MENYU", callback_data="home")
            ]])
        )

    if data.startswith("r:"):
        yours = data.split(":")[1]
        bot = random.choice(["rock", "paper", "scissors"])
        names = {"rock": "🪨 Tosh", "paper": "📄 Qog‘oz", "scissors": "✂️ Qaychi"}
        beats = {"rock": "scissors", "scissors": "paper", "paper": "rock"}

        if yours == bot:
            result = "🤝 Durrang!"
        elif beats[yours] == bot:
            p["score"] += 5
            p["wins"] += 1
            result = "🎉 Yutding! +5 ball"
        else:
            result = "🙂 Bu safar bot yutdi."

        save()
        return await q.edit_message_text(
            f"Sen: {names[yours]}\nBot: {names[bot]}\n\n{result}\n"
            f"⭐ Ball: {p['score']}",
            reply_markup=menu()
        )

    if data == "bonus":
        today = date.today().isoformat()
        if p.get("daily") == today:
            msg = "🎁 Bonusni bugun olib bo‘lgansan!"
        else:
            amount = random.randint(10, 25)
            p["score"] += amount
            p["daily"] = today
            msg = f"🎁 +{amount} ball! Jami: {p['score']}"
            save()
        return await q.edit_message_text(msg, reply_markup=menu())

    if data == "profile":
        return await q.edit_message_text(
            f"👤 PROFIL\n\nIsm: {esc(p['name'])}\n"
            f"⭐ Ball: {p['score']}\n🏆 G‘alabalar: {p['wins']}",
            reply_markup=menu()
        )

    if data == "top":
        ranked = sorted(players.values(), key=lambda x: x["score"], reverse=True)[:10]
        text = "🏆 TOP O‘YINCHILAR\n\n"
        for i, item in enumerate(ranked, 1):
            text += f"{i}. {esc(item['name'])} — {item['score']} ball\n"
        return await q.edit_message_text(text, reply_markup=menu())

    if data == "home":
        return await q.edit_message_text("🎮 SUMMON GAME\nO‘yinni tanla 👇", reply_markup=menu())


async def messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    p = player(update.effective_user)
    game = games.get(uid)
    text = (update.effective_message.text or "").strip()

    if not game:
        return await update.effective_message.reply_text(
            "🎮 O‘ynash uchun /start ni bos.", reply_markup=menu()
        )

    if not text.lstrip("-").isdigit():
        return await update.effective_message.reply_text("Javobni raqam bilan yoz.")

    value = int(text)

    if game["type"] == "guess":
        game["tries"] += 1
        if value == game["n"]:
            points = max(3, 12 - game["tries"])
            p["score"] += points
            p["wins"] += 1
            del games[uid]
            result = f"🎉 To‘g‘ri! +{points} ball!"
        elif game["tries"] >= 6:
            del games[uid]
            result = f"Urinish tugadi. Son {game['n']} edi."
        else:
            result = ("⬆️ Kattaroq son!" if value < game["n"] else "⬇️ Kichikroq son!")
    else:
        if value == game["ans"]:
            p["score"] += 5
            p["wins"] += 1
            result = "🟢 To‘g‘ri! +5 ball!"
        else:
            result = f"🔴 Noto‘g‘ri. Javob: {game['ans']}"
        del games[uid]

    save()
    await update.effective_message.reply_text(result, reply_markup=menu())


async def main():
    if not TOKEN:
        raise RuntimeError("Render Environment ichiga BOT_TOKEN kiriting.")

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, messages))
    print("SUMMON GAME ishga tushdi!")
    await app.run_polling()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
