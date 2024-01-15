import os
import sys
from aiogram import Dispatcher, types
import keyboards
import database
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.utils.callback_data import CallbackData
import aiohttp
import random
import logging
import json


logging.basicConfig(level=logging.INFO)

class ReplenishBalanceStates(StatesGroup):
    choose_method = State()  
    enter_amount = State()  
    payment_method = None  

async def update_crypto_rates():
    global btc_price, ltc_price
    url = 'https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,litecoin&vs_currencies=rub'
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()
            btc_price = data['bitcoin']['rub']
            ltc_price = data['litecoin']['rub']

async def periodic_crypto_update():
    while True:
        await update_crypto_rates()
        await asyncio.sleep(900)  

btc_price = 0
ltc_price = 0

async def register_handlers(dp: Dispatcher, bot_token):
    @dp.message_handler(commands=['start'])
    async def send_welcome(message: types.Message):
        user_id = message.from_user.id
        if not database.check_user_exists(user_id, bot_token):
            database.add_user(user_id, bot_token)
            await message.answer("Привет! Салам! Шалом! На связи DOC. У нас ты получишь именно то, что так искал!🦸 Давай быстрее заказывай!", reply_markup=keyboards.main_keyboard())
            
            await show_cities(message)
        else:
            await message.answer("И снова здравствуй! 👋 Соскучился по нам? Мы тоже 😅 Бегом заказывай. Товар уже тебя заждался 😜", reply_markup=keyboards.main_keyboard())
    @dp.message_handler(lambda message: message.text == "Выбор категории")
    async def show_cities(message: types.Message):
        cities = database.get_cities()
        markup = InlineKeyboardMarkup(row_width=1)
    
        for city in cities:
            city_button = InlineKeyboardButton(city[1], callback_data=f"city_{city[0]}")
            markup.insert(city_button)
    
        await message.answer("Теперь выбери город, в котором будешь делать заказ", reply_markup=markup)
    @dp.message_handler(lambda message: message.text == "Сменить город/район")
    async def show_cities(message: types.Message):
        cities = database.get_cities()
        markup = InlineKeyboardMarkup(row_width=1)
    
        for city in cities:
            city_button = InlineKeyboardButton(city[1], callback_data=f"city_{city[0]}")
            markup.insert(city_button)
    
        await message.answer("Теперь выбери город, в котором будешь делать заказ", reply_markup=markup)
    @dp.callback_query_handler(lambda c: c.data.startswith('city_'))
    async def show_categories(callback_query: types.CallbackQuery):
        city_id = int(callback_query.data.split('_')[1])
        city_name = database.get_city_name(city_id)
        categories = database.get_categories_by_city(city_id)
        markup = InlineKeyboardMarkup(row_width=1)
    
        for category in categories:
            category_button = InlineKeyboardButton(category[1], callback_data=f"category_{category[0]}")
            markup.insert(category_button)
    
        await callback_query.message.edit_text(f"Выбирай категорию товара, который тебя прямо сейчас хочется!👇", reply_markup=markup)
    @dp.callback_query_handler(lambda c: c.data.startswith('category_'))
    async def show_products(callback_query: types.CallbackQuery):
        category_id = int(callback_query.data.split('_')[1])
        products = database.get_products_by_category(category_id)
    
        
        await callback_query.message.delete()
    
        if not products:
            
            await callback_query.message.answer("В данной категории товаров пока нет.")
            return
    
        for product in products:
            product_details_list = database.get_product_details(product[0])
            if not product_details_list:
                continue  
    
            
            product_text = f"<b>{product[1]}</b>\n"
            description = ""
            for details in product_details_list:
                if not description:
                    description = details["description"] if details["description"] else "Описание отсутствует"
                price = int(details["price"]) if details["price"] else "Цена не указана"
                weight = details["weight"]
                product_text += f"✅ {weight}гр — {price}₽\n"
    
            product_text += f"\n<b>Описание:</b>\n{description}"
    
            markup = InlineKeyboardMarkup(row_width=1)
            markup.add(InlineKeyboardButton("Выбрать", callback_data=f"select_{product[0]}"))
    
            
            await callback_query.message.answer(text=product_text, parse_mode='HTML', reply_markup=markup)
    @dp.callback_query_handler(lambda c: c.data.startswith('select_'))
    async def select_product(callback_query: types.CallbackQuery):
        product_id = int(callback_query.data.split('_')[1])
        product_details_list = database.get_product_details(product_id)
        
        if not product_details_list:
            await callback_query.answer("Информация о данном товаре отсутствует.")
            return
    
        
        markup = InlineKeyboardMarkup()
        for details in product_details_list:
            weight = details["weight"]
            price = details["price"]
            button_text = f"{weight}гр — {price}₽"
            markup.add(InlineKeyboardButton(button_text, callback_data=f"buy_{product_id}_{weight}"))
    
        await callback_query.message.edit_reply_markup(reply_markup=markup)
        await callback_query.answer()
    @dp.callback_query_handler(lambda c: c.data.startswith('buy_'))
    async def select_district(callback_query: types.CallbackQuery):
        _, product_id, weight = callback_query.data.split('_')
        product_details_list = database.get_product_details_by_weight(product_id, weight)
    
        if not product_details_list:
            await callback_query.answer("Информация о данном товаре отсутствует.")
            return
        
        
        details = product_details_list[0]
        product_price = details["price"]
    
        
        districts = set(details["districts"].split(',')) if details["districts"] else set()
    
        message_text = f"Вы выбрали {weight}гр\nСтоимость: {product_price}₽\n\nТеперь выбери район, в котором будешь делать заказ:"
    
        if districts:
            
            markup = InlineKeyboardMarkup()
            for district in districts:
                markup.add(InlineKeyboardButton(district, callback_data=f"district_{product_id}_{weight}_{district}"))
            await callback_query.message.edit_text(message_text, reply_markup=markup)
        else:
            
            await choose_product_payment_method(callback_query)
    @dp.callback_query_handler(lambda c: c.data.startswith('district_'))
    async def choose_product_payment_method(callback_query: types.CallbackQuery, state: FSMContext):
        _, product_id, weight, district = callback_query.data.split('_')
        product_price = database.get_product_price(product_id, float(weight))
    
        
        await ReplenishBalanceStates.choose_method.set()
    
        
        await state.update_data(product_id=product_id, weight=weight, product_price=product_price)
    
        
        inline_kb = InlineKeyboardMarkup()
        inline_kb.row(InlineKeyboardButton("Карта", callback_data="pay_card"))
        inline_kb.row(InlineKeyboardButton("Bitcoin", callback_data="pay_btc"),
                      InlineKeyboardButton("Litecoin", callback_data="pay_ltc"))
        inline_kb.row(InlineKeyboardButton("Отмена", callback_data="cancel"))
    
        await callback_query.message.answer(
            "Выберите метод оплаты:",
            reply_markup=inline_kb
        )
    @dp.callback_query_handler(lambda c: c.data.startswith('pay_'), state=ReplenishBalanceStates.choose_method)
    async def process_payment_method_selection(callback_query: types.CallbackQuery, state: FSMContext):
        payment_method = callback_query.data.split('_')[1]
    
        user_data = await state.get_data()
        product_price = user_data['product_price']
    
        await state.update_data(payment_method=payment_method)
    
        final_amount = calculate_final_amount(product_price, payment_method)
        payment_details = database.get_payment_details(payment_method)
        currency = "RUB" if payment_method == "card" else payment_method.upper()
    
        
        order_number = ''.join([str(random.randint(0, 9)) for _ in range(8)])
    
        await callback_query.message.edit_text(
            f"<b>Заказ №{order_number} ожидает оплаты.</b>\n\nОплатите {final_amount} {currency}.\nРеквизиты: {payment_details}",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup().row(
                InlineKeyboardButton("✅ Я оплатил", callback_data=f"paid")
            ).row(
                InlineKeyboardButton("Отмена", callback_data="cancel")
            )
        )
        await state.finish()
    @dp.message_handler(lambda message: message.text == "Отзывы")
    async def send_first_review(message: types.Message):
        
        review_text = "Все просто супер, лучше не придумаешь. место идеальное и тихое став огонь."
        review_date = "10.06.2023 18:50"
        keyboard = keyboards.get_review_navigation_keyboard(0)
        await message.answer(f"<b>Отзыв от {review_date}</b>\n\nТовар: ALFA (ПРОБА)\n\n{review_text}", reply_markup=keyboard, parse_mode='HTML')
    @dp.callback_query_handler(lambda c: c.data.startswith('review_'))
    async def navigate_reviews(callback_query: types.CallbackQuery):
        
        reviews_data = [
            {"date": "10.06.2023 18:50", "text": "Все просто супер, лучше не придумаешь. место идеальное и тихое став огонь."},
            {"date": "02.06.2023 21:59", "text": "Всё было очень чудесно, поднялся первого касания ))"},
            {"date": "01.06.2023 05:15", "text": "Стаф на пятерочку из пяти, спрятанно было чётко снял в касание, всём советую этот магазин."}
        ]
        
        current_index = int(callback_query.data.split('_')[1])
        review = reviews_data[current_index]
        keyboard = keyboards.get_review_navigation_keyboard(current_index)
        
        await callback_query.message.edit_text(f"<b>Отзыв от {review['date']}</b>\n\nТовар: ALFA (ПРОБА)\n\n{review['text']}", reply_markup=keyboard, parse_mode='HTML')
    @dp.callback_query_handler(lambda c: c.data == 'my_products_list')
    async def process_callback_my_products_list(callback_query: types.CallbackQuery):
        await callback_query.answer("У вас еще нет заказов.", show_alert=True)
    @dp.message_handler(lambda message: message.text == "Личный кабинет")
    async def show_profile(message: types.Message):
        user_id = message.from_user.id

        response_message = (f"Личный Кабинет\n\n"
                            f"Ваш баланс: 0₽\n"
                            f"Пополняйте ваш баланс, чтоб у вас была возможность когда-угодно заказать в нашем магазине.\n\n")
        await message.answer(response_message, parse_mode='HTML', reply_markup=keyboards.replenish_balance_keyboard())
    @dp.message_handler(lambda message: message.text == "Поддержка")
    async def handle_help_request(message: types.Message):
        help_text = database.get_help_text()  
        await message.answer(help_text, parse_mode='HTML')
    @dp.callback_query_handler(lambda c: c.data == 'replenish_balance')
    async def replenish_balance(callback_query: types.CallbackQuery):
        inline_kb = InlineKeyboardMarkup()
        
        inline_kb.row(InlineKeyboardButton("Карта", callback_data="method_card"))
    
        
        inline_kb.row(
            InlineKeyboardButton("Bitcoin", callback_data="method_btc"),
            InlineKeyboardButton("Litecoin", callback_data="method_ltc")
        )
    
        inline_kb.row(InlineKeyboardButton("Отмена", callback_data="cancel"))
        
        await callback_query.message.edit_text(
            "Выберите метод пополнения:",
            reply_markup=inline_kb
        )
        await ReplenishBalanceStates.choose_method.set()
    @dp.callback_query_handler(lambda c: c.data == 'method_card', state=ReplenishBalanceStates.choose_method)
    async def process_card_payment_method(callback_query: types.CallbackQuery, state: FSMContext):
        await state.update_data(payment_method='card')
        await show_enter_amount_message(callback_query.message, state)
    
    @dp.callback_query_handler(lambda c: c.data == 'method_btc', state=ReplenishBalanceStates.choose_method)
    async def process_btc_payment_method(callback_query: types.CallbackQuery, state: FSMContext):
        await state.update_data(payment_method='btc')
        await show_enter_amount_message(callback_query.message, state)
    
    @dp.callback_query_handler(lambda c: c.data == 'method_ltc', state=ReplenishBalanceStates.choose_method)
    async def process_ltc_payment_method(callback_query: types.CallbackQuery, state: FSMContext):
        await state.update_data(payment_method='ltc')
        await show_enter_amount_message(callback_query.message, state)
    
    async def show_enter_amount_message(message, state: FSMContext):
        await message.edit_text(
            "Введите сумму пополнения в рублях:",
            reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("Отмена", callback_data="cancel"))
        )
        await ReplenishBalanceStates.enter_amount.set()
    @dp.message_handler(state=ReplenishBalanceStates.enter_amount)
    async def process_replenish_amount(message: types.Message, state: FSMContext):
        amount = message.text
        if not amount.isdigit() or int(amount) < 1000:
            await message.reply("Введите корректную сумму (не менее 1000 рублей).")
            return
        
        user_data = await state.get_data()
        payment_method = user_data['payment_method']
    
        
        final_amount = calculate_final_amount(amount, payment_method)
    
        payment_details = database.get_payment_details(payment_method)
        currency = "RUB" if payment_method == "card" else payment_method.upper()
    
        await message.answer(
            f"Совершите перевод:\n\nСумма: <code>{final_amount}</code> {currency}\nРеквезиты: <code>{payment_details}</code>",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup().row(
                InlineKeyboardButton("✅ Я оплатил", callback_data="paid")
            ).row(
                InlineKeyboardButton("Отмена", callback_data="cancel")
            )
        )
        await state.finish()
    @dp.callback_query_handler(lambda c: c.data == 'cancel', state='*')
    async def process_cancel(callback_query: types.CallbackQuery, state: FSMContext):
        await state.finish()  
        await callback_query.message.answer("Действие отменено.")
    @dp.callback_query_handler(lambda c: c.data == 'paid', state='*')
    async def process_payment_confirmation(callback_query: types.CallbackQuery, state: FSMContext):
        await callback_query.answer("Ваша оплата не найдена, попробуйте позже или обратитесь в поддержку.", show_alert=True)

     
def calculate_final_amount(amount, payment_method):
    amount = float(amount)
    if payment_method == 'card':
        return amount  
    elif payment_method == 'btc':
        return round(amount / btc_price, 8)  
    elif payment_method == 'ltc':
        return round(amount / ltc_price, 5)  
