import os, re, asyncio, logging, tempfile, shutil, subprocess
from pathlib import Path
from urllib.parse import urlparse
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from yt_dlp import YoutubeDL

TOKEN=os.getenv('BOT_TOKEN'); MAX_MB=int(os.getenv('MAX_FILE_MB','45')); ROOT=Path(os.getenv('WORKDIR','/tmp/summon_media')); ROOT.mkdir(parents=True,exist_ok=True)
logging.basicConfig(level=logging.INFO); log=logging.getLogger('summon-media'); URL_RE=re.compile(r'https?://\S+',re.I)

def menu(): return InlineKeyboardMarkup([[InlineKeyboardButton('🎵 Qo‘shiq qidirish',callback_data='search'),InlineKeyboardButton('🎙 Audio yuborish',callback_data='audio_help')],[InlineKeyboardButton('❔ Yordam',callback_data='help'),InlineKeyboardButton('📜 Qoidalar',callback_data='rules')]])
def media_menu(job): return InlineKeyboardMarkup([[InlineKeyboardButton('🟢 Musiqasini yuklash',callback_data='music:'+job)],[InlineKeyboardButton('🔵 Dumaloq video qilish',callback_data='round:'+job)]])
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
    await update.message.reply_text('💠 <b>SUMMON MEDIA</b>\n━━━━━━━━━━━━━━━━\n🎬 O‘zingga tegishli yoki yuklashga ruxsating bor video havolasini yubor.\n🎵 Qo‘shiq qidirish: /song nomi - ijrochi\nVideo tayyor bo‘lgach, musiqa yoki dumaloq video tugmasini tanla.',parse_mode='HTML',reply_markup=menu())
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
        await status.delete(); await update.message.reply_text(f'✨ <b>Video tayyor!</b>\n🎬 {esc(info.get("title") or path.stem)}\n\nTugmani tanla:',parse_mode='HTML',reply_markup=media_menu(job))
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
    q=update.callback_query; data=q.data or ''
    if data in ('help','rules','search','audio_help'):
        await q.answer(); texts={'help':'Video linkini yubor, so‘ng kerakli tugmani tanla. Qo‘shiq uchun /song nomi - ijrochi.','rules':'📜 Faqat o‘zingga tegishli yoki yuklashga ruxsating bor kontentdan foydalan. Parol, cookie yoki tasdiqlash kodini yuborma.','search':'🎵 Qo‘shiq qidirish: /song nomi - ijrochi','audio_help':'🎙 Ovoz yoki audio fayl yubor — bot uni qaytarib yuboradi.'}; return await q.message.reply_text(texts[data],reply_markup=menu())
    action,job=data.split(':',1); src=context.bot_data.get('jobs',{}).get(job); await q.answer('Tayyorlanmoqda…')
    if not src or not Path(src).exists(): return await q.message.reply_text('Video fayl muddati tugagan. Havolani qayta yubor.')
    folder=Path(tempfile.mkdtemp(prefix='proc_',dir=ROOT))
    try:
        if action=='music':
            out=folder/'audio.mp3'; await asyncio.to_thread(subprocess.run,['ffmpeg','-y','-i',src,'-vn','-codec:a','libmp3lame','-q:a','2',str(out)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
            if too_big(out): return await q.message.reply_text('Audio hajmi limitdan katta.')
            with out.open('rb') as f: await q.message.reply_audio(audio=f,title='SUMMON audio',caption='🟢 Videoning audiosi')
        elif action=='round':
            out=folder/'round.mp4'; await asyncio.to_thread(round_video,Path(src),out)
            if too_big(out): return await q.message.reply_text('Dumaloq video hajmi limitdan katta.')
            with out.open('rb') as f: await q.message.reply_video_note(video=f,duration=60,length=640)
            await q.message.reply_text('🔵 Tayyor! Fon xiralashtirildi.')
    except Exception as e: log.warning('Processing failed: %s',e); await q.message.reply_text('Faylni qayta ishlashda xatolik. FFmpeg o‘rnatilganini tekshir.')
    finally: shutil.rmtree(folder,ignore_errors=True)
def main():
    if not TOKEN: raise RuntimeError('BOT_TOKEN environment variable missing')
    app=Application.builder().token(TOKEN).build(); app.add_handler(CommandHandler('start',start)); app.add_handler(CommandHandler('help',help_cmd)); app.add_handler(CommandHandler('song',song_cmd)); app.add_handler(CallbackQueryHandler(callbacks)); app.add_handler(MessageHandler(filters.VOICE|filters.AUDIO,audio_handler)); app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,text_handler)); app.run_polling(allowed_updates=Update.ALL_TYPES)
if __name__=='__main__': main()
