import os
import threading
import time
import telebot
import requests
import json
from flask import Flask

# 1. Запуск Flask веб-сервера для Render (чтобы статус горел Live)
app = Flask(__name__)

@app.route('/')
def home():
    return "Сервер совещаний фонда активен", 200

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
        user_input = ""
        headers = {
            "Authorization": f"Bearer {DIFY_KEY}",
            "Content-Type": "application/json"
        }

        # ЕСЛИ ПРИШЕЛ ТЕКСТ:
        if message.content_type == 'text':
            user_input = message.text

        # ЕСЛИ ПРИШЛО ГОЛОСОВОЕ СООБЩЕНИЕ:
        elif message.content_type == 'voice':
            file_info = bot.get_file(message.voice.file_id)
            file_data = bot.download_file(file_info.file_path)
            
            # Переводим аудио в текст через аудио-эндпоинт Dify
            audio_url = "https://dify.ai"
            audio_headers = {"Authorization": f"Bearer {DIFY_KEY}"}
            files = {'file': ('voice.ogg', file_data, 'audio/ogg')}
            data = {"user": f"tg_{message.chat.id}"}
            
            audio_res = requests.post(audio_url, data=data, files=files, headers=audio_headers)
            if audio_res.status_code != 200:
                bot.reply_to(message, f"Ошибка распознавания речи (Код {audio_res.status_code}): {audio_res.text}")
                return
            user_input = audio_res.json().get('text', '')

        if not user_input:
            bot.reply_to(message, "Не удалось распознать текст запроса.")
            return

        # ИСПРАВЛЕННЫЙ URL И PAYLOAD ДЛЯ MULTI-AGENT CHATFLOW (Обход ошибки 405)
        chat_url = "https://dify.ai"
        
        payload = {
            "inputs": {},
            "query": user_input,
            "response_mode": "streaming",
            "user": f"tg_{message.chat.id}",
            "conversation_id": None,
            "files": []
        }
        
        res = requests.post(chat_url, json=payload, headers=headers, stream=True)
        
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
                        
                        # Собираем текстовые куски из потока мультиагентного Chatflow
                        if data.get("event") in ["message", "agent_message", "text_chunk"]:
                            full_answer += data.get("answer", "") or data.get("text", "")
                    except:
                        continue
                        
        if not full_answer:
            bot.reply_to(message, "Ошибка: ответ пуст. Убедитесь, что в Dify в блоке ANSWER вставлена переменная {{MODERATOR.text}}.")
            return
            
        bot.reply_to(message, full_answer)
        
    except Exception as e:
        bot.reply_to(message, f"Ошибка скрипта: {str(e)}")

def start_polling():
    while True:
        try:
            bot.infinity_polling(timeout=20, long_polling_timeout=10)
        except Exception as e:
            time.sleep(5)

if __name__ == "__main__":
    print("Бот успешно запущен...")
    start_polling()
