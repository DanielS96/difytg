import os
import threading
import telebot
import requests
from flask import Flask

# 1. Запуск Flask веб-сервера
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
        
        # Исправленный URL специально для Dify Chatflow
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
            "conversation_id": ""
        }
        
        res = requests.post(url, json=payload, headers=headers)
        
        if res.status_code != 200:
            bot.reply_to(message, f"Ошибка Dify (Код {res.status_code}): {res.text}")
            return
            
        response = res.json()
        
        # В Chatflow ответ может лежать в поле 'answer' или внутри событий стрима
        ai_text = response.get('answer', '')
        if not ai_text and 'event' in response:
            ai_text = response.get('text', 'Ошибка: пустой ответ')
            
        if not ai_text:
            ai_text = "Запрос обработан воркфлоу успешно."
            
        bot.reply_to(message, ai_text)
        
    except Exception as e:
        bot.reply_to(message, f"Ошибка скрипта: {str(e)}")

if __name__ == "__main__":
    print("Запуск бота...")
    bot.infinity_polling()
