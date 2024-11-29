import logging
import sqlite3
from sqlite3 import Error
import threading
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
    filters,
)

# Налаштування логування для відстеження подій та помилок
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# Визначення станів для розмови
SELL, RENT, HELP, SELL_DETAILS, RENT_DETAILS = range(5)


def create_connection(db_file):
    """
    Створює з'єднання з базою даних SQLite.
    :param db_file: Шлях до файлу бази даних.
    :return: Об'єкт з'єднання або None при помилці.
    """
    try:
        conn = sqlite3.connect(db_file, check_same_thread=False)
        return conn
    except Error as e:
        logger.error(f"Error connecting to database: {e}")
    return None


def init_db(conn):
    """
    Ініціалізує базу даних, створюючи необхідні таблиці та додаючи початкові дані.
    :param conn: Об'єкт з'єднання з базою даних.
    """
    try:
        cursor = conn.cursor()
        # Створення таблиці для нерухомості на продаж, якщо вона не існує
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS properties_for_sale (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                property_type TEXT,
                area TEXT,
                rooms TEXT,
                location TEXT,
                price TEXT
            )
        ''')
        # Видалення всіх записів у таблиці (можливо, для очищення бази при запуску)
        cursor.execute('DELETE FROM properties_for_sale')
        # Додавання початкових даних для продажу нерухомості
        cursor.execute('''
            INSERT INTO properties_for_sale (user_id, property_type, area, rooms, location, price)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (0, 'Квартира', '50м²', '2', 'вул. Шевченка', '$300'))
        cursor.execute('''
            INSERT INTO properties_for_sale (user_id, property_type, area, rooms, location, price)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (0, 'Будинок', '100м²', '4', 'вул. Лесі Українки', '$500'))
        conn.commit()
    except Error as e:
        logger.error(f"Error initializing database: {e}")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Обробник команди /start. Відправляє користувачу головне меню.
    :param update: Об'єкт оновлення.
    :param context: Контекст розмови.
    :return: Наступний стан розмови.
    """
    myProps = f"Мої пропозиції для продажу ({update.message.from_user.full_name})"
    # Створення клавіатури з варіантами дій
    reply_keyboard = [['Продати житло', 'Орендувати житло'],
                      [myProps, 'Інформація']]
    await update.message.reply_text(
        'Вітаємо! Оберіть опцію:',
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, resize_keyboard=True
        ),
    )
    return SELL


async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Обробник вибору користувача в головному меню.
    :param update: Об'єкт оновлення.
    :param context: Контекст розмови.
    :return: Наступний стан розмови.
    """
    choice = update.message.text
    if choice == 'Продати житло':
        context.user_data['action'] = 'sell'
        # Створення клавіатури з типами житла
        reply_keyboard = [['Квартира', 'Будинок', 'Гараж'],
                          ['Будка', 'Тент', 'Назад']]
        await update.message.reply_text(
            'Оберіть тип житла:',
            reply_markup=ReplyKeyboardMarkup(
                reply_keyboard, resize_keyboard=True
            ),
        )
        return SELL_DETAILS
    elif choice == 'Орендувати житло':
        context.user_data['action'] = 'rent'
        # Запит бажаної локації для оренди
        await update.message.reply_text(
            'Введіть бажану локацію або натисніть "Назад":',
            reply_markup=ReplyKeyboardMarkup(
                [['Назад']], resize_keyboard=True
            ),
        )
        return RENT_DETAILS
    elif choice == 'Мої пропозиції для продажу':
        # Відображення пропозицій користувача
        await my_properties(update, context)
        return SELL
    elif choice == 'Інформація':
        # Відображення інформації про бота
        await inform_command(update, context)
        return SELL
    elif choice == 'Назад':
        # Повернення до головного меню
        return await start(update, context)
    else:
        # Повідомлення про некоректний вибір
        await update.message.reply_text('Будь ласка, оберіть опцію з меню.')
        return SELL


async def sell_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Обробник деталей для продажу житла.
    :param update: Об'єкт оновлення.
    :param context: Контекст розмови.
    :return: Наступний стан розмови.
    """
    text = update.message.text
    if text == 'Назад':
        # Повернення до попереднього меню
        return await start(update, context)
    user_data = context.user_data
    db_conn = context.bot_data['db_connection']
    db_lock = context.bot_data['db_lock']
    user_id = update.message.from_user.id

    if 'property_type' not in user_data:
        # Збереження типу житла
        user_data['property_type'] = text
        await update.message.reply_text('Введіть площу або натисніть "Назад":',
                                        reply_markup=ReplyKeyboardMarkup(
                                            [['Назад']], resize_keyboard=True
                                        ),
                                        )
    elif 'area' not in user_data:
        if text == 'Назад':
            # Повернення до вибору типу житла
            del user_data['property_type']
            reply_keyboard = [['Квартира', 'Будинок', 'Гараж'],
                              ['Будка', 'Тент', 'Назад']]
            await update.message.reply_text(
                'Оберіть тип житла:',
                reply_markup=ReplyKeyboardMarkup(
                    reply_keyboard, resize_keyboard=True
                ),
            )
            return SELL_DETAILS
        # Збереження площі житла
        user_data['area'] = text
        await update.message.reply_text('Введіть кількість кімнат або натисніть "Назад":',
                                        reply_markup=ReplyKeyboardMarkup(
                                            [['Назад']], resize_keyboard=True
                                        ),
                                        )
    elif 'rooms' not in user_data:
        if text == 'Назад':
            # Повернення до введення площі
            del user_data['area']
            await update.message.reply_text('Введіть площу або натисніть "Назад":',
                                            reply_markup=ReplyKeyboardMarkup(
                                                [['Назад']], resize_keyboard=True
                                            ),
                                            )
            return SELL_DETAILS
        # Збереження кількості кімнат
        user_data['rooms'] = text
        await update.message.reply_text('Введіть локацію або натисніть "Назад":',
                                        reply_markup=ReplyKeyboardMarkup(
                                            [['Назад']], resize_keyboard=True
                                        ),
                                        )
    elif 'location' not in user_data:
        if text == 'Назад':
            # Повернення до введення кількості кімнат
            del user_data['rooms']
            await update.message.reply_text('Введіть кількість кімнат або натисніть "Назад":',
                                            reply_markup=ReplyKeyboardMarkup(
                                                [['Назад']], resize_keyboard=True
                                            ),
                                            )
            return SELL_DETAILS
        # Збереження локації
        user_data['location'] = text
        await update.message.reply_text('Введіть ціну або натисніть "Назад":',
                                        reply_markup=ReplyKeyboardMarkup(
                                            [['Назад']], resize_keyboard=True
                                        ),
                                        )
    elif 'price' not in user_data:
        if text == 'Назад':
            # Повернення до введення локації
            del user_data['location']
            await update.message.reply_text('Введіть локацію або натисніть "Назад":',
                                            reply_markup=ReplyKeyboardMarkup(
                                                [['Назад']], resize_keyboard=True
                                            ),
                                            )
            return SELL_DETAILS
        # Збереження ціни
        user_data['price'] = text

        try:
            # Збереження даних у базі даних з використанням блокування
            with db_lock:
                cursor = db_conn.cursor()
                cursor.execute('''
                    INSERT INTO properties_for_sale (user_id, property_type, area, rooms, location, price)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    user_id,
                    user_data.get('property_type'),
                    user_data.get('area'),
                    user_data.get('rooms'),
                    user_data.get('location'),
                    user_data.get('price')
                ))
                db_conn.commit()
                await update.message.reply_text('Дякуємо! Ваші дані збережено.')
        except Error as e:
            # Обробка помилки при збереженні даних
            logger.error(f"Error saving data: {e}")
            await update.message.reply_text('Сталася помилка при збереженні даних. Спробуйте пізніше.')

        # Очищення даних користувача та повернення до головного меню
        user_data.clear()
        return await start(update, context)
    return SELL_DETAILS


