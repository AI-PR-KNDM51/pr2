import requests
import json
import telebot
from telebot import types

# Ініціалізація бота з використанням токену, отриманого від BotFather
bot = telebot.TeleBot('8137252780:AAGrFqlpmOXe00EyQjc3cs3D_Ub3Q29FNpE')

# API ключ для доступу до OpenWeatherMap
API = 'f088cbb49c94b518e1128451d7c3e2d2'

# Обробник команди /start
@bot.message_handler(commands=['start'])
def start(message):
    # Створення клавіатури з кнопками міст
    markup = types.ReplyKeyboardMarkup(row_width=2)
    button1 = types.KeyboardButton('Київ')
    button2 = types.KeyboardButton('Львів')
    button3 = types.KeyboardButton('Одеса')
    button4 = types.KeyboardButton('Харків')
    # Додавання кнопок до клавіатури
    markup.add(button1, button2, button3, button4)
    # Відправлення повідомлення користувачу з клавіатурою
    bot.send_message(message.chat.id, 'Виберіть місто для отримання погоди:', reply_markup=markup)

# Обробник текстових повідомлень (міста)
@bot.message_handler(content_types=['text'])
def get_weather(message):
    # Отримання тексту повідомлення та видалення зайвих пробілів
    city = message.text.strip()
    # Виконання GET запиту до API OpenWeatherMap для отримання погоди в обраному місті
    res = requests.get(f'https://api.openweathermap.org/data/2.5/weather?q={city}&appid={API}&units=metric&lang=ua')

    if res.status_code == 200:
        # Перетворення відповіді у формат JSON
        data = res.json()
        # Отримання температури
        temp = data["main"]["temp"]
        # Отримання відчувається як
        feels_like = data["main"]["feels_like"]
        # Отримання опису погоди
        description = data["weather"][0]["description"]
        # Отримання швидкості вітру
        wind_speed = data["wind"]["speed"]
        # Отримання вологості
        humidity = data["main"]["humidity"]
        # Отримання тиску
        pressure = data["main"]["pressure"]

        # Створення повідомлення з інформацією про погоду
        weather_message = (
            f'Погода в {city}:\n'
            f'Температура: {temp}°C\n'
            f'Відчувається як: {feels_like}°C\n'
            f'Опис: {description.capitalize()}\n'
            f'Вологість: {humidity}%\n'
            f'Тиск: {pressure} hPa\n'
            f'Швидкість вітру: {wind_speed} м/с'
        )
        # Відправлення повідомлення користувачу
        bot.reply_to(message, weather_message)

        # Отримання іконки погоди
        icon = data["weather"][0]["icon"]
        # Формування URL для отримання зображення іконки
        image_url = f'http://openweathermap.org/img/wn/{icon}@2x.png'
        # Відправлення зображення користувачу
        bot.send_photo(message.chat.id, image_url)
    else:
        # Відправлення повідомлення про помилку, якщо місто не знайдено або сталася інша помилка
        bot.reply_to(message, 'Місто вказано невірно або сталася помилка під час отримання даних.')

# Запуск бота в нескінченному циклі для прослуховування повідомлень
bot.polling(none_stop=True)