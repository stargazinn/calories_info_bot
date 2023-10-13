import json
import requests
import os
import sys
sys.path.append(os.path.abspath('..')) # Переміщуємось на рівень вище
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nutrition_bot.settings')
import django
django.setup()
import emoji
from telegram import Update, bot, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler, ConversationHandler
from nutrition_bot_app.models import FoodQuery, UsersFoodQuery
from deep_translator import GoogleTranslator
from dotenv import load_dotenv


load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv('TOKEN')
print(TELEGRAM_BOT_TOKEN)


WAITING_FOR_FOOD_NAME, WAITING_FOR_FOOD_PRODUCTS = range(2)

WAITING_FOR_FOOD_NUMBER = 1


def start(update: Update, context: CallbackContext):
    update.message.reply_text(emoji.emojize("Привіт! Я бот для розрахунку калорійності їжі. "
                              "Просто напиши, що ти їси, і я розкажу, скільки там калорій!\n"
                              "Зверни увагу на кнопку 'Інфо' :neutral_face:"))
    reply_markup = main_menu()

    update.message.reply_text("Обери дію:", reply_markup=reply_markup)
    return WAITING_FOR_FOOD_NAME


def main_menu():
    keyboard = [
        [KeyboardButton('Калорійність продукту')],
        [KeyboardButton('Створити страву')],
        [KeyboardButton('Мої страви')],
        [KeyboardButton('Видалити страву')],
        [KeyboardButton('Відміна')],
        [KeyboardButton('Інфо')],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    return reply_markup


def get_calories(query):
    translated_query = GoogleTranslator(source='uk', target='english').translate(query)
    api_url = 'https://api.api-ninjas.com/v1/nutrition?query={}'.format(translated_query)
    response = requests.get(api_url,
                            headers={'X-Api-Key': 'qISGbWJ9OZTV9EjZwGz/Yw==7fDtHz92e655T987'})
    if response.status_code == requests.codes.ok:
        try:
            calories = response.json()[0]['calories']
            proteins, fats, carbohydrates = response.json()[0]['protein_g'], \
                response.json()[0]['fat_total_g'], \
                response.json()[0]['carbohydrates_total_g']
            return [calories, proteins, fats, carbohydrates]
        except (json.JSONDecodeError, KeyError):
            update.message.reply_text("Помилка: некоректний формат даних від сервера.")
    else:
        update.message.reply_text("Помилка під час отримання даних. Спробуйте пізніше.")


def echo(update: Update, context: CallbackContext):
    query = update.message.text
    if query == 'Калорійність продукту':
        update.message.reply_text('Введіть продукт:')
        return 1
    elif query == 'Мої страви':
        show_my_food(update, context)
        return ConversationHandler.END
    elif query == 'Інфо':
        info(update, context)
        return ConversationHandler.END
    elif query == 'Відміна':
        cancel(update, context)
        return ConversationHandler.END

    translated_query = GoogleTranslator(source='uk', target='english').translate(query)
    telegram_user_id = update.message.chat.username
    try:
        food_info = get_calories(translated_query)
    except (json.JSONDecodeError, KeyError):
        update.message.reply_text("Помилка: некоректний формат даних від сервера.")
    except (json.JSONDecodeError, IndexError):
        update.message.reply_text("Перепрошую, не вдалося знайти ваш продукт.")
    if food_info[0] is not None:
        update.message.reply_text(f"{query} містить приблизно {food_info[0]} калорій.\n"
                                  f"Білки: {food_info[1]}\n"
                                  f"Жири: {food_info[2]}\n"
                                  f"Вуглеводи: {food_info[3]}")
        food_query = FoodQuery(user_id=telegram_user_id,
                               query=query,
                               calories=food_info[0])
        food_query.save()
    else:
        update.message.reply_text("На жаль, не вдалося отримати інформацію про калорійність цієї страви.")


def start_create_food(update: Update, context: CallbackContext):
    keyboard = [
        [KeyboardButton("Зберегти страву")],
        [KeyboardButton("Відміна")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

    update.message.reply_text("Введіть назву страви:", reply_markup=reply_markup)
    return WAITING_FOR_FOOD_NAME


def save_food_name(update: Update, context: CallbackContext):
    user_input = update.message.text
    if user_input == 'Відміна':
        cancel(update, context)
        return ConversationHandler.END
    context.user_data['food_name'] = update.message.text
    context.user_data['food_products'] = []
    update.message.reply_text("Додайте продукти до страви. Введіть назву продукту:")
    return WAITING_FOR_FOOD_PRODUCTS


def add_food_product(update: Update, context: CallbackContext):
    user_input = update.message.text
    telegram_user_id = update.message.chat.username
    if user_input == 'Зберегти страву':
        food_name = context.user_data.get('food_name')
        food_products = context.user_data.get('food_products')
        print(food_name)
        print(food_products)
        if food_name and food_products:
            calories = 0
            for product in food_products:
                calories += get_calories(product)[0]
            calories = round(calories, 2)
            food_query = UsersFoodQuery(user_id=telegram_user_id,
                                   query=food_name,
                                   calories=calories)
            food_query.save()
            update.message.reply_text(
                f"Страву '{food_name}' збережено з наступними продуктами: {', '.join(food_products)}\n"
                f"Містить приблизно {calories} калорій")
        else:
            update.message.reply_text("Не вдалося зберегти страву. Перевірте, чи ви ввели назву та продукти.")
        context.user_data.clear()
        reply_markup = main_menu()
        update.message.reply_text("Обери дію:", reply_markup=reply_markup)
        return ConversationHandler.END
    elif user_input == 'Відміна':
        cancel(update, context)
        return ConversationHandler.END
    context.user_data['food_products'].append(user_input )

    update.message.reply_text(f"Продукт '{user_input }' додано до страви. Введіть наступний продукт, "
                              "або використайте кнопку 'Зберегти страву' для завершення додавання.")
    return WAITING_FOR_FOOD_PRODUCTS


def info(update: Update, context: CallbackContext):
    update.message.reply_text("Можеш писати продукти в наступних форматах:\n"
                              "1. 2 банани - розрахувати калорійність двох бананів.\n"
                              "2. 200г бананів - розрахувати калорійність 200г бананів.\n"
                              "3. Банан - розрахувати калорійність 100г бананів (значення за замовчуванням).\n"
                              "Введіть команду /cancel щоб відмінити поточну дію.\n"
                              "Також я розумію англійську!")
    reply_markup = main_menu()
    update.message.reply_text("Обери дію:", reply_markup=reply_markup)
    return ConversationHandler.END


def show_my_food(update: Update, context: CallbackContext):
    ufq_s = UsersFoodQuery.objects.filter(user_id=update.message.chat.username).values()
    food_text = ""
    if len(ufq_s) != 0:
        for _ in range(len(ufq_s)):
            food_text += f"{_+1}. Страва {ufq_s[_]['query']} приблизно містить {ufq_s[_]['calories']} калорій.\n"
        update.message.reply_text(food_text)
    else:
        update.message.reply_text("Ви ще не додали жодної страви.")
    main_menu()
    return ConversationHandler.END


def remove_food_choose(update: Update, context: CallbackContext):
    show_my_food(update, context)
    ufq_s = UsersFoodQuery.objects.filter(user_id=update.message.chat.username).values()
    if len(ufq_s) != 0:
        update.message.reply_text("Введіть номер страви для видалення:")
    else:
        update.message.reply_text("Ви ще не додали жодної страви.")
    return WAITING_FOR_FOOD_NUMBER


def remove_food(update: Update, context: CallbackContext):
    food_number = update.message.text
    if food_number == 'Відміна':
        cancel(update, context)
        return ConversationHandler.END
    ufq_s = UsersFoodQuery.objects.filter(user_id=update.message.chat.username).values()
    try:
        food_number = int(food_number)
    except:
        update.message.reply_text(f"Ви повинні ввести ціле число.")
    if food_number <= len(ufq_s):
        for _ in range(len(ufq_s)):
            if _ == (food_number - 1):
                UsersFoodQuery.objects.filter(query=ufq_s[_]['query'], user_id=update.message.chat.username).delete()
                update.message.reply_text(f"Страву '{ufq_s[_]['query']}' видалено.")
    else:
        update.message.reply_text(f"Ви повинні ввести ціле число з діапазону 1 - {len(ufq_s)}.")
    main_menu()
    return ConversationHandler.END


def cancel(update: Update, context: CallbackContext):
    update.message.reply_text("Скасовано.")
    context.user_data.clear()
    reply_markup = main_menu()
    update.message.reply_text("Обери дію:", reply_markup=reply_markup)
    return ConversationHandler.END


def main():
    updater = Updater(TELEGRAM_BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler("start", start))
    # dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))
    # ----------------------------------------------------------------
    conv_handler_create = ConversationHandler(
        entry_points=[MessageHandler(Filters.regex('^Створити страву$'), start_create_food)],
        states={
            WAITING_FOR_FOOD_NAME: [MessageHandler(Filters.text & ~Filters.command, save_food_name)],
            WAITING_FOR_FOOD_PRODUCTS: [MessageHandler(Filters.text & ~Filters.command, add_food_product)],
        },
        fallbacks=[
            CommandHandler('cancel', cancel)
        ]
    )
    conv_handler_echo = ConversationHandler(
        entry_points=[MessageHandler(Filters.regex('^Калорійність продукту$'), echo)],
        states={
            1: [MessageHandler(Filters.text & ~Filters.command, echo)]
        },
        fallbacks=[
            CommandHandler('cancel', cancel)
        ]
    )
    conv_handler_info = ConversationHandler(
        entry_points=[MessageHandler(Filters.regex('^Інфо$'), info)],
        states={
            1: [MessageHandler(Filters.text & ~Filters.command, info)]
        },
        fallbacks=[
            CommandHandler('cancel', cancel)
        ]
    )
    conv_handler_my_food = ConversationHandler(
        entry_points=[MessageHandler(Filters.regex('^Мої страви$'), show_my_food)],
        states={
            1: [MessageHandler(Filters.text & ~Filters.command, show_my_food)]
        },
        fallbacks=[
            CommandHandler('cancel', cancel)
        ]
    )
    conv_handler_remove_food = ConversationHandler(
        entry_points=[MessageHandler(Filters.regex('^Видалити страву$'), remove_food_choose)],
        states={
            WAITING_FOR_FOOD_NUMBER: [MessageHandler(Filters.text & ~Filters.command, remove_food)]
        },
        fallbacks=[
            CommandHandler('cancel', cancel)
        ]
    )
    conv_handler_cancel = ConversationHandler(
        entry_points=[MessageHandler(Filters.regex('^Відміна$'), cancel)],
        states={
            1: [MessageHandler(Filters.text & ~Filters.command, cancel)]
        },
        fallbacks=[
            CommandHandler('cancel', cancel)
        ]
    )


    dispatcher.add_handler(conv_handler_create)
    dispatcher.add_handler(conv_handler_echo)
    dispatcher.add_handler(conv_handler_info)
    dispatcher.add_handler(conv_handler_my_food)
    dispatcher.add_handler(conv_handler_remove_food)
    dispatcher.add_handler(conv_handler_cancel)

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
