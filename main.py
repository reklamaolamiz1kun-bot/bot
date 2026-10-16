import os
import logging
import sqlite3
import httpx
from datetime import datetime, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters, ConversationHandler)

TOKEN = os.getenv('BOT_TOKEN', '').strip()
ADMIN_IDS = {int(x.strip()) for x in os.getenv('ADMIN_IDS', '').split(',') if x.strip().isdigit()}
DB_PATH = os.getenv('DB_PATH', 'market.db')
TITLE, DESCRIPTION, PRICE, CONTACT, RATE_ID, RATE_SCORE, RATE_COMMENT, AVATAR_USERNAME = range(8)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
logging.getLogger('httpx').setLevel(logging.WARNING)
log = logging.getLogger('summon_market')


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with db() as c:
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT,
            joined_at TEXT NOT NULL)''')
        c.execute('''CREATE TABLE IF NOT EXISTS listings (
            id INTEGER PRIMARY KEY AUTOINCREMENT, seller_id INTEGER NOT NULL,
            title TEXT NOT NULL, description TEXT NOT NULL, price TEXT NOT NULL,
            contact TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL)''')
        c.execute('''CREATE TABLE IF NOT EXISTS ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT, listing_id INTEGER NOT NULL,
            rater_id INTEGER NOT NULL, seller_id INTEGER NOT NULL,
            score INTEGER NOT NULL, comment TEXT NOT NULL, created_at TEXT NOT NULL,
            UNIQUE(listing_id, rater_id))''')


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def register_user(user):
    with db() as c:
        c.execute('INSERT INTO users(user_id, username, first_name, joined_at) VALUES(?,?,?,?) '
                  'ON CONFLICT(user_id) DO UPDATE SET username=excluded.username, first_name=excluded.first_name',
                  (user.id, user.username or '', user.first_name or '', now()))


def button(text, data, style='primary'):
    # Button colors are supported only by compatible Telegram clients/Bot API versions.
    try:
        return InlineKeyboardButton(text, callback_data=data, style=style)
    except TypeError:
        return InlineKeyboardButton(text, callback_data=data)


def kb(rows):
    return InlineKeyboardMarkup(rows)


def home_kb():
    return kb([
        [button('🛍 E’lonlarni ko‘rish', 'browse', 'success'), button('➕ E’lon berish', 'new', 'primary')],
        [button('⭐ Reytinglar', 'ratings', 'success'), button('👤 Profilim', 'profile', 'primary')],
        [button('🧑‍🎤 Roblox Avatar Search', 'avatar_search', 'danger')],
        [button('📜 Qoidalar', 'rules', 'danger')],
    ])


def back_home():
    return kb([[button('🏠 Bosh menyu', 'home', 'primary')]])


def is_admin(user_id):
    return user_id in ADMIN_IDS

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    register_user(user)
    text = (f"🛒 SUMMON ROBLOX MARKET\n\nSalom, {user.first_name}!\n"
            "Roblox o‘yinidagi itemlar va xizmatlar uchun e’lonlar maydoni.\n\n"
            "✅ E’lonlar admin tekshiruvidan o‘tadi.\n"
            "⚠️ Parol, cookie yoki akkauntga kirish ma’lumotlarini so‘ramang va yubormang.")
    await update.effective_message.reply_text(text, reply_markup=home_kb())

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text('/start — menyu\n/cancel — amalni bekor qilish\n/admin — admin panel (adminlar uchun)')

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.effective_message.reply_text('Amal bekor qilindi.', reply_markup=home_kb())
    return ConversationHandler.END

async def new_listing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    context.user_data.clear()
    await update.callback_query.message.reply_text('E’lon sarlavhasini yoz (5–70 belgi).\n/cancel — bekor qilish')
    return TITLE

async def title_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    title = update.message.text.strip()
    if len(title) < 5 or len(title) > 70:
        await update.message.reply_text('Sarlavha 5–70 belgi bo‘lsin. Qayta yoz:')
        return TITLE
    context.user_data['title'] = title
    await update.message.reply_text('E’lon tavsifini yoz (10–500 belgi). Akkaunt paroli yoki cookie kiritma.')
    return DESCRIPTION

async def description_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    desc = update.message.text.strip()
    if len(desc) < 10 or len(desc) > 500:
        await update.message.reply_text('Tavsif 10–500 belgi bo‘lsin. Qayta yoz:')
        return DESCRIPTION
    context.user_data['description'] = desc
    await update.message.reply_text('Narxni yoz (masalan: 25 000 so‘m, bepul yoki kelishiladi):')
    return PRICE

async def price_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    price = update.message.text.strip()
    if len(price) > 40:
        await update.message.reply_text('Narxni qisqaroq yoz:')
        return PRICE
    context.user_data['price'] = price
    await update.message.reply_text('Aloqa usulini yoz: Telegram username yoki “shu bot orqali”. Telefon raqam majburiy emas.')
    return CONTACT

async def contact_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.text.strip()
    if len(contact) > 100:
        await update.message.reply_text('Aloqa ma’lumoti 100 belgidan oshmasin:')
        return CONTACT
    user = update.effective_user
    data = context.user_data
    with db() as c:
        cur = c.execute('INSERT INTO listings(seller_id,title,description,price,contact,status,created_at) VALUES(?,?,?,?,?,?,?)',
            (user.id, data['title'], data['description'], data['price'], contact, 'pending', now()))
        listing_id = cur.lastrowid
    await update.message.reply_text(f'✅ E’lon #{listing_id} admin tekshiruviga yuborildi. Tasdiqlansa hammaga ko‘rinadi.', reply_markup=home_kb())
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(admin_id,
                f'🆕 Yangi e’lon #{listing_id}\nSotuvchi: {user.full_name} (@{user.username or "yo‘q"})\n'
                f'{data["title"]}\n{data["description"]}\nNarx: {data["price"]}\nAloqa: {contact}',
                reply_markup=kb([[button('✅ Tasdiqlash', f'approve:{listing_id}', 'success'),
                                  button('❌ Rad etish', f'reject:{listing_id}', 'danger')]]))
        except Exception:
            log.exception('Admin notification failed')
    context.user_data.clear()
    return ConversationHandler.END

async def browse(query, context):
    with db() as c:
        rows = c.execute("SELECT id,title,description,price,seller_id FROM listings WHERE status='approved' ORDER BY id DESC LIMIT 10").fetchall()
    if not rows:
        await query.edit_message_text('Hozircha tasdiqlangan e’lon yo‘q.', reply_markup=back_home())
        return
    for row in rows:
        with db() as c:
            rating = c.execute('SELECT AVG(score) avg, COUNT(*) n FROM ratings WHERE seller_id=?', (row['seller_id'],)).fetchone()
        avg = f"{rating['avg']:.1f}/5 ({rating['n']} ta)" if rating['n'] else 'hali reyting yo‘q'
        text = (f"🛍 E’lon #{row['id']}\n{row['title']}\n\n{row['description']}\n\n"
                f"💰 Narx: {row['price']}\n⭐ Sotuvchi reytingi: {avg}")
        await context.bot.send_message(query.message.chat_id, text, reply_markup=kb([
            [button('✉️ Sotuvchi bilan aloqa', f'contact:{row["id"]}', 'success'),
             button('⭐ Baholash', f'rate:{row["id"]}', 'primary')]]))
    await context.bot.send_message(query.message.chat_id, 'E’lonlar tugadi.', reply_markup=back_home())

async def avatar_search_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.message.reply_text(
        "🧑‍🎤 ROBLOX AVATAR SEARCH\n\n"
        "Roblox username’ni yubor. Masalan: Builderman\n"
        "Display name emas, profil username kerak.\n"
        "/cancel — bekor qilish"
    )
    return AVATAR_USERNAME


async def avatar_username_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = (update.message.text or '').strip()
    if not username or len(username) > 20 or not username.replace('_', '').isalnum():
        await update.message.reply_text('Username noto‘g‘ri ko‘rinadi. Faqat Roblox username yubor (20 belgigacha):')
        return AVATAR_USERNAME

    await update.message.reply_text(f'🔎 @{username} qidirilyapti...')
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            response = await client.post(
                'https://users.roblox.com/v1/usernames/users',
                json={'usernames': [username], 'excludeBannedUsers': False},
            )
            response.raise_for_status()
            results = response.json().get('data', [])
            if not results:
                await update.message.reply_text('❌ Bu username topilmadi. Imlo xatosini tekshirib qayta urin.', reply_markup=home_kb())
                return ConversationHandler.END
            user = results[0]
            user_id = user['id']
            real_username = user.get('name', username)
            display_name = user.get('displayName', real_username)
            thumb_response = await client.get(
                'https://thumbnails.roblox.com/v1/users/avatar?userIds=' + str(user_id) + '&size=720x720&format=Png&isCircular=false'
            )
            thumb_response.raise_for_status()
            thumb_data = thumb_response.json().get('data', [])
            image_url = thumb_data[0].get('imageUrl') if thumb_data else None

        caption = (
            f'🧑‍🎤 ROBLOX AVATAR\n\n'
            f'👤 Display name: {display_name}\n'
            f'🔎 Username: @{real_username}\n'
            f'🆔 User ID: {user_id}\n'
            f'🔗 Profil: https://www.roblox.com/users/{user_id}/profile'
        )
        if image_url:
            await update.message.reply_photo(photo=image_url, caption=caption, reply_markup=kb([
                [button('🔗 Roblox profilini ochish', 'avatar_profile:' + str(user_id), 'success')],
                [button('🏠 Bosh menyu', 'home', 'primary')],
            ]))
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
        per_chat=True, per_user=True,
    )
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('help', help_cmd))
    app.add_handler(CommandHandler('cancel', cancel))
    app.add_handler(CommandHandler('admin', admin_cmd))
    app.add_handler(avatar_conv)
    app.add_handler(listing_conv)
    app.add_handler(rating_conv)
    app.add_handler(CallbackQueryHandler(callback))
    app.add_error_handler(error_handler)
    log.info('SUMMON Roblox Market started')
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
