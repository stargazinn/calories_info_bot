import json
import requests
import os
import sys
sys.path.append(os.path.abspath('..')) # Переміщуємось на рівень вище
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nutrition_bot.settings')
import django
django.setup()
from telegram import Update, bot, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from nutrition_bot_app.models import FoodQuery
from deep_translator import GoogleTranslator



TELEGRAM_BOT_TOKEN = '6191972563:AAGrQvoK15ch3jdIKteKbDzWbgIuskHEfak'

def start(update: Update, context: CallbackContext):
    update.message.reply_text("Привіт! Я бот для розрахунку калорійності їжі. "
                              "Просто напиши, що ти їси, і я розкажу, скільки там калорій!")

def echo(update: Update, context: CallbackContext):
    query = update.message.text
    translated_query = GoogleTranslator(source='uk', target='english').translate(query)
    telegram_user_id = update.message.chat.username
    api_url = 'https://api.api-ninjas.com/v1/nutrition?query={}'.format(translated_query)
    response = requests.get(api_url,
                            headers={'X-Api-Key': 'qISGbWJ9OZTV9EjZwGz/Yw==7fDtHz92e655T987'})
    if response.status_code == requests.codes.ok:
        try:
            calories = response.json()[0]['calories']
            if calories is not None:
                update.message.reply_text(f"{query} містить приблизно {calories} калорій.")
                food_query = FoodQuery(user_id=telegram_user_id,
                                       query=query,
                                       calories=calories)
                food_query.save()
            else:
                update.message.reply_text("На жаль, не вдалося отримати інформацію про калорійність цієї страви.")
        except (json.JSONDecodeError, KeyError):
            update.message.reply_text("Помилка: некоректний формат даних від сервера.")
    else:
        update.message.reply_text("Помилка під час отримання даних. Спробуйте пізніше.")

def create_a_dish(update: Update, context: CallbackContext):pass

def main():
    buttons = [KeyboardButton('Створити страву'), KeyboardButton('Додати страву до обраного')]
    updater = Updater(TELEGRAM_BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
