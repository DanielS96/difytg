import os
import telebot
import requests

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DIFY_KEY = os.getenv("DIFY_API_KEY")

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(content_types=['text', 'voice'])
def handle_message(message):
    try:
        # Обрабатываем текст или голосовой ввод
        user_input = message.text if message.text else "[Голосовое сообщение]"
        
        url = "https://dify.ai"
        headers = {
            "Authorization": f"Bearer {DIFY_KEY}", 
            "Content-Type": "application/json"
        }
        
        # Жестко задаем структуру для Chatflow
        payload = {
            "inputs": {},
            "query": user_input,
            "response_mode": "blocking",
            "user": f"tg_{message.chat.id}",
            "conversation_id": ""
        }
        
        # Делаем запрос к Dify
        res = requests.post(url, json=payload, headers=headers)
        
        # Если Dify ответил не JSON, а ошибкой — выводим её текст
        if res.status_code != 200:
            bot.reply_to(message, f"Ошибка Dify (Код {res.status_code}): {res.text}")
            return
            
        response = res.json()
        ai_text = response.get('answer', 'Ошибка: нет текста ответа')
        
        # Выводим текстовый ответ в Telegram
        bot.reply_to(message, ai_text)
        
    except Exception as e:
        bot.reply_to(message, f"Ошибка скрипта: {str(e)}")

if __name__ == "__main__":
    bot.infinity_polling()
