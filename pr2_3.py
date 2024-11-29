import telebot
from currency_converter import CurrencyConverter
from telebot import types

# Ініціалізація бота з використанням токену, отриманого від BotFather
bot = telebot.TeleBot('8137252780:AAGrFqlpmOXe00EyQjc3cs3D_Ub3Q29FNpE')

# Ініціалізація об'єкту для конвертації валют
currency = CurrencyConverter()

# Глобальна змінна для зберігання суми, яку вводить користувач
amount = 0

# Обробник команди /start
@bot.message_handler(commands=['start'])
def start(message):
    # Відправлення повідомлення користувачу з проханням вказати суму
    bot.send_message(message.chat.id, 'Вкажіть суму:')
    # Реєстрація наступного кроку для обробки введеної суми
    bot.register_next_step_handler(message, summa)

# Функція для обробки введеної суми
def summa(message):
    global amount  # Використання глобальної змінної для зберігання суми
    try:
        # Спроба конвертувати введений текст у ціле число
        amount = int(message.text.strip())
    except ValueError:
        # Відправлення повідомлення про некоректний формат введення
        bot.send_message(message.chat.id, 'Невірний формат')
        # Повторна реєстрація наступного кроку для повторного введення суми
        bot.register_next_step_handler(message, summa)
        return

    if amount > 0:
        # Створення Inline клавіатури з кнопками для вибору валюти
        markup = types.InlineKeyboardMarkup(row_width=2)
        btn1 = types.InlineKeyboardButton('USD/EUR', callback_data='usd/eur')
        btn2 = types.InlineKeyboardButton('EUR/USD', callback_data='eur/usd')
        btn3 = types.InlineKeyboardButton('USD/GBP', callback_data='usd/gbp')
        btn4 = types.InlineKeyboardButton('Інше значення', callback_data='else')
        # Додавання кнопок до клавіатури
        markup.add(btn1, btn2, btn3, btn4)
        # Відправлення повідомлення з клавіатурою для вибору валюти
        bot.send_message(message.chat.id, 'Виберіть валюту:', reply_markup=markup)
    else:
        # Відправлення повідомлення про від'ємну суму та запит повторного введення
        bot.send_message(message.chat.id, 'Число від’ємне. Повторно вкажіть суму.')
        bot.register_next_step_handler(message, summa)

# Обробник callback запитів від Inline кнопок
@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    if call.data != 'else':
        # Розбиття callback_data на дві валюти
        values = call.data.upper().split('/')
        # Виконання конвертації валюти
        res = currency.convert(amount, values[0], values[1])
        # Відправлення результату конвертації користувачу
        bot.send_message(call.message.chat.id, f'Отримуєте: {round(res, 2)}. Вкажіть іншу суму.')
        # Реєстрація наступного кроку для введення нової суми
        bot.register_next_step_handler(call.message, summa)
    else:
        # Запит користувача вказати валюти через слеш для конвертації
        bot.send_message(call.message.chat.id, 'Вкажіть суму конвертації через слеш:')
        # Реєстрація наступного кроку для обробки введених валют
        bot.register_next_step_handler(call.message, my_currency)

# Функція для обробки користувацького вводу валют у форматі "FROM/TO"
def my_currency(message):
    try:
        # Розбиття введеного тексту на дві валюти
        values = message.text.upper().split('/')
        # Виконання конвертації валют
        res = currency.convert(amount, values[0], values[1])
        # Відправлення результату конвертації користувачу
        bot.send_message(message.chat.id, f'Отримуєте: {round(res, 2)}. Можете вказати іншу суму.')
        # Реєстрація наступного кроку для введення нової суми
        bot.register_next_step_handler(message, summa)
    except Exception:
        # Відправлення повідомлення про помилку та запит повторного введення валюти
        bot.send_message(message.chat.id, 'Невірне значення. Вкажіть суму повторно.')
        bot.register_next_step_handler(message, my_currency)

# Запуск бота в нескінченному циклі для прослуховування повідомлень
bot.polling(none_stop=True)