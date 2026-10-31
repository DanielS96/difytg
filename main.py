import os
import telebot
import requests

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DIFY_KEY = os.getenv("DIFY_API_KEY")

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(content_types=['text', 'voice'])
def handle_message(message):
    try:
        # Для базового теста обрабатываем текст. Если это голос, Dify сам умеет
        # делать Speech-to-Text на своей стороне, если вы включили его в Features
        user_input = message.text if message.text else "[Голосовое сообщение]"
        
        url = "https://dify.ai"
        headers = {"Authorization": f"Bearer {DIFY_KEY}", "Content-Type": "application/json"}
        payload = {
            "inputs": {},
            "query": user_input,
            "response_mode": "blocking",
            "user": str(message.chat.id)
        }
        
        response = requests.post(url, json=payload, headers=headers).json()
        bot.reply_to(message, response.get('answer', 'Ошибка ответа ИИ'))
    except Exception as e:
        bot.reply_to(message, f"Ошибка: {str(e)}")

if __name__ == "__main__":
    bot.infinity_polling()
