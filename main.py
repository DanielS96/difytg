import os
import threading
import time
import telebot
import requests
import json
from flask import Flask

# 1. Фоновый веб-сервер Flask для Render
app = Flask(__name__)

@app.route('/')
def home():
    return "Бот работает в облаке стабильно", 200

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
        headers = {"Authorization": f"Bearer {DIFY_KEY}"}

        # Обработка текста
        if message.content_type == 'text':
            user_input = message.text

        # Обработка голосового сообщения
        elif message.content_type == 'voice':
            file_info = bot.get_file(message.voice.file_id)
            file_data = bot.download_file(file_info.file_path)
            
            audio_url = "https://dify.ai"
            files = {'file': ('voice.ogg', file_data, 'audio/ogg')}
            data = {"user": f"tg_{message.chat.id}"}
            
            audio_res = requests.post(audio_url, data=data, files=files, headers=headers)
            if audio_res.status_code != 200:
                bot.reply_to(message, f"Ошибка аудио-модуля Dify (Код {audio_res.status_code}): {audio_res.text}")
                return
            user_input = audio_res.json().get('text', '')

        if not user_input:
            bot.reply_to(message, "Не удалось получить текст запроса.")
            return

        # Отправка в Dify Chatflow
        chat_url = "https://dify.ai"
        chat_headers = {
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
        
        res = requests.post(chat_url, json=payload, headers=chat_headers, stream=True)
        
        if res.status_code != 200:
            bot.reply_to(message, f"Ошибка Dify (Код {res.status_code}): {res.text}")
            return
            
        full_answer = ""
        
        # Построчно читаем стрим событий от Dify
        for line in res.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                if decoded_line.startswith("data:"):
                    try:
                        json_str = decoded_line[5:].strip()
                        data = json.loads(json_str)
                        
                        # Перехватываем ответ из ЛЮБЫХ возможных событий Chatflow
                        # (включая message, agent_message, text_chunk и финальные ноды)
                        if "answer" in data:
                            full_answer += data.get("answer", "")
                        elif "text" in data:
                            full_answer += data.get("text", "")
                        elif data.get("event") == "node_finished" and "outputs" in data:
                            # Экстренный перехват прямо из логов выполнения ноды ANSWER
                            outputs = data.get("data", {}).get("outputs", {})
                            if "text" in outputs:
                                full_answer += outputs.get("text", "")
                    except:
                        continue
                        
        # Если текст все еще пустой, выводим сырой лог последнего события для отладки
        if not full_answer:
            bot.reply_to(message, "Ошибка: Dify прислал пустой ответ в стриме. Проверьте, что в блоке ANSWER в Dify написан текст или вставлена переменная {{MODERATOR.text}}.")
            return
            
        bot.reply_to(message, full_answer)
        
    except Exception as e:
        bot.reply_to(message, f"Критический сбой скрипта: {str(e)}")

def start_polling():
    while True:
        try:
            bot.infinity_polling(timeout=20, long_polling_timeout=10)
        except Exception as e:
            time.sleep(5)

if __name__ == "__main__":
    start_polling()
