await q.edit_message_text(
            "🥋 FIGHTING STYLE\n\n"
            "• Godhuman — ko‘p combo uchun universal variant.\n"
            "• Electric Claw — tezkor hujumlar uchun.\n"
            "• Sharkman Karate — ayrim yaqin masofali buildlar uchun.\n"
            "• Dragon Talon — o‘rganib ishlatish kerak.\n\n"
            "Tanlov meva, mastery va o‘yin uslubingga bog‘liq.",
            reply_markup=back()
        )

    elif key == "equipment":
        await q.edit_message_text(
            "🗡️ SWORD VA RACE\n\n"
            "Sword: CDK, Shark Anchor yoki Yama kabi variantlarni "
            "o‘zingdagi qurol va buildga qarab tanla.\n\n"
            "Race: Angel — himoya va havoda harakat; "
            "Ghoul — ayrim jang uslublari bilan mos; "
            "Cyborg — hujum bosimi; Shark — himoyaga urg‘u.\n\n"
            "Eng yaxshisi raqib va buildga bog‘liq.",
            reply_markup=back()
        )

    elif key == "practice":
        await q.edit_message_text(
            "🎯 15 DАQIQA MASHQ REJASI\n\n"
            "1️⃣ 5 daqiqa — skill nishonga tekkizish.\n"
            "2️⃣ 5 daqiqa — 2 ta skillni ulash.\n"
            "3️⃣ 5 daqiqa — do‘st bilan sparring.\n\n"
            "Har safar bitta xatoni aniqlab, qayta mashq qil.",
            reply_markup=back()
        )

    elif key == "help":
        await q.edit_message_text(
            "/start — asosiy menyu\n"
            "/help — yordam\n\n"
            "Mevangni tanla, buildni ko‘r va combo bo‘limidan "
            "qiyinlikni tanla.",
            reply_markup=back()
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "💎 SUMMON PvP COACH\n/start — menyu\n/help — yordam",
        reply_markup=menu()
    )

def main():
    if not TOKEN:
        raise RuntimeError("Render Environment'da BOT_TOKEN yo‘q!")

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(callback))
    print("SUMMON PvP COACH ishga tushdi!")
    app.run_polling()

if name == "main":
    main()
