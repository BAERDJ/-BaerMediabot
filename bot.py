import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import os
import requests
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

def run_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), DummyHandler)
    server.serve_forever()

threading.Thread(target=run_dummy_server, daemon=True).start()

TOKEN = os.getenv('BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)
user_requests = {}

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Привіт! Надішли мені посилання на відео (YouTube, TikTok, Instagram).")

@bot.message_handler(func=lambda message: message.text.startswith('http'))
def handle_url(message):
    url = message.text
    user_requests[message.chat.id] = url
    
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("🎬 Макс. якість відео", callback_data="video"),
        InlineKeyboardButton("🎵 Тільки MP3", callback_data="audio")
    )
    bot.reply_to(message, "Обери формат завантаження:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data in ['video', 'audio'])
def handle_download(call):
    chat_id = call.message.chat.id
    url = user_requests.get(chat_id)
    
    if not url:
        return bot.answer_callback_query(call.id, "Посилання застаріле. Надішли його ще раз.")

    bot.edit_message_text("Шукаю посилання на файл... ⏳", chat_id, call.message.message_id)
    
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
    }
    
    payload = {
        "url": url,
        "videoQuality": "max"
    }
    
    if call.data == 'audio':
        payload["downloadMode"] = "audio"
        payload["audioFormat"] = "mp3"

    try:
        # Використовуємо нове стабільне дзеркало Cobalt замість закритого сайту
        response = requests.post("https://co.wuk.sh/api/json", headers=headers, json=payload, timeout=15)
        data = response.json()
        
        download_url = data.get("url") or data.get("picker") and data["picker"][0].get("url")
        
        if not download_url and "tunnel" in data:
            download_url = data["tunnel"]

        if download_url:
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("⬇️ Завантажити файл", url=download_url))
            bot.edit_message_text("✅ **Готово!** Тисни на кнопку нижче, щоб завантажити файл у найвищій якості без водяних знаків:", chat_id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
        else:
            err_text = data.get('text', 'Невідома помилка')
            bot.edit_message_text(f"❌ Помилка: {err_text}", chat_id, call.message.message_id)
            
    except Exception as e:
        bot.edit_message_text("❌ Помилка з'єднання з новим сервером. Спробуй ще раз.", chat_id, call.message.message_id)

bot.polling(none_stop=True)
