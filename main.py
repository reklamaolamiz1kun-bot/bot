        else:
            await update.message.reply_text(caption + '\n\nAvatar rasmi hozircha olinmadi.', reply_markup=home_kb())
    except httpx.TimeoutException:
        await update.message.reply_text('⏳ Roblox serveri javob bermadi. Birozdan keyin urin.', reply_markup=home_kb())
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        log.warning('Roblox avatar lookup failed: %s', exc)
        await update.message.reply_text('⚠️ Roblox ma’lumotini olishda xato bo‘ldi. Keyinroq urin.', reply_markup=home_kb())
    return ConversationHandler.END


async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    data = q.data
    if data.startswith(('approve:', 'reject:')) and not is_admin(q.from_user.id):
        await q.answer('Bu amal faqat admin uchun.', show_alert=True)
        return
    await q.answer()
    if data == 'home':
        await q.edit_message_text('🛒 SUMMON ROBLOX MARKET\nKerakli bo‘limni tanla:', reply_markup=home_kb())
    elif data == 'browse':
        await browse(q, context)
    elif data == 'avatar_search':
        return await avatar_search_start(update, context)
    elif data.startswith('avatar_profile:'):
        user_id = data.split(':', 1)[1]
        await q.message.reply_text(f'https://www.roblox.com/users/{user_id}/profile')
    elif data == 'new':
        return await new_listing(update, context)
    elif data == 'rules':
        await q.edit_message_text('📜 MARKET QOIDALARI\n\n• E’lonlar admin tomonidan tekshiriladi.\n• Roblox akkauntlarini, parol, cookie yoki login ma’lumotlarini sotish/so‘rash mumkin emas.\n• Aldov yoki soxta e’lonlar taqiqlanadi.\n• To‘lovdan oldin sotuvchini tekshiring; bot to‘lovni kafolatlamaydi.', reply_markup=back_home())
    elif data == 'profile':
        user = q.from_user
        with db() as c:
            listings = c.execute('SELECT COUNT(*) n FROM listings WHERE seller_id=?', (user.id,)).fetchone()['n']
            rating = c.execute('SELECT AVG(score) avg, COUNT(*) n FROM ratings WHERE seller_id=?', (user.id,)).fetchone()
        avg = f"{rating['avg']:.1f}/5 ({rating['n']} ta baho)" if rating['n'] else 'hali yo‘q'
        await q.edit_message_text(f'👤 Profil\nID: {user.id}\nE’lonlar: {listings}\nReyting: {avg}', reply_markup=back_home())
    elif data == 'ratings':
        with db() as c:
            rows = c.execute('SELECT seller_id, AVG(score) avg, COUNT(*) n FROM ratings GROUP BY seller_id ORDER BY avg DESC, n DESC LIMIT 10').fetchall()
        if not rows:
            text = '⭐ Hali reytinglar yo‘q.'
        else:
            text = '⭐ TOP SOTUVCHILAR\n\n' + '\n'.join(f"{i+1}. ID {r['seller_id']} — {r['avg']:.1f}/5 ({r['n']} ta)" for i,r in enumerate(rows))
        await q.edit_message_text(text, reply_markup=back_home())
    elif data.startswith('approve:') or data.startswith('reject:'):
        action, sid = data.split(':')
        status = 'approved' if action == 'approve' else 'rejected'
        with db() as c:
            c.execute('UPDATE listings SET status=? WHERE id=? AND status=?', (status, int(sid), 'pending'))
            row = c.execute('SELECT seller_id,title FROM listings WHERE id=?', (int(sid),)).fetchone()
        await q.edit_message_reply_markup(reply_markup=None)
        await q.message.reply_text(f'#{sid} {"tasdiqlandi ✅" if status == "approved" else "rad etildi ❌"}')
        if row:
            try:
                await context.bot.send_message(row['seller_id'], f'E’lon #{sid} holati: {"tasdiqlandi" if status == "approved" else "rad etildi"}.\n{row["title"]}')
            except Exception:
                pass
    elif data.startswith('contact:'):
        lid = int(data.split(':')[1])
        with db() as c:
            row = c.execute("SELECT seller_id,contact,title FROM listings WHERE id=? AND status='approved'", (lid,)).fetchone()
        if not row:
            await q.message.reply_text('E’lon topilmadi.')
        elif row['seller_id'] == q.from_user.id:
            await q.message.reply_text('Bu sening e’loning.')
        else:
            await q.message.reply_text(f"✉️ {row['title']}\nSotuvchi aloqa ma’lumoti: {row['contact']}\n\nShaxsiy ma’lumot va to‘lovda ehtiyot bo‘l.")
    elif data.startswith('rate:'):
        lid = int(data.split(':')[1])
        with db() as c:
            row = c.execute("SELECT seller_id FROM listings WHERE id=? AND status='approved'", (lid,)).fetchone()
            exists = c.execute('SELECT 1 FROM ratings WHERE listing_id=? AND rater_id=?', (lid, q.from_user.id)).fetchone()
        if not row or row['seller_id'] == q.from_user.id or exists:
            await q.message.reply_text('Bu e’lonni baholab bo‘lmaydi (o‘zingniki yoki avval baholangan).')
        else:
            context.user_data['rate_listing'] = lid
            context.user_data['rate_seller'] = row['seller_id']
            await q.message.reply_text('Sotuvchiga 1 dan 5 gacha baho ber:', reply_markup=kb([[button(str(n)+' ⭐', f'score:{n}', 'success' if n >= 4 else 'primary') for n in range(1,6)]]))
    elif data.startswith('score:'):
        score = int(data.split(':')[1])
        if not 1 <= score <= 5 or 'rate_listing' not in context.user_data:
            await q.message.reply_text('Baholash sessiyasi tugagan. E’londan qayta boshlang.')
        else:
            context.user_data['rate_score'] = score
            await q.message.reply_text('Qisqa izoh yoz (yoki “-”):')
            return RATE_COMMENT
    elif data == 'admin':
        if not is_admin(q.from_user.id):
            await q.answer('Ruxsat yo‘q', show_alert=True)
            return
        with db() as c:
            pending = c.execute("SELECT COUNT(*) n FROM listings WHERE status='pending'").fetchone()['n']
            users = c.execute('SELECT COUNT(*) n FROM users').fetchone()['n']
            total = c.execute('SELECT COUNT(*) n FROM listings').fetchone()['n']
        await q.edit_message_text(f'🛠 ADMIN PANEL\nFoydalanuvchilar: {users}\nJami e’lonlar: {total}\nKutilayotgan e’lonlar: {pending}', reply_markup=back_home())

