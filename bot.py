import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import os
import requests
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

# === Фейковий сервер для стабільної роботи на Render ===
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
# =======================================================

TOKEN = os.getenv('BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)
user_requests = {}

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Привіт! Надішли посилання (YouTube, TikTok, Instagram тощо).")

@bot.message_handler(func=lambda message: message.text.startswith('http'))
def handle_url(message):
    url = message.text
    user_requests[message.chat.id] = url
    
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("🎬 Макс. якість відео", callback_data="video"),
        InlineKeyboardButton("🎵 Тільки MP3", callback_data="audio")
    )
    bot.reply_to(message, "Обери формат:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data in ['video', 'audio'])
def handle_download(call):
    chat_id = call.message.chat.id
    url = user_requests.get(chat_id)
    
    if not url:
        return bot.answer_callback_query(call.id, "Надішли посилання ще раз.")

    bot.edit_message_text("Оброблюю запит через анти-блок сервер... ⏳", chat_id, call.message.message_id)
    
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    
    payload = {
        "url": url,
        "vQuality": "max"
    }
    
    if call.data == 'audio':
        payload["isAudioOnly"] = True

    try:
        response = requests.post("https://api.cobalt.tools/api/json", headers=headers, json=payload)
        data = response.json()
        
        if "url" in data:
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("⬇️ Завантажити файл", url=data["url"]))
            bot.edit_message_text(f"✅ **Файл успішно згенеровано!**\n\nТисни на кнопку нижче, щоб миттєво зберегти відео/аудіо у найвищій якості без водяних знаків:", chat_id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
        else:
            bot.edit_message_text("❌ Сервіс не зміг обробити це посилання.", chat_id, call.message.message_id)
            
    except Exception:
        bot.edit_message_text("❌ Помилка з'єднання з API.", chat_id, call.message.message_id)

bot.polling(none_stop=True)