async def rent_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Обробник деталей для оренди житла.
    :param update: Об'єкт оновлення.
    :param context: Контекст розмови.
    :return: Наступний стан розмови.
    """
    text = update.message.text
    if text == 'Назад':
        # Повернення до головного меню
        return await start(update, context)
    user_data = context.user_data
    db_conn = context.bot_data['db_connection']
    db_lock = context.bot_data['db_lock']

    if 'location' not in user_data:
        # Збереження бажаної локації
        user_data['location'] = text
        # Створення клавіатури з вибором площі
        reply_keyboard = [['До 50м²', '50-100м²', '>100м²'], ['Назад']]
        await update.message.reply_text(
            'Оберіть бажану площу або натисніть "Назад":',
            reply_markup=ReplyKeyboardMarkup(
                reply_keyboard, resize_keyboard=True
            ),
        )
    elif 'area' not in user_data:
        if text == 'Назад':
            # Повернення до введення локації
            del user_data['location']
            await update.message.reply_text(
                'Введіть бажану локацію або натисніть "Назад":',
                reply_markup=ReplyKeyboardMarkup(
                    [['Назад']], resize_keyboard=True
                ),
            )
            return RENT_DETAILS
        # Збереження бажаної площі
        user_data['area'] = text
        await update.message.reply_text('Введіть кількість кімнат або натисніть "Назад":',
                                        reply_markup=ReplyKeyboardMarkup(
                                            [['Назад']], resize_keyboard=True
                                        ),
                                        )
    elif 'rooms' not in user_data:
        if text == 'Назад':
            # Повернення до вибору площі
            del user_data['area']
            reply_keyboard = [['До 50м²', '50-100м²', '>100м²'], ['Назад']]
            await update.message.reply_text(
                'Оберіть бажану площу або натисніть "Назад":',
                reply_markup=ReplyKeyboardMarkup(
                    reply_keyboard, resize_keyboard=True
                ),
            )
            return RENT_DETAILS
        # Збереження кількості кімнат
        user_data['rooms'] = text
        await update.message.reply_text('Введіть діапазон цін або натисніть "Назад":',
                                        reply_markup=ReplyKeyboardMarkup(
                                            [['Назад']], resize_keyboard=True
                                        ),
                                        )
    elif 'price_range' not in user_data:
        if text == 'Назад':
            # Повернення до введення кількості кімнат
            del user_data['rooms']
            await update.message.reply_text('Введіть кількість кімнат або натисніть "Назад":',
                                            reply_markup=ReplyKeyboardMarkup(
                                                [['Назад']], resize_keyboard=True
                                            ),
                                            )
            return RENT_DETAILS
        # Збереження діапазону цін
        user_data['price_range'] = text

        try:
            # Пошук нерухомості за введеними критеріями
            with db_lock:
                cursor = db_conn.cursor()
                query = '''
                    SELECT property_type, area, rooms, location, price
                    FROM properties_for_sale
                    WHERE location LIKE ? AND area LIKE ? AND rooms = ?
                '''
                cursor.execute(query, (
                    f'%{user_data.get("location")}%',
                    f'%{user_data.get("area")}%',
                    user_data.get('rooms')
                ))
                rows = cursor.fetchall()
                if rows:
                    # Формування повідомлення зі списком доступних варіантів
                    message = 'Ось список доступних варіантів:\n'
                    for row in rows:
                        message += f"{row[0]} в {row[3]}, {row[1]}, кімнат: {row[2]}, ціна: {row[4]}\n"
                    await update.message.reply_text(message)
                else:
                    # Повідомлення, якщо за запитом нічого не знайдено
                    await update.message.reply_text('Немає доступних варіантів за вашим запитом.')
        except Error as e:
            # Обробка помилки при отриманні даних
            logger.error(f"Error retrieving data: {e}")
            await update.message.reply_text('Сталася помилка при отриманні даних. Спробуйте пізніше.')

        # Очищення даних користувача та повернення до головного меню
        user_data.clear()
        return await start(update, context)
    return RENT_DETAILS


async def inform_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обробник команди /inform. Відправляє користувачу зображення.
    :param update: Об'єкт оновлення.
    :param context: Контекст розмови.
    """
    # Створення кнопки для отримання зображення
    button = InlineKeyboardButton('Натисніть, щоб отримати зображення', callback_data='get_image')
    reply_markup = InlineKeyboardMarkup([[button]])
    # Відправлення повідомлення з кнопкою
    await update.message.reply_text('Натисніть кнопку нижче, щоб отримати зображення.', reply_markup=reply_markup)


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обробник callback запитів від Inline кнопок.
    :param update: Об'єкт оновлення.
    :param context: Контекст розмови.
    """
    query = update.callback_query
    await query.answer()
    if query.data == 'get_image':
        # Відправлення зображення користувачу
        await query.message.reply_photo(photo='https://www.cambridgemaths.org/Images/The-trouble-with-graphs.jpg')
        await query.message.reply_text('Ось ваше зображення!')


async def my_properties(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Відображає пропозиції користувача для продажу.
    :param update: Об'єкт оновлення.
    :param context: Контекст розмови.
    """
    db_conn = context.bot_data['db_connection']
    db_lock = context.bot_data['db_lock']
    user_id = update.message.from_user.id

    try:
        # Отримання пропозицій користувача з бази даних
        with db_lock:
            cursor = db_conn.cursor()
            cursor.execute('''
                SELECT property_type, area, rooms, location, price
                FROM properties_for_sale
                WHERE user_id = ?
            ''', (user_id,))
            rows = cursor.fetchall()
            if rows:
                # Формування повідомлення зі списком пропозицій
                message = f"Ваші пропозиції для продажу, {update.message.from_user.full_name}" + ':\n'
                for row in rows:
                    message += f"{row[0]} в {row[3]}, {row[1]}, кімнат: {row[2]}, ціна: {row[4]}\n"
                await update.message.reply_text(message)
            else:
                # Повідомлення, якщо пропозицій немає
                await update.message.reply_text('У вас немає активних пропозицій для продажу.')
    except Error as e:
        # Обробка помилки при отриманні даних
        logger.error(f"Error retrieving data: {e}")
        await update.message.reply_text('Сталася помилка при отриманні даних. Спробуйте пізніше.')


