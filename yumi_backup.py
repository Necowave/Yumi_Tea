import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ConversationHandler,
    MessageHandler, filters, PreCheckoutQueryHandler
)

# Состояния разговора
CHOOSE_LANGUAGE, MAIN_MENU, ORDER_CATEGORY, CHOOSE_FLAVOR, CHOOSE_TOPPINGS, CONFIRM_ORDER, ADD_LOCATION, PAYMENT, SETTINGS, CONTACT_INPUT = range(10)

# Инициализация базы данных
def init_db():
    with sqlite3.connect('bubble_tea_bot.db') as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users 
                     (user_id INTEGER PRIMARY KEY, language TEXT, loyalty_drinks INTEGER DEFAULT 0)''')
        c.execute('''CREATE TABLE IF NOT EXISTS orders 
                     (order_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, 
                      category TEXT, flavor TEXT, toppings TEXT, status TEXT, stars_paid INTEGER, is_free BOOLEAN, 
                      latitude REAL, longitude REAL)''')
        conn.commit()

# Тексты на двух языках
RU = {
    'welcome': 'Привет! Добро пожаловать в Yumi Tea! Выбери язык:',
    'main_menu': 'Привет! Я твой помощник в Yumi Tea. Что хочешь сделать?',
    'order': '🛒 Заказать',
    'view_menu': '📖 Посмотреть меню',
    'loyalty': '⭐ Программа лояльности',
    'contact': '📞 Связаться с нами',
    'settings': '⚙️ Настройки',
    'choose_category': 'Выбери категорию напитка:',
    'choose_flavor': 'Выбери вкус:',
    'choose_toppings': 'Выбери топпинг (один):',
    'confirm_order': 'Твой заказ: {order}. Цена: {price} Stars. Подтвердить?',
    'add_location': 'Отправь геопозицию для доставки или выбери позже:',
    'payment': 'Оплати заказ через Telegram Stars: {price} Stars',
    'order_confirmed': 'Спасибо за заказ в Yumi Tea! Твой номер заказа: #{order_id}',
    'menu': 'Меню Yumi Tea:\n- ☕ Классический молочный чай: Оригинальный, Таро, Матча\n- 🍹 Фруктовый чай: Манго, Клубника, Персик\n- 🥤 Особый чай: Коричневый сахар, Сырная пенка\nТоппинги: 🧋 Жемчуг тапиоки, 🍮 Желе, 💥 Лопающиеся боба\nВсе напитки — 50 Stars (средний размер)',
    'loyalty_status': 'Ты заказал {drinks} напитков. {remaining} до бесплатного!',
    'contact_prompt': 'Напиши свой вопрос, и мы ответим!',
    'send_location': 'Пожалуйста, отправь свою геопозицию.',
    'location_later': 'Не забудь добавить геопозицию позже!',
    'send_location_not_text': 'Пожалуйста, отправь свою геопозицию, а не текст.',
    'language_set': 'Язык установлен: {lang}',
    'order_cancelled': 'Заказ отменён',
    'order_error': 'Ошибка: данные заказа неполные',
    'order_not_found': 'Ошибка: заказ не найден',
    'db_error': 'Ошибка базы данных',
    'free_drink_used': 'Поздравляем! Ваш бесплатный напиток использован. Счётчик обнулён!',
    'message_sent': 'Сообщение отправлено!'
}

EN = {
    'welcome': 'Hello! Welcome to Yumi Tea! Choose your language:',
    'main_menu': 'Hi! I’m your assistant at Yumi Tea. What would you like to do?',
    'order': '🛒 Order',
    'view_menu': '📖 View Menu',
    'loyalty': '⭐ Loyalty Program',
    'contact': '📞 Contact Us',
    'settings': '⚙️ Settings',
    'choose_category': 'Choose a drink category:',
    'choose_flavor': 'Choose a flavor:',
    'choose_toppings': 'Choose one topping:',
    'confirm_order': 'Your order: {order}. Price: {price} Stars. Confirm?',
    'add_location': 'Send your location for delivery or choose later:',
    'payment': 'Pay for your order with Telegram Stars: {price} Stars',
    'order_confirmed': 'Thank you for your order at Yumi Tea! Your order number: #{order_id}',
    'menu': 'Yumi Tea Menu:\n- ☕ Classic Milk Tea: Original, Taro, Matcha\n- 🍹 Fruit Tea: Mango, Strawberry, Peach\n- 🥤 Special Tea: Brown Sugar, Cheese Foam\nToppings: 🧋 Tapioca Pearls, 🍮 Jelly, 💥 Popping Boba\nAll drinks — 50 Stars (medium size)',
    'loyalty_status': 'You’ve ordered {drinks} drinks. {remaining} until a free one!',
    'contact_prompt': 'Write your question, and we’ll reply!',
    'send_location': 'Please send your location.',
    'location_later': 'Don’t forget to add your location later!',
    'send_location_not_text': 'Please send your location, not text.',
    'language_set': 'Language set: {lang}',
    'order_cancelled': 'Order cancelled',
    'order_error': 'Error: incomplete order data',
    'order_not_found': 'Error: order not found',
    'db_error': 'Database error',
    'free_drink_used': 'Congratulations! Your free drink has been used. Counter reset!',
    'message_sent': 'Message sent!'
}

def get_text(user_id, key, **kwargs):
    user = get_user(user_id)
    lang = user[1] if user else 'en'
    text = RU.get(key, EN[key]) if lang == 'ru' else EN[key]
    return text.format(**kwargs)

def get_user(user_id):
    with sqlite3.connect('bubble_tea_bot.db') as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        return c.fetchone()

def update_user(user_id, language=None, loyalty_drinks=None):
    with sqlite3.connect('bubble_tea_bot.db') as conn:
        c = conn.cursor()
        if language:
            c.execute('UPDATE users SET language = ? WHERE user_id = ?', (language, user_id))
        if loyalty_drinks is not None:
            c.execute('UPDATE users SET loyalty_drinks = ? WHERE user_id = ?', (loyalty_drinks, user_id))
        conn.commit()

def create_order(user_id, category, flavor, toppings):
    user = get_user(user_id)
    loyalty_drinks = user[2] if user else 0
    is_free = (loyalty_drinks % 10 == 9)
    stars_paid = 0 if is_free else 50
    with sqlite3.connect('bubble_tea_bot.db') as conn:
        c = conn.cursor()
        c.execute('''INSERT INTO orders (user_id, category, flavor, toppings, status, stars_paid, is_free)
                     VALUES (?, ?, ?, ?, 'pending_location', ?, ?)''',
                  (user_id, category, flavor, toppings, stars_paid, is_free))
        order_id = c.lastrowid
        conn.commit()
    return order_id, stars_paid

# Хелперы клавиатур
def add_back_button(keyboard, back_text="🔙 Назад"):
    keyboard.append([InlineKeyboardButton(back_text, callback_data='back')])
    return keyboard

def get_main_menu_keyboard(lang):
    button_text = "🏠 Главное меню" if lang == 'ru' else "🏠 Main Menu"
    keyboard = [[KeyboardButton(button_text)]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Обработчики callback
async def back_to_main_menu(update: Update, context):
    query = update.callback_query
    await query.answer()
    print(f"Returning to MAIN_MENU for user {update.effective_user.id}")
    await show_main_menu(update, context)
    return MAIN_MENU

async def back_to_main_menu_text(update: Update, context):
    print(f"Back to main menu text triggered for user {update.effective_user.id}")
    await show_main_menu(update, context)
    return MAIN_MENU

async def settings(update: Update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    print(f"Settings triggered for user {user_id}")
    keyboard = [
        [InlineKeyboardButton("🇷🇺 Русский", callback_data='set_lang_ru')],
        [InlineKeyboardButton("🇬🇧 English", callback_data='set_lang_en')]
    ]
    add_back_button(keyboard)
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(get_text(user_id, 'welcome'), reply_markup=reply_markup)
    context.user_data['state'] = 'SETTINGS'
    return SETTINGS

async def set_language(update: Update, context):
    query = update.callback_query
    await query.answer()
    lang = query.data.split('_')[2]
    user_id = query.from_user.id
    update_user(user_id, language=lang)
    await query.edit_message_text(get_text(user_id, 'language_set', lang=lang))
    await show_main_menu(update, context)
    return MAIN_MENU

# Основные обработчики
async def start(update: Update, context):
    user_id = update.effective_user.id
    if get_user(user_id):
        await show_main_menu(update, context)
        return MAIN_MENU
    keyboard = [
        [InlineKeyboardButton("🇷🇺 Русский", callback_data='lang_ru')],
        [InlineKeyboardButton("🇬🇧 English", callback_data='lang_en')]
    ]
    add_back_button(keyboard)
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(get_text(user_id, 'welcome'), reply_markup=reply_markup)
    context.user_data['state'] = 'CHOOSE_LANGUAGE'
    return CHOOSE_LANGUAGE

async def choose_language(update: Update, context):
    query = update.callback_query
    await query.answer()
    lang = query.data.split('_')[1]
    user_id = query.from_user.id
    if get_user(user_id):
        update_user(user_id, language=lang)
    else:
        with sqlite3.connect('bubble_tea_bot.db') as conn:
            c = conn.cursor()
            c.execute('INSERT INTO users (user_id, language) VALUES (?, ?)', (user_id, lang))
            conn.commit()
    await query.edit_message_text(get_text(user_id, 'language_set', lang=lang))
    await show_main_menu(update, context)
    return MAIN_MENU

async def show_main_menu(update: Update, context):
    user_id = update.effective_user.id
    print(f"Showing main menu for user {user_id}")
    text = get_text(user_id, 'main_menu')
    keyboard = [
        [InlineKeyboardButton(get_text(user_id, 'order'), callback_data='order')],
        [InlineKeyboardButton(get_text(user_id, 'view_menu'), callback_data='view_menu')],
        [InlineKeyboardButton(get_text(user_id, 'loyalty'), callback_data='loyalty')],
        [InlineKeyboardButton(get_text(user_id, 'contact'), callback_data='contact')],
        [InlineKeyboardButton(get_text(user_id, 'settings'), callback_data='settings')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
        await context.bot.send_message(
            chat_id=user_id,
            text="Выбери действие" if get_user(user_id)[1] == 'ru' else "Choose an action",
            reply_markup=get_main_menu_keyboard(get_user(user_id)[1])
        )
    else:
        await update.message.reply_text(text, reply_markup=reply_markup)
        await update.message.reply_text(
            "Выбери действие" if get_user(user_id)[1] == 'ru' else "Choose an action",
            reply_markup=get_main_menu_keyboard(get_user(user_id)[1])
        )
    context.user_data['state'] = 'MAIN_MENU'
    return MAIN_MENU

async def start_order(update: Update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    print(f"Start order triggered for user {user_id}")
    context.user_data['order'] = {}
    text = get_text(user_id, 'choose_category')
    keyboard = [
        [InlineKeyboardButton("☕ Classic Milk Tea" if get_user(user_id)[1] == 'en' else "☕ Классический молочный чай", callback_data='cat_classic')],
        [InlineKeyboardButton("🍹 Fruit Tea" if get_user(user_id)[1] == 'en' else "🍹 Фруктовый чай", callback_data='cat_fruit')],
        [InlineKeyboardButton("🥤 Special Tea" if get_user(user_id)[1] == 'en' else "🥤 Особый чай", callback_data='cat_special')]
    ]
    add_back_button(keyboard)
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup)
    context.user_data['state'] = 'ORDER_CATEGORY'
    return ORDER_CATEGORY

async def choose_category(update: Update, context):
    query = update.callback_query
    await query.answer()
    category = query.data.split('_')[1]
    context.user_data['order']['category'] = category
    user_id = query.from_user.id
    lang = get_user(user_id)[1]
    if category == 'classic':
        flavors = [
            InlineKeyboardButton("🍵 Оригинальный" if lang == 'ru' else "🍵 Original", callback_data='flav_original'),
            InlineKeyboardButton("🥔 Таро" if lang == 'ru' else "🥔 Taro", callback_data='flav_taro'),
            InlineKeyboardButton("🍵 Матча" if lang == 'ru' else "🍵 Matcha", callback_data='flav_matcha')
        ]
    elif category == 'fruit':
        flavors = [
            InlineKeyboardButton("🥭 Манго" if lang == 'ru' else "🥭 Mango", callback_data='flav_mango'),
            InlineKeyboardButton("🍓 Клубника" if lang == 'ru' else "🍓 Strawberry", callback_data='flav_strawberry'),
            InlineKeyboardButton("🍑 Персик" if lang == 'ru' else "🍑 Peach", callback_data='flav_peach')
        ]
    else:  # special
        flavors = [
            InlineKeyboardButton("🍯 Коричневый сахар" if lang == 'ru' else "🍯 Brown Sugar", callback_data='flav_brown_sugar'),
            InlineKeyboardButton("🧀 Сырная пенка" if lang == 'ru' else "🧀 Cheese Foam", callback_data='flav_cheese_foam')
        ]
    keyboard = [flavors[i:i+2] for i in range(0, len(flavors), 2)]
    add_back_button(keyboard)
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(get_text(user_id, 'choose_flavor'), reply_markup=reply_markup)
    context.user_data['state'] = 'CHOOSE_FLAVOR'
    return CHOOSE_FLAVOR

async def choose_flavor(update: Update, context):
    query = update.callback_query
    await query.answer()
    flavor = "_".join(query.data.split('_')[1:])
    context.user_data['order']['flavor'] = flavor
    user_id = query.from_user.id
    lang = get_user(user_id)[1]
    keyboard = [
        [InlineKeyboardButton("🧋 Жемчуг тапиоки" if lang == 'ru' else "🧋 Tapioca Pearls", callback_data='top_pearls'),
         InlineKeyboardButton("🍮 Желе" if lang == 'ru' else "🍮 Jelly", callback_data='top_jelly')],
        [InlineKeyboardButton("💥 Лопающиеся боба" if lang == 'ru' else "💥 Popping Boba", callback_data='top_boba')]
    ]
    add_back_button(keyboard)
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(get_text(user_id, 'choose_toppings'), reply_markup=reply_markup)
    context.user_data['state'] = 'CHOOSE_TOPPINGS'
    return CHOOSE_TOPPINGS

async def choose_toppings(update: Update, context):
    query = update.callback_query
    await query.answer()
    topping = query.data.split('_')[1]
    context.user_data['order']['toppings'] = topping
    user_id = query.from_user.id
    order_desc = f"{context.user_data['order']['category']} - {context.user_data['order']['flavor']} с {topping}"
    user = get_user(user_id)
    price = 0 if (user[2] % 10 == 9) else 50
    keyboard = [
        [InlineKeyboardButton("✅ Подтвердить" if user[1] == 'ru' else "✅ Confirm", callback_data='confirm'),
         InlineKeyboardButton("❌ Отмена" if user[1] == 'ru' else "❌ Cancel", callback_data='cancel')]
    ]
    add_back_button(keyboard)
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(get_text(user_id, 'confirm_order', order=order_desc, price=price), reply_markup=reply_markup)
    context.user_data['state'] = 'CONFIRM_ORDER'
    return CONFIRM_ORDER

async def confirm_order(update: Update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if query.data == 'cancel':
        await query.edit_message_text(get_text(user_id, 'order_cancelled'))
        context.user_data.clear()
        return ConversationHandler.END

    order_data = context.user_data.get('order', {})
    missing_fields = [field for field in ['category', 'flavor', 'toppings'] if field not in order_data or not order_data[field]]
    
    if missing_fields:
        missing_text = "Отсутствуют данные: " + ", ".join(missing_fields) if get_user(user_id)[1] == 'ru' else "Missing data: " + ", ".join(missing_fields)
        await query.edit_message_text(f"{get_text(user_id, 'order_error')}\n{missing_text}")
        if 'category' not in order_data or not order_data['category']:
            return await start_order(update, context)
        elif 'flavor' not in order_data or not order_data['flavor']:
            return await choose_category(update, context)
        elif 'toppings' not in order_data or not order_data['toppings']:
            return await choose_flavor(update, context)
    
    try:
        order_id, price = create_order(user_id,
                                       order_data['category'],
                                       order_data['flavor'],
                                       order_data['toppings'])
        context.user_data['order_id'] = order_id
        context.user_data['price'] = price
        
        keyboard = [
            [InlineKeyboardButton("📍 Отправить сейчас" if get_user(user_id)[1] == 'ru' else "📍 Send Now", callback_data='loc_now'),
             InlineKeyboardButton("⏳ Добавить позже" if get_user(user_id)[1] == 'ru' else "⏳ Add Later", callback_data='loc_later')]
        ]
        add_back_button(keyboard)
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(get_text(user_id, 'add_location'), reply_markup=reply_markup)
        context.user_data['state'] = 'ADD_LOCATION'
        return ADD_LOCATION
    
    except Exception as e:
        await query.edit_message_text(f"{get_text(user_id, 'order_error')}: {str(e)}")
        return await start_order(update, context)

async def add_location(update: Update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if 'order_id' not in context.user_data:
        await query.edit_message_text(get_text(user_id, 'order_not_found'))
        return ConversationHandler.END
    order_id = context.user_data['order_id']
    price = context.user_data['price']
    if query.data == 'loc_now':
        location_button = KeyboardButton("📍 Отправить геопозицию" if get_user(user_id)[1] == 'ru' else "📍 Send Location", request_location=True)
        keyboard = [[location_button]]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        await query.message.reply_text(get_text(user_id, 'send_location'), reply_markup=reply_markup)
        return ADD_LOCATION
    await query.edit_message_text(get_text(user_id, 'location_later'))
    keyboard = [
        [InlineKeyboardButton("💳 Оплатить через Stars" if get_user(user_id)[1] == 'ru' else "💳 Pay with Stars", callback_data='pay_real')],
        [InlineKeyboardButton("🧪 Тестовая оплата" if get_user(user_id)[1] == 'ru' else "🧪 Test Payment", callback_data='pay_test')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text(
        get_text(user_id, 'payment', price=price),
        reply_markup=reply_markup
    )
    await query.message.reply_text(
        "Выбери действие" if get_user(user_id)[1] == 'ru' else "Choose an action",
        reply_markup=get_main_menu_keyboard(get_user(user_id)[1])
    )
    context.user_data['state'] = 'PAYMENT'
    return PAYMENT

async def handle_location(update: Update, context):
    user_id = update.effective_user.id
    location = update.message.location
    if 'order_id' not in context.user_data:
        await update.message.reply_text(get_text(user_id, 'order_not_found'))
        return ConversationHandler.END
    order_id = context.user_data['order_id']
    price = context.user_data['price']
    try:
        with sqlite3.connect('bubble_tea_bot.db') as conn:
            c = conn.cursor()
            c.execute('UPDATE orders SET latitude = ?, longitude = ?, status = ? WHERE order_id = ?',
                      (location.latitude, location.longitude, 'pending_payment', order_id))
            conn.commit()
        keyboard = [
            [InlineKeyboardButton("💳 Оплатить через Stars" if get_user(user_id)[1] == 'ru' else "💳 Pay with Stars", callback_data='pay_real')],
            [InlineKeyboardButton("🧪 Тестовая оплата" if get_user(user_id)[1] == 'ru' else "🧪 Test Payment", callback_data='pay_test')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            get_text(user_id, 'payment', price=price),
            reply_markup=reply_markup
        )
        await update.message.reply_text(
            "Выбери действие" if get_user(user_id)[1] == 'ru' else "Choose an action",
            reply_markup=get_main_menu_keyboard(get_user(user_id)[1])
        )
        context.user_data['state'] = 'PAYMENT'
        return PAYMENT
    except sqlite3.Error:
        await update.message.reply_text(get_text(user_id, 'db_error'))
        return ConversationHandler.END

async def handle_text_in_add_location(update: Update, context):
    user_id = update.effective_user.id
    await update.message.reply_text(get_text(user_id, 'send_location_not_text'))
    return ADD_LOCATION

async def pre_checkout(update: Update, context):
    await context.bot.answer_pre_checkout_query(update.pre_checkout_query.id, ok=True)
    return PAYMENT

async def test_payment(update: Update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    print(f"Test payment triggered for user {user_id}")
    if 'order_id' not in context.user_data:
        await query.edit_message_text(get_text(user_id, 'order_not_found'))
        return ConversationHandler.END
    await query.edit_message_text(
        "Тестовая оплата прошла успешно!" if get_user(user_id)[1] == 'ru' else "Test payment completed successfully!"
    )
    # Вызываем successful_payment напрямую
    await successful_payment(update, context)
    context.user_data['state'] = 'MAIN_MENU'
    return MAIN_MENU

async def real_payment(update: Update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    print(f"Real payment triggered for user {user_id}")
    if 'order_id' not in context.user_data:
        await query.edit_message_text(get_text(user_id, 'order_not_found'))
        return ConversationHandler.END
    order_id = context.user_data['order_id']
    price = context.user_data['price']
    await query.edit_message_text(get_text(user_id, 'payment', price=price))
    await context.bot.send_invoice(
        chat_id=user_id,
        title="Yumi Tea Order",
        description="Your bubble tea order",
        payload=f"order_{order_id}",
        provider_token="",
        currency="XTR",
        prices=[{"label": "Drink", "amount": price}]
    )
    context.user_data['state'] = 'PAYMENT'
    return PAYMENT

async def successful_payment(update: Update, context):
    user_id = update.effective_user.id
    print(f"Successful payment triggered for user {user_id}")
    if 'order_id' not in context.user_data:
        await update.effective_message.reply_text(get_text(user_id, 'order_not_found'))
        return ConversationHandler.END
    order_id = context.user_data['order_id']
    try:
        with sqlite3.connect('bubble_tea_bot.db') as conn:
            c = conn.cursor()
            c.execute('UPDATE orders SET status = ? WHERE order_id = ?', ('completed', order_id))
            user = get_user(user_id)
            if user[2] % 10 != 9:
                new_loyalty = user[2] + 1
                if new_loyalty % 10 == 9:
                    remaining = "Бесплатный напиток!" if user[1] == 'ru' else "Free drink!"
                else:
                    remaining = f"Осталось {10 - (new_loyalty % 10)}" if user[1] == 'ru' else f"{10 - (new_loyalty % 10)} left"
                c.execute('UPDATE users SET loyalty_drinks = ? WHERE user_id = ?', (new_loyalty, user_id))
                await update.effective_message.reply_text(get_text(user_id, 'loyalty_status', drinks=new_loyalty, remaining=remaining))
            else:
                c.execute('UPDATE users SET loyalty_drinks = ? WHERE user_id = ?', (0, user_id))
                await update.effective_message.reply_text(get_text(user_id, 'free_drink_used'))
            order = c.execute('SELECT latitude, longitude FROM orders WHERE order_id = ?', (order_id,)).fetchone()
            conn.commit()
        await update.effective_message.reply_text(get_text(user_id, 'order_confirmed', order_id=order_id))
        if order is None or order[0] is None or order[1] is None:
            await update.effective_message.reply_text(get_text(user_id, 'location_later'))
        # Очищаем данные заказа
        context.user_data.clear()
        # Переход в главное меню
        await show_main_menu(update, context)
        print(f"Returning to MAIN_MENU after successful payment for user {user_id}")
        context.user_data['state'] = 'MAIN_MENU'
        return MAIN_MENU
    except sqlite3.Error:
        await update.effective_message.reply_text(get_text(user_id, 'db_error'))
        return ConversationHandler.END

async def view_menu(update: Update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    print(f"View menu triggered for user {user_id}")
    keyboard = []
    add_back_button(keyboard)
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(get_text(user_id, 'menu'), reply_markup=reply_markup)
    context.user_data['state'] = 'MAIN_MENU'
    return MAIN_MENU

async def loyalty(update: Update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    print(f"Loyalty triggered for user {user_id}")
    user = get_user(user_id)
    drinks = user[2]
    if drinks % 10 == 9:
        remaining = "Бесплатный напиток!" if user[1] == 'ru' else "Free drink!"
    else:
        remaining = f"Осталось {10 - (drinks % 10)}" if user[1] == 'ru' else f"{10 - (drinks % 10)} left"
    keyboard = []
    add_back_button(keyboard)
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(get_text(user_id, 'loyalty_status', drinks=drinks, remaining=remaining), reply_markup=reply_markup)
    context.user_data['state'] = 'MAIN_MENU'
    return MAIN_MENU

async def contact(update: Update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    print(f"Contact triggered for user {user_id}")
    keyboard = []
    add_back_button(keyboard)
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(get_text(user_id, 'contact_prompt'), reply_markup=reply_markup)
    context.user_data['state'] = 'CONTACT_INPUT'
    return CONTACT_INPUT

async def forward_contact(update: Update, context):
    user_id = update.effective_user.id
    message = update.message.text
    await context.bot.send_message(chat_id='627749619', text=f"Сообщение от {user_id}: {message}")
    await update.message.reply_text(get_text(user_id, 'message_sent'))
    await show_main_menu(update, context)
    return MAIN_MENU

def main():
    init_db()
    application = Application.builder().token('7437991442:AAF104FtAQuMDoM28KnlKRE68X7eqKeNwX4').build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOOSE_LANGUAGE: [
                CallbackQueryHandler(choose_language, pattern='lang_'),
                CallbackQueryHandler(back_to_main_menu, pattern='back')
            ],
            MAIN_MENU: [
                CallbackQueryHandler(start_order, pattern='order'),
                CallbackQueryHandler(view_menu, pattern='view_menu'),
                CallbackQueryHandler(loyalty, pattern='loyalty'),
                CallbackQueryHandler(contact, pattern='contact'),
                CallbackQueryHandler(settings, pattern='settings'),
                MessageHandler(filters.Regex(r'^(🏠 Главное меню|🏠 Main Menu)$'), back_to_main_menu_text)
            ],
            ORDER_CATEGORY: [
                CallbackQueryHandler(choose_category, pattern='cat_'),
                CallbackQueryHandler(back_to_main_menu, pattern='back')
            ],
            CHOOSE_FLAVOR: [
                CallbackQueryHandler(choose_flavor, pattern='flav_'),
                CallbackQueryHandler(back_to_main_menu, pattern='back')
            ],
            CHOOSE_TOPPINGS: [
                CallbackQueryHandler(choose_toppings, pattern='top_'),
                CallbackQueryHandler(back_to_main_menu, pattern='back')
            ],
            CONFIRM_ORDER: [
                CallbackQueryHandler(confirm_order, pattern='confirm|cancel'),
                CallbackQueryHandler(back_to_main_menu, pattern='back')
            ],
            ADD_LOCATION: [
                CallbackQueryHandler(add_location, pattern='loc_'),
                MessageHandler(filters.LOCATION, handle_location),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_in_add_location),
                CallbackQueryHandler(back_to_main_menu, pattern='back')
            ],
            PAYMENT: [
                CallbackQueryHandler(real_payment, pattern='pay_real'),
                CallbackQueryHandler(test_payment, pattern='pay_test'),
                MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment),
                CallbackQueryHandler(back_to_main_menu, pattern='back')
            ],
            SETTINGS: [
                CallbackQueryHandler(set_language, pattern='set_lang_'),
                CallbackQueryHandler(back_to_main_menu, pattern='back')
            ],
            CONTACT_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, forward_contact),
                CallbackQueryHandler(back_to_main_menu, pattern='back')
            ]
        },
        fallbacks=[MessageHandler(filters.TEXT & ~filters.COMMAND, forward_contact)]
    )

    application.add_handler(conv_handler)
    application.add_handler(MessageHandler(filters.Regex(r'^(🏠 Главное меню|🏠 Main Menu)$'), back_to_main_menu_text))
    application.add_handler(PreCheckoutQueryHandler(pre_checkout))
    application.run_polling()

if __name__ == '__main__':
    main()