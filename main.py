import os, re, asyncio, logging, tempfile, shutil, subprocess
from pathlib import Path
from urllib.parse import urlparse
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from yt_dlp import YoutubeDL
from aiohttp import web

TOKEN=os.getenv('BOT_TOKEN'); MAX_MB=int(os.getenv('MAX_FILE_MB','45')); ROOT=Path(os.getenv('WORKDIR','/tmp/summon_media')); ROOT.mkdir(parents=True,exist_ok=True)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s'); log=logging.getLogger('summon-media'); URL_RE=re.compile(r'https?://\S+',re.I)

def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('🟢 MUSIQA QIDIRISH', callback_data='search'), InlineKeyboardButton('🔵 AUDIO / OVOZ', callback_data='audio_help')],
        [InlineKeyboardButton('🔴 YORDAM', callback_data='help'), InlineKeyboardButton('🔴 QOIDALAR', callback_data='rules')],
    ])

def media_menu(job):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('🟢 MUSIQASINI YUKLASH', callback_data='music:'+job)],
        [InlineKeyboardButton('🔵 DUMALOQ VIDEO QILISH', callback_data='round:'+job)],
        [InlineKeyboardButton('🔴 BEKOR QILISH', callback_data='cancel:'+job)],
    ])
def too_big(p): return p.stat().st_size>MAX_MB*1024*1024
def ydl_download(url,folder,audio=False):
    opts={'outtmpl':str(folder/'%(title).60s-%(id)s.%(ext)s'),'noplaylist':True,'quiet':True,'no_warnings':True,'socket_timeout':20,'retries':2}
    if audio: opts.update(format='bestaudio/best',postprocessors=[{'key':'FFmpegExtractAudio','preferredcodec':'mp3','preferredquality':'192'}])
    else: opts.update(format='best[height<=720][ext=mp4]/best[height<=720]/best',merge_output_format='mp4')
    with YoutubeDL(opts) as y: info=y.extract_info(url,download=True)
    ext=['.mp3'] if audio else ['.mp4','.mkv','.webm','.mov']; files=[p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in ext and p.stat().st_size]
    if not files: raise RuntimeError('No output file')
    return max(files,key=lambda p:p.stat().st_mtime),info
def search_song(query,folder):
    opts={'outtmpl':str(folder/'%(title).60s-%(id)s.%(ext)s'),'noplaylist':True,'quiet':True,'no_warnings':True,'format':'bestaudio/best','postprocessors':[{'key':'FFmpegExtractAudio','preferredcodec':'mp3','preferredquality':'192'}]}
    with YoutubeDL(opts) as y: info=y.extract_info('ytsearch1:'+query,download=True)
    entry=(info.get('entries') or [info])[0]; files=[p for p in folder.iterdir() if p.is_file() and p.suffix.lower()=='.mp3']
    if not files: raise RuntimeError('No audio')
    return max(files,key=lambda p:p.stat().st_mtime),entry.get('title',query),entry.get('webpage_url','')
