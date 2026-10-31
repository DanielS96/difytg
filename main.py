import os
import threading
import telebot
import requests
from flask import Flask

# 1. Запуск фонового веб-сервера Flask для прохождения проверок Render
app = Flask(__name__)

@app.route('/')
def home():
    return "Бот работает", 200

def run_flask():
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_flask, daemon=True).start()

# 2. Логика работы Telegram-бота
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DIFY_KEY = os.getenv("DIFY_API_KEY")

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(content_types=['text', 'voice'])
def handle_message(message):
    try:
        user_input = message.text if message.text else "[Голосовое сообщение]"
        
        # Исправленный URL: добавлен обязательный префикс /api/ вместо /v1/
        url = "https://dify.ai"
        
        headers = {
            "Authorization": f"Bearer {DIFY_KEY}", 
            "Content-Type": "application/json"
        }
        
        payload = {
            "inputs": {},
            "query": user_input,
            "response_mode": "blocking",
            "user": f"tg_{message.chat.id}",
            "conversation_id": None,
            "files": []
        }
        
        res = requests.post(url, json=payload, headers=headers)
        
        if res.status_code != 200:
            bot.reply_to(message, f"Ошибка Dify (Код {res.status_code}): {res.text}")
            return
            
        response = res.json()
        ai_text = response.get('answer', 'Ошибка: сервер вернул пустой ответ.')
        bot.reply_to(message, ai_text)
        
    except Exception as e:
        bot.reply_to(message, f"Ошибка скрипта: {str(e)}")

if __name__ == "__main__":
    print("Бот успешно запущен...")
    bot.infinity_polling()
