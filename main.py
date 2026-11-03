import os
import threading
import time
import telebot
import requests
import json
from flask import Flask

# 1. Запуск Flask веб-сервера для Render
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

        # ЕДИНСТВЕННЫЙ РАБОЧИЙ ЭНДПОИНТ ДЛЯ ПОТОКОВЫХ СХЕМ (ВОРКФЛОУ)
        chat_url = "https://dify.ai"
        
        # Передаем query внутрь переменной, как требует эндпоинт воркфлоу
        payload = {
            "inputs": {
                "query": user_input
            },
            "response_mode": "streaming",
            "user": f"tg_{message.chat.id}"
        }
        
        res = requests.post(chat_url, json=payload, headers=headers, stream=True)
        
        if res.status_code != 200:
            bot.reply_to(message, f"Ошибка Dify (Код {res.status_code}): {res.text}\nПроверьте API-ключ в настройках Render.")
            return
            
        full_answer = ""
        for line in res.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                if decoded_line.startswith("data:"):
                    try:
                        json_str = decoded_line[5:].strip()
                        data = json.loads(json_str)
                        
                        # Собираем ответ из событий воркфлоу
                        if data.get("event") == "text_chunk":
                            full_answer += data.get("data", {}).get("text", "")
                        elif data.get("event") == "workflow_finished":
                            # Экстренный перехват из финальных выходов
                            outputs = data.get("data", {}).get("outputs", {})
                            if "text" in outputs and not full_answer:
                                full_answer = outputs.get("text", "")
                    except:
                        continue
                        
        if not full_answer:
            bot.reply_to(message, "Воркфлоу отработал, но финальный текст пуст. Убедитесь, что в Dify на выходе из блока ANSWER (или в финальных параметрах Workflow) возвращается нужный текст.")
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
