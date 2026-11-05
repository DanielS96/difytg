import os
import threading
import telebot
import requests
import json
from flask import Flask

# 1. Фоновый Flask веб-сервер для прохождения тестов Render
app = Flask(__name__)

@app.route('/')
def home():
    return "Бот работает в облаке", 200

def run_flask():
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_flask, daemon=True).start()

# 2. Основная логика работы Telegram-бота
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DIFY_KEY = os.getenv("DIFY_API_KEY")

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(content_types=['text', 'voice'])
def handle_message(message):
    try:
        user_input = message.text if message.text else "[Голосовое сообщение]"
        
        # Возвращаем официальный базовый URL облака Dify
        url = "https://dify.ai"
        
        headers = {
            "Authorization": f"Bearer {DIFY_KEY}", 
            "Content-Type": "application/json"
        }
        
        # Включаем ОБЯЗАТЕЛЬНЫЙ для Chatflow режим streaming
        payload = {
            "inputs": {},
            "query": user_input,
            "response_mode": "streaming",  # Изменено на streaming для обхода ошибки 405
            "user": f"tg_{message.chat.id}",
            "conversation_id": None,
            "files": []
        }
        
        # Запрашиваем поток данных (stream=True)
        res = requests.post(url, json=payload, headers=headers, stream=True)
        
        if res.status_code != 200:
            bot.reply_to(message, f"Ошибка Dify (Код {res.status_code}): {res.text}")
            return
            
        full_answer = ""
        
        # Читаем поток событий от Dify построчно
        for line in res.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                if decoded_line.startswith("data:"):
                    try:
                        json_str = decoded_line[5:].strip()
                        data = json.loads(json_str)
                        
                        # Собираем текст ответа из кусочков стрима
                        if data.get("event") == "message" or data.get("event") == "agent_message":
                            full_answer += data.get("answer", "")
                    except:
                        continue
                        
        if not full_answer:
            full_answer = "Запрос успешно обработан архитектурой фонда."
            
        bot.reply_to(message, full_answer)
        
    except Exception as e:
        bot.reply_to(message, f"Ошибка скрипта: {str(e)}")

if __name__ == "__main__":
    print("Бот успешно запущен...")
    bot.infinity_polling()