def round_video(src,dst):
    cmd=['ffmpeg','-y','-i',str(src),'-filter_complex','[0:v]split=2[bg][fg];[bg]scale=640:640:force_original_aspect_ratio=increase,crop=640:640,boxblur=20:10[blur];[fg]scale=640:640:force_original_aspect_ratio=decrease[front];[blur][front]overlay=(W-w)/2:(H-h)/2,setsar=1,fps=30,format=yuv420p[v]','-map','[v]','-map','0:a?','-c:v','libx264','-preset','veryfast','-crf','25','-c:a','aac','-b:a','128k','-t','60','-movflags','+faststart',str(dst)]
    subprocess.run(cmd,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
def esc(s): return (s or '').replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
async def start(update:Update,context:ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    name = esc(user.first_name if user else 'do‘st')
    text = (
        '🎧 <b>SUMMON MUSIC</b>\n'
        '🔴━━━━━━━━━━━━━━━━━━🔵\n'
        f'Assalomu alaykum, <b>{name}</b>! 👋\n\n'
        '🟢 <b>VIDEO HAVOLASI</b> — Instagram, TikTok yoki YouTube havolasini yubor.\n'
        '🔵 <b>MUSIQA QIDIRISH</b> — qo‘shiq nomini yoz yoki pastdagi tugmani bos.\n'
        '🔴 <b>AUDIO / OVOZ</b> — audio fayl yoki voice yubor.\n\n'
        '<i>Video kelgach, undan musiqa ajratish yoki dumaloq video tayyorlash mumkin.</i>\n'
        '🔴━━━━━━━━━━━━━━━━━━🔵\n'
        '⚠️ Faqat foydalanishga ruxsating bor kontentni yukla.'
    )
    await update.message.reply_text(text, parse_mode='HTML', reply_markup=menu())
async def help_cmd(update:Update,context:ContextTypes.DEFAULT_TYPE): await update.message.reply_text('Video linkini yubor, keyin 🟢 Musiqasini yuklash yoki 🔵 Dumaloq video qilishni tanla. Qo‘shiq uchun: /song nomi - ijrochi. Ayrim saytlar yuklashni cheklaydi; bot login yoki DRM himoyasini chetlab o‘tmaydi.',reply_markup=menu())
async def text_handler(update:Update,context:ContextTypes.DEFAULT_TYPE):
    text=(update.message.text or '').strip()
    if text.startswith('/'): return
    m=URL_RE.search(text)
    if not m: return await update.message.reply_text('🎵 Qo‘shiq qidirish: /song nomi - ijrochi\nYoki video havolasini yubor.',reply_markup=menu())
    url=m.group(0).rstrip(').,!?]'); parsed=urlparse(url)
    if parsed.scheme not in ('http','https') or not parsed.netloc: return await update.message.reply_text('Havola noto‘g‘ri.')
    folder=Path(tempfile.mkdtemp(prefix='dl_',dir=ROOT)); status=await update.message.reply_text('⏳ Havola tekshirilmoqda…')
    try:
        path,info=await asyncio.to_thread(ydl_download,url,folder,False)
        if too_big(path): return await status.edit_text(f'Fayl {MAX_MB} MB limitidan katta.')
        job=f'{update.effective_user.id}_{int(asyncio.get_running_loop().time()*1000)}'; saved=ROOT/('job_'+job); saved.mkdir(parents=True,exist_ok=True); dest=saved/path.name; shutil.copy2(path,dest); context.bot_data.setdefault('jobs',{})[job]=str(dest)
        await status.delete(); await update.message.reply_text(f'🟢 <b>VIDEO TAYYOR</b>\n🔴━━━━━━━━━━━━━━━━━━🔵\n🎬 <b>{esc(info.get("title") or path.stem)}</b>\n\nQaysi amalni bajarishni tanla:', parse_mode='HTML', reply_markup=media_menu(job))
    except Exception as e: log.warning('Download failed: %s',e); await status.edit_text('❌ Bu havoladan yuklab bo‘lmadi. Sayt cheklagan yoki format qo‘llanmasligi mumkin.')
    finally: shutil.rmtree(folder,ignore_errors=True)
async def song_cmd(update:Update,context:ContextTypes.DEFAULT_TYPE):
    query=' '.join(context.args).strip()
    if not query: return await update.message.reply_text('Misol: /song qo‘shiq nomi - ijrochi')
    folder=Path(tempfile.mkdtemp(prefix='song_',dir=ROOT)); msg=await update.message.reply_text('🔎 Qo‘shiq qidirilyapti…')
    try:
        path,title,url=await asyncio.to_thread(search_song,query,folder)
        if too_big(path): return await msg.edit_text('Audio hajmi limitdan katta.')
        await msg.delete()
        with path.open('rb') as f: await update.message.reply_audio(audio=f,title=title[:64],caption='🎵 '+esc(title),parse_mode='HTML')
        if url: await update.message.reply_text('Manba: '+url)
    except Exception as e: log.warning('Song search failed: %s',e); await msg.edit_text('❌ Qo‘shiq topilmadi yoki audio olishning iloji bo‘lmadi.')
    finally: shutil.rmtree(folder,ignore_errors=True)
async def audio_handler(update:Update,context:ContextTypes.DEFAULT_TYPE):
    msg=update.message; media=msg.voice or msg.audio; folder=Path(tempfile.mkdtemp(prefix='aud_',dir=ROOT))
    try:
        tg=await context.bot.get_file(media.file_id); ext='.ogg' if msg.voice else (Path(msg.audio.file_name or 'audio.mp3').suffix or '.mp3'); path=folder/('audio'+ext); await tg.download_to_drive(custom_path=str(path))
        with path.open('rb') as f: await msg.reply_document(document=f,filename='SUMMON-audio'+ext,caption='🎙 Audio fayling tayyor.')
    except Exception: await msg.reply_text('Audio faylni olishda xatolik bo‘ldi.')
    finally: shutil.rmtree(folder,ignore_errors=True)
async def callbacks(update:Update,context:ContextTypes.DEFAULT_TYPE):
    q=update.callback_query
    data=q.data or ''
    if data in ('help','rules','search','audio_help'):
        await q.answer()
        if data == 'search':
            return await q.message.reply_text('🟢 <b>QO‘SHIQ QIDIRISH</b>\n\nQuyidagi formatda yubor:\n<code>/song qo‘shiq nomi - ijrochi</code>\n\nMasalan: <code>/song Believer - Imagine Dragons</code>', parse_mode='HTML', reply_markup=menu())
        texts={
            'help':'🔴 <b>YORDAM</b>\nVideo havolasini yubor, keyin kerakli funksiyani tanla. Qo‘shiq uchun /song nomi - ijrochi yoz.',
            'rules':'🔴 <b>QOIDALAR</b>\nFaqat o‘zingga tegishli yoki yuklashga ruxsating bor kontentdan foydalan. Parol, cookie yoki tasdiqlash kodlarini yuborma.',
            'audio_help':'🔵 <b>AUDIO / OVOZ</b>\nVoice yoki audio fayl yubor — bot uni fayl sifatida qaytaradi.'
        }
        return await q.message.reply_text(texts[data], parse_mode='HTML', reply_markup=menu())
    if ':' not in data:
        await q.answer('Noma’lum buyruq', show_alert=True)
        return
    action,job=data.split(':',1)
    if action == 'cancel':
        context.bot_data.get('jobs',{}).pop(job,None)
        await q.answer('Bekor qilindi')
        return await q.message.reply_text('🔴 Amal bekor qilindi.', reply_markup=menu())
    src=context.bot_data.get('jobs',{}).get(job)
    await q.answer('Tayyorlanmoqda…')
    if not src or not Path(src).exists(): return await q.message.reply_text('Video fayl muddati tugagan. Havolani qayta yubor.')
    folder=Path(tempfile.mkdtemp(prefix='proc_',dir=ROOT))
    try:
        if action=='music':
            out=folder/'audio.mp3'; await asyncio.to_thread(subprocess.run,['ffmpeg','-y','-i',src,'-vn','-codec:a','libmp3lame','-q:a','2',str(out)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
            if too_big(out): return await q.message.reply_text('Audio hajmi limitdan katta.')
            with out.open('rb') as f: await q.message.reply_audio(audio=f,title='SUMMON MUSIC',caption='🟢 <b>SUMMON MUSIC</b> • Videodan ajratilgan audio',parse_mode='HTML')
        elif action=='round':
            out=folder/'round.mp4'; await asyncio.to_thread(round_video,Path(src),out)
            if too_big(out): return await q.message.reply_text('Dumaloq video hajmi limitdan katta.')
            with out.open('rb') as f: await q.message.reply_video_note(video=f,duration=60,length=640)
            await q.message.reply_text('🔵 <b>DUMALOQ VIDEO TAYYOR!</b>\nFon xiralashtirildi.', parse_mode='HTML', reply_markup=menu())
    except Exception as e: log.warning('Processing failed: %s',e); await q.message.reply_text('Faylni qayta ishlashda xatolik. FFmpeg o‘rnatilganini tekshir.')
    finally: shutil.rmtree(folder,ignore_errors=True)
async def health(request):
    return web.Response(text='SUMMON MEDIA is running', content_type='text/plain')

async def main():
    if not TOKEN:
        raise RuntimeError('BOT_TOKEN environment variable missing. Add BOT_TOKEN in Render Environment.')
    bot_app = Application.builder().token(TOKEN).build()
    bot_app.add_handler(CommandHandler('start', start))
    bot_app.add_handler(CommandHandler('help', help_cmd))
    bot_app.add_handler(CommandHandler('song', song_cmd))
    bot_app.add_handler(CallbackQueryHandler(callbacks))
    bot_app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, audio_handler))
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    # Render Web Service requires an HTTP server listening on 0.0.0.0:$PORT.
    web_app = web.Application()
    web_app.router.add_get('/', health)
    web_app.router.add_get('/health', health)
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.getenv('PORT', '10000')))
    await site.start()

    await bot_app.initialize()
    await bot_app.start()
    if bot_app.updater is None:
        raise RuntimeError('Telegram updater could not start')
    await bot_app.updater.start_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=False)
    log.info('SUMMON MEDIA bot and web health server started')
    try:
        await asyncio.Event().wait()
    finally:
        await bot_app.updater.stop()
        await bot_app.stop()
        await bot_app.shutdown()
        await runner.cleanup()

if __name__ == '__main__':
    asyncio.run(main())
