
import os
import ast
import random
import logging
import operator

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)

TOKEN = os.getenv("BOT_TOKEN")


def btn(text, data, style="primary"):
    return InlineKeyboardButton(
        text=text,
        callback_data=data,
        style=style,
    )


def markup(rows):
    return InlineKeyboardMarkup(rows)


def main_menu():
    return markup([
        [btn("🍎 Fruit Build", "fruits", "success"),
         btn("🔥 PvP Combos", "combos", "danger")],
        [btn("🥋 Fighting Style", "styles", "primary"),
         btn("🗡️ Sword & Race", "equipment", "success")],
        [btn("🎯 Mashq rejasi", "practice", "primary"),
         btn("ℹ️ Yordam", "help", "primary")],
    ])


def back_button(destination="home"):
    return markup([[btn("⬅️ Orqaga", destination)]])


FRUITS = {
    "Dough": {
        "style": "Godhuman / Electric Claw",
        "sword": "Cursed Dual Katana (CDK)",
        "race": "Ghoul / Angel",
        "difficulty": "O‘rta–qiyin",
        "tip": "Stun va skill vaqtini mashq qil."
    },
    "Ice": {
        "style": "Godhuman / Sharkman Karate",
        "sword": "CDK / Yama",
        "race": "Angel / Shark",
        "difficulty": "Oson–o‘rta",
        "tip": "Freeze orqali combo boshlashni o‘rgan."
    },
    "Dark": {
        "style": "Godhuman / Electric Claw",
        "sword": "CDK / Shark Anchor",
        "race": "Ghoul / Cyborg",
        "difficulty": "O‘rta",
        "tip": "Stun va yaqin masofali hujumlarni mashq qil."
    },
    "Portal": {
        "style": "Godhuman / Electric Claw",
        "sword": "CDK / Shark Anchor",
        "race": "Ghoul / Angel",
        "difficulty": "Qiyin",
        "tip": "Harakat, joylashuv va sword almashishni mashq qil."
    },
    "Tiger": {
        "style": "Godhuman / Electric Claw",
        "sword": "CDK / Shark Anchor",
        "race": "Ghoul / Angel",
        "difficulty": "O‘rta–qiyin",
        "tip": "Hujum vaqtini va masofani nazorat qil."
    },
    "Gas": {
        "style": "Godhuman / Electric Claw",
        "sword": "CDK / Shark Anchor",
        "race": "Cyborg / Ghoul",
        "difficulty": "O‘rta",
        "tip": "Skill vaqtini va maydon nazoratini mashq qil."
    },
    "Kitsune": {
        "style": "Godhuman / Electric Claw",
        "sword": "CDK / Shark Anchor",
        "race": "Angel / Ghoul",
        "difficulty": "O‘rta",
        "tip": "Mobillikdan foydalan va hujumlarni aniq vaqtla."
    },
    "Dragon": {
        "style": "Godhuman / Electric Claw",
        "sword": "CDK / Shark Anchor",
        "race": "Angel / Ghoul",
        "difficulty": "Qiyin",
        "tip": "Skill ketma-ketligini va transformatsiyani mashq qil."
    },
    "Buddha": {
        "style": "Sharkman Karate / Godhuman",
        "sword": "O‘zingdagi qulay sword",
        "race": "Shark / Ghoul",
        "difficulty": "O‘rta",
        "tip": "Yaqin masofada harakat va hujum vaqtini o‘rgan."
    },
    "Light": {
        "style": "Godhuman / Electric Claw",
        "sword": "CDK / Yama",
        "race": "Angel / Ghoul",
        "difficulty": "O‘rta",
        "tip": "Masofa va skill aniqligini mashq qil."
    },
}


COMBOS = {
    "easy": [
        ("Ice", "Ice Z → Fighting Style Z → Sword skill"),
        ("Dark", "Dark C → Fighting Style Z → Sword skill"),
        ("Dough", "Dough C → Dough X → Fighting Style skill"),
        ("Light", "Light skill → Sword skill → Fighting Style"),
    ],
    "medium": [
        ("Ice", "Ice Z → Sword Z → Fighting Style X → Ice X"),
        ("Dark", "Dark C → Sword skill → Fighting Style X → Dark X"),
        ("Dough", "Dough C → Dough X → Sword skill → Fighting Style"),
        ("Gas", "Gas Z → Sword skill → Gas X → Fighting Style"),
    ],
    "hard": [
        ("Ice", "Ice Z → Sword Z → Fighting Style X → Ice X → Sword X"),
        ("Dark", "Dark C → Sword Z → Fighting Style X → Dark X"),
        ("Dough", "Dough C → Dough X → Sword Z → Fighting Style X"),
        ("Portal", "Portal skill → Sword skill → Fighting Style → Portal"),
    ],
}


TIPS = [
    "🎯 Avval skillni nishonga tekkizishni mashq qil.",
    "⚔️ Combo ichidagi skilllar orasidagi vaqtni o‘rgan.",
    "🏃 Raqibning hujumidan qochishni ham mashq qil.",
    "🧠 Bitta buildni tanlab, uni yaxshilab o‘rgan.",
    "🔧 Stat va mastery buildga mos ekanini tekshir.",
]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "💎 SUMMON PvP COACH\n\n"
        "🏴‍☠️ Blox Fruits PvP yordamching!\n"
        "🍎 Fruit build tanla\n"
        "🔥 Combo ko‘r\n"
        "🥋 Fighting style va sword tanla\n"
        "🎯 Mashq rejasidan foydalan\n\n"
        "👇 Bo‘limni tanla:",
        reply_markup=main_menu(),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "📚 BUYRUQLAR\n\n"
        "/start — asosiy menyu\n"
        "/help — yordam\n\n"
        "Tugmalar orqali bo‘limlarni tanla.",
        reply_markup=main_menu(),
    )


