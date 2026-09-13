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
    bot.send_message(message.chat.id, "Привіт! Надішли мені посилання на відео.")

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
        return bot.answer_callback_query(call.id, "Посилання застаріло. Надішли його ще раз.")

    bot.edit_message_text("Шукаю посилання на файл... ⏳", chat_id, call.message.message_id)
    
    try:
        # Використовуємо стабільний відкритий API-ендпоінт для генерації
        api_url = f"https://apis.davidcyriltech.my.id/download?url={url}"
        response = requests.get(api_url, timeout=20)
        res_data = response.json()
        
        download_url = None
        if "result" in res_data:
            download_url = res_data["result"].get("dl_url") or res_data["result"].get("download_url")
        elif "download" in res_data:
            download_url = res_data["download"]

        if not download_url:
            # Запасний варіант через альтернативний шлюз
            alt_response = requests.get(f"https://tikwm.com/api/?url={url}", timeout=15).json()
            if "data" in alt_response and "play" in alt_response["data"]:
                download_url = alt_response["data"]["play"]

        if download_url:
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("⬇️ Завантажити файл", url=download_url))
            bot.edit_message_text("✅ **Готово!** Тисни на кнопку нижче, щоб завантажити файл:", chat_id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
        else:
            bot.edit_message_text("❌ Не вдалося отримати пряме посилання. Спробуй інше відео.", chat_id, call.message.message_id)
            
    except Exception:
        bot.edit_message_text("❌ Помилка з'єднання з архівом. Спробуй ще раз.", chat_id, call.message.message_id)

bot.polling(none_stop=True)
