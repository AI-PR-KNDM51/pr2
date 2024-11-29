import telebot
import wikipedia

# Ініціалізація бота з використанням токену, отриманого від BotFather
bot = telebot.TeleBot('8137252780:AAGrFqlpmOXe00EyQjc3cs3D_Ub3Q29FNpE')

# Встановлення мови Вікіпедії на українську
wikipedia.set_lang("uk")

# Обробник команди /start
@bot.message_handler(commands=['start'])
def start(message):
    # Відправлення привітального повідомлення користувачу
    bot.send_message(message.chat.id, "Вітаю! Введіть запит для пошуку на Вікіпедії:")

# Обробник текстових повідомлень
@bot.message_handler(content_types=['text'])
def search_wikipedia(message):
    query = message.text.strip()  # Отримання тексту запиту від користувача та видалення зайвих пробілів
    try:
        # Отримання короткого резюме статті з Вікіпедії
        summary = wikipedia.summary(query, sentences=3)
        # Отримання сторінки Вікіпедії для запиту
        page = wikipedia.page(query)
        # Формування відповіді з назвою статті, резюме та посиланням на сторінку
        response = f"Назва статті: {page.title}\n\nОсновний текст статті: {summary}\n\nПосилання на статтю: {page.url}"
    except wikipedia.exceptions.DisambiguationError as e:
        # Обробка випадків неоднозначних запитів, коли існує кілька можливих статей
        response = f"Ваш запит неоднозначний. Можливо, ви мали на увазі:\n" + "\n".join(e.options[:5])
    except wikipedia.exceptions.PageError:
        # Обробка випадків, коли сторінку з таким запитом не знайдено
        response = "Статтю не знайдено. Спробуйте інший запит."
    # Відправлення відповіді користувачу
    bot.send_message(message.chat.id, response)

# Запуск бота в нескінченному циклі для прослуховування повідомлень
bot.polling(none_stop=True)