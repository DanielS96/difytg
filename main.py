import os
import threading
import telebot
import requests
from flask import Flask

# 1. Запуск Flask веб-сервера для Render
app = Flask(__name__)

@app.route('/')
def home():
    return "Бот активен", 200

def run_flask():
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_flask, daemon=True).start()

# 2. Логика Telegram-бота
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DIFY_KEY = os.getenv("DIFY_API_KEY")

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(content_types=['text', 'voice'])
def handle_message(message):
    try:
        user_input = message.text if message.text else "[Голосовое сообщение]"
        
        # Точный базовый эндпоинт (работает для Chatflow при полной структуре payload)
        url = "https://dify.ai"
        headers = {
            "Authorization": f"Bearer {DIFY_KEY}", 
            "Content-Type": "application/json"
        }
        
        # Эталонный JSON-payload для Chatflow (со всеми обязательными для Nginx полями)
        payload = {
            "inputs": {},
            "query": user_input,
            "response_mode": "blocking",
            "user": f"tg_{message.chat.id}",
            "conversation_id": None,
            "files": []
        }
        
        res = requests.post(url, json=payload, headers=headers)
        
        # Если сервер вернул не 200, выводим понятную ошибку
        if res.status_code != 200:
            bot.reply_to(message, f"Ошибка Dify (Код {res.status_code}): {res.text}")
            return
            
        response = res.json()
        ai_text = response.get('answer', 'Ошибка: пустой ответ')
        bot.reply_to(message, ai_text)
        
    except Exception as e:
        bot.reply_to(message, f"Ошибка скрипта: {str(e)}")

if __name__ == "__main__":
    print("Запуск бота...")
    bot.infinity_polling()