def main() -> None:
    # Створення з'єднання з базою даних
    db_connection = create_connection('real_estate_bot.db')
    # Ініціалізація бази даних
    init_db(db_connection)

    # Створення блокування для безпечного доступу до бази даних з кількох потоків
    db_lock = threading.Lock()

    # Створення об'єкту додатку Telegram бота з використанням токену
    application = ApplicationBuilder().token('8137252780:AAGrFqlpmOXe00EyQjc3cs3D_Ub3Q29FNpE').build()

    # Збереження з'єднання та блокування у bot_data для доступу в обробниках
    application.bot_data['db_connection'] = db_connection
    application.bot_data['db_lock'] = db_lock

    # Визначення ConversationHandler для управління розмовами
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            SELL: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, main_menu
                )
            ],
            SELL_DETAILS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, sell_details),
            ],
            RENT_DETAILS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, rent_details),
            ],
        },
        fallbacks=[CommandHandler('inform', inform_command)],
    )

    # Додавання ConversationHandler до додатку
    application.add_handler(conv_handler)
    # Додавання обробника команди /inform
    application.add_handler(CommandHandler('inform', inform_command))
    # Додавання обробника callback запитів від Inline кнопок
    application.add_handler(CallbackQueryHandler(button_callback))

    # Запуск бота та початок опитування
    application.run_polling()


if __name__ == '__main__':
    main()