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

def send_large_message(chat_id, text, reply_to_id):
    """Разбивает длинный текст на части по 4000 символов и отправляет в Telegram"""
    MAX_LENGTH = 4000
    if len(text) <= MAX_LENGTH:
        bot.send_message(chat_id, text, reply_to_message_id=reply_to_id)
    else:
        # Режем текст по кускам
        for i in range(0, len(text), MAX_LENGTH):
            part = text[i:i + MAX_LENGTH]
            bot.send_message(chat_id, part)

@bot.message_handler(content_types=['text', 'voice'])
def handle_message(message):
    try:
        user_input = message.text if message.text else "[Голосовое сообщение]"
        
        url = "https://api.dify.ai/v1/chat-messages"
        
        headers = {
            "Authorization": f"Bearer {DIFY_KEY}", 
            "Content-Type": "application/json"
        }
        
        payload = {
            "inputs": {},
            "query": user_input,
            "response_mode": "streaming",
            "user": f"tg_{message.chat.id}",
            "conversation_id": None,
            "files": []
        }
        
        res = requests.post(url, json=payload, headers=headers, stream=True)
        
        if res.status_code != 200:
            bot.reply_to(message, f"Ошибка Dify (Код {res.status_code}): {res.text}")
            return
            
        full_answer = ""
        
        for line in res.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                if decoded_line.startswith("data:"):
                    try:
                        json_str = decoded_line[5:].strip()
                        data = json.loads(json_str)
                        
                        if data.get("event") == "message" or data.get("event") == "agent_message":
                            full_answer += data.get("answer", "")
                    except:
                        continue
                        
        if not full_answer:
            full_answer = "Запрос успешно обработан архитектурой фонда."
            
        # Используем безопасную отправку длинных сообщений вместо bot.reply_to
        send_large_message(message.chat.id, full_answer, message.message_id)
        
    except Exception as e:
        bot.reply_to(message, f"Ошибка скрипта: {str(e)}")

if __name__ == "__main__":
    print("Бот успешно запущен...")
    bot.infinity_polling()
