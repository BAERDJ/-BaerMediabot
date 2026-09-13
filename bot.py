import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import yt_dlp
import os
import glob
import time
import requests

TOKEN = os.getenv('BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)
user_requests = {}

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Привіт! Надішли мені посилання на відео.")

@bot.message_handler(func=lambda message: message.text.startswith('http'))
def handle_url(message):
    url = message.text
    msg = bot.send_message(message.chat.id, "Шукаю інформацію... ⏳")
    
    ydl_opts = {'quiet': True, 'noplaylist': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'Невідоме відео')
            
            user_requests[message.chat.id] = {'url': url, 'title': title}
            
            markup = InlineKeyboardMarkup()
            markup.add(
                InlineKeyboardButton("🎬 Макс. якість", callback_data="dl_video"),
                InlineKeyboardButton("🎵 Тільки MP3", callback_data="dl_audio")
            )
            bot.edit_message_text(f"🎬 **{title}**\n\nОбери формат:", chat_id=message.chat.id, message_id=msg.message_id, reply_markup=markup, parse_mode="Markdown")
    except Exception:
        bot.edit_message_text("❌ Помилка. Перевір посилання.", chat_id=message.chat.id, message_id=msg.message_id)

@bot.callback_query_handler(func=lambda call: call.data in ['dl_video', 'dl_audio'])
def handle_download(call):
    chat_id = call.message.chat.id
    req = user_requests.get(chat_id)
    if not req: return bot.answer_callback_query(call.id, "Надішли посилання ще раз.")

    url = req['url']
    choice = call.data
    unique_id = int(time.time())
    bot.edit_message_text("Завантажую... ⏳", chat_id=chat_id, message_id=call.message.message_id)
    
    ydl_opts = {'outtmpl': f'{chat_id}_{unique_id}_%(title)s.%(ext)s', 'noplaylist': True, 'quiet': True}

    if choice == 'dl_video':
        ydl_opts['format'] = 'bestvideo+bestaudio/best'
        ydl_opts['merge_output_format'] = 'mp4'
    else:
        ydl_opts['format'] = 'bestaudio/best'
        ydl_opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '320'}]

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            files = glob.glob(f'{chat_id}_{unique_id}_*.*')
            
            if files:
                file_to_send = files[0]
                if os.path.getsize(file_to_send) / (1024 * 1024) > 48:
                    bot.edit_message_text("Вага > 50 МБ. Створюю хмарне посилання... ☁️", chat_id=chat_id, message_id=call.message.message_id)
                    try:
                        with open(file_to_send, 'rb') as f:
                            resp = requests.post('https://file.io', files={'file': f}).json()
                        bot.edit_message_text(f"✅ **Файл завеликий для Telegram!**\n\nТримай посилання: {resp.get('link')}\n*(Діє на 1 скачування)*", chat_id=chat_id, message_id=call.message.message_id, parse_mode="Markdown")
                    except Exception:
                        bot.edit_message_text("❌ Помилка завантаження у хмару.", chat_id=chat_id, message_id=call.message.message_id)
                else:
                    bot.edit_message_text("Відправляю у чат 🚀", chat_id=chat_id, message_id=call.message.message_id)
                    with open(file_to_send, 'rb') as f:
                        bot.send_video(chat_id, f) if choice == 'dl_video' else bot.send_audio(chat_id, f)
                    bot.delete_message(chat_id=chat_id, message_id=call.message.message_id)
                
                if os.path.exists(file_to_send): os.remove(file_to_send)
    except Exception:
        bot.edit_message_text("❌ Помилка завантаження.", chat_id=chat_id, message_id=call.message.message_id)

bot.polling(none_stop=True)