async def show_fruit(query, fruit):
    data = FRUITS[fruit]
    await query.edit_message_text(
        f"🍎 {fruit.upper()} PVP BUILD\n\n"
        f"🎯 Qiyinlik: {data['difficulty']}\n"
        f"🥋 Fighting style: {data['style']}\n"
        f"🗡️ Sword: {data['sword']}\n"
        f"🧬 Race: {data['race']}\n\n"
        f"💡 Maslahat: {data['tip']}\n\n"
        "Eslatma: buildlar tavsiya sifatida berilgan. "
        "Aniq combo natijasi update, stat va masteryga bog‘liq.",
        reply_markup=markup([
            [btn("🔥 Combo katalogi", "combos", "danger")],
            [btn("⬅️ Mevalar", "fruits")],
            [btn("🏠 Asosiy menyu", "home")],
        ]),
    )


async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    key = query.data

    if key == "home":
        await query.edit_message_text(
            "💎 SUMMON PvP COACH\nBo‘limni tanla:",
            reply_markup=main_menu(),
        )

    elif key == "fruits":
        names = list(FRUITS.keys())
        rows = []
        for i in range(0, len(names), 2):
            rows.append([
                btn("🍎 " + name, "fruit:" + name, "success")
                for name in names[i:i + 2]
            ])
        rows.append([btn("⬅️ Menyu", "home")])
        await query.edit_message_text(
            "🍎 MEVANGNI TANLA:",
            reply_markup=markup(rows),
        )

    elif key.startswith("fruit:"):
        fruit = key.split(":", 1)[1]
        if fruit in FRUITS:
            await show_fruit(query, fruit)

    elif key == "combos":
        await query.edit_message_text(
            "🔥 COMBO QIYINLIGINI TANLA:",
            reply_markup=markup([
                [btn("🟢 Oson", "combo:easy", "success")],
                [btn("🟡 O‘rta", "combo:medium", "primary")],
                [btn("🔴 Qiyin", "combo:hard", "danger")],
                [btn("⬅️ Menyu", "home")],
            ]),
        )

    elif key.startswith("combo:"):
        level = key.split(":", 1)[1]
        combos = COMBOS.get(level)
        if combos:
            title = {"easy": "🟢 OSON", "medium": "🟡 O‘RTA",
                     "hard": "🔴 QIYIN"}.get(level, "COMBO")
            text = f"🔥 {title} COMBOLAR\n\n"
            for fruit, sequence in combos:
                text += f"🍎 {fruit}\n{sequence}\n\n"
            text += (
                "⚠️ Namunaviy combo ketma-ketliklari. "
                "Barcha skilllar har doim ulanmasligi mumkin."
            )
            await query.edit_message_text(
                text,
                reply_markup=markup([
                    [btn("⬅️ Qiyinliklar", "combos")],
                    [btn("🏠 Menyu", "home")],
                ]),
            )

    elif key == "styles":
        await query.edit_message_text(
            "🥋 FIGHTING STYLE\n\n"
            "• Godhuman — ko‘p buildlarda ishlatiladi.\n"
            "• Electric Claw — tezkor hujumlar uchun.\n"
            "• Sharkman Karate — yaqin jang uchun.\n"
            "• Dragon Talon — alohida mashq talab qiladi.\n\n"
            "Eng mos tanlov meva va o‘yin uslubiga bog‘liq.",
            reply_markup=back_button(),
        )

    elif key == "equipment":
        await query.edit_message_text(
            "🗡️ SWORD VA RACE\n\n"
            "Sword: CDK, Yama, Shark Anchor kabi variantlarni "
            "o‘zingdagi qurolga qarab tanla.\n\n"
            "Angel: himoya va harakat imkoniyatlari.\n"
            "Ghoul: ayrim jang uslublari bilan mos.\n"
            "Cyborg: raqibga bosim berishga mos.\n"
            "Shark: himoyaga urg‘u beradi.\n\n"
            "Build va race imkoniyatlarini o‘yin ichida tekshir.",
            reply_markup=back_button(),
        )

    elif key == "practice":
        await query.edit_message_text(
            "🎯 PVP MASHQ REJASI\n\n"
            "1. 5 daqiqa: skill aniqligi.\n"
            "2. 5 daqiqa: ikkita skillni ulash.\n"
            "3. 5 daqiqa: dodging va masofa.\n"
            "4. 5 daqiqa: do‘st bilan sparring.\n\n"
            "Har kuni o‘zing qiynalayotgan bitta narsani mashq qil.",
            reply_markup=back_button(),
        )

    elif key == "help":
        await help_command_from_callback(query)

async def help_command_from_callback(query):
    await query.edit_message_text(
        "/start — asosiy menyu\n/help — yordam\n\n"
        "Tugmalardan foydalanib build va combo tanla.",
        reply_markup=back_button(),
    )


def main():
    if not TOKEN:
        raise RuntimeError(
            "BOT_TOKEN topilmadi! Render Environment Variables "
            "bo‘limiga BOT_TOKEN qo‘sh."
        )

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(callback))

    print("SUMMON PvP COACH ishga tushdi!")
    app.run_polling()


if __name__ == "__main__":
    main()