async def save_rating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    comment = update.message.text.strip()[:250]
    lid = context.user_data.get('rate_listing')
    seller = context.user_data.get('rate_seller')
    score = context.user_data.get('rate_score')
    if not lid or not seller or not score:
        await update.message.reply_text('Baholash topilmadi. E’londan qayta boshlang.')
        return ConversationHandler.END
    try:
        with db() as c:
            c.execute('INSERT INTO ratings(listing_id,rater_id,seller_id,score,comment,created_at) VALUES(?,?,?,?,?,?)',
                      (lid, update.effective_user.id, seller, score, comment, now()))
        await update.message.reply_text('⭐ Bahoying saqlandi. Rahmat!', reply_markup=home_kb())
    except sqlite3.IntegrityError:
        await update.message.reply_text('Bu e’lonni avval baholagansan.', reply_markup=home_kb())
    context.user_data.clear()
    return ConversationHandler.END

async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text('Bu buyruq faqat admin uchun.')
        return
    with db() as c:
        pending = c.execute("SELECT id,title,description,price,seller_id FROM listings WHERE status='pending' ORDER BY id LIMIT 10").fetchall()
        users = c.execute('SELECT COUNT(*) n FROM users').fetchone()['n']
        total = c.execute('SELECT COUNT(*) n FROM listings').fetchone()['n']
    await update.message.reply_text(f'🛠 ADMIN PANEL\nFoydalanuvchilar: {users}\nJami e’lonlar: {total}\nKutilayotgan: {len(pending)}')
    for r in pending:
        await update.message.reply_text(f"#{r['id']} — {r['title']}\n{r['description']}\nNarx: {r['price']}\nSotuvchi ID: {r['seller_id']}", reply_markup=kb([[button('✅ Tasdiqlash', f"approve:{r['id']}", 'success'), button('❌ Rad etish', f"reject:{r['id']}", 'danger')]]))

async def post_init(app):
    await app.bot.set_my_commands([('start', 'Asosiy menyu'), ('help', 'Yordam'), ('cancel', 'Amalni bekor qilish'), ('admin', 'Admin panel')])

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    log.exception('Unhandled bot error', exc_info=context.error)


def main():
    if not TOKEN:
        raise RuntimeError('Render Environment Variables ichida BOT_TOKEN qo‘shilmagan.')
    init_db()
    app = Application.builder().token(TOKEN).post_init(post_init).build()
    avatar_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(avatar_search_start, pattern='^avatar_search$')],
        states={AVATAR_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, avatar_username_step)]},
        fallbacks=[CommandHandler('cancel', cancel)],
        per_chat=True, per_user=True,
    )
    listing_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(new_listing, pattern='^new$')],
        states={
            TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, title_step)],
            DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, description_step)],
            PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, price_step)],
            CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, contact_step)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        per_chat=True, per_user=True,
    )
    rating_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(callback, pattern='^score:[1-5]$')],
        states={RATE_COMMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_rating)]},
        fallbacks=[CommandHandler('cancel', cancel)],
