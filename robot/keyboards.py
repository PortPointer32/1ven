from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def main_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("Выбор категории"), KeyboardButton("Сменить город/район"))
    keyboard.add(KeyboardButton("Поддержка"))
    keyboard.add(KeyboardButton("Отзывы"))
    keyboard.add(KeyboardButton("Личный кабинет"))
    return keyboard

def replenish_balance_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("Пополнить баланс", callback_data="replenish_balance"))
    keyboard.add(InlineKeyboardButton("📦 Мои заказы", callback_data="my_products_list"))
    return keyboard

def get_review_navigation_keyboard(current_index):
    keyboard = InlineKeyboardMarkup(row_width=2)
    
    prev_button = InlineKeyboardButton("Предыдущий Отзыв", callback_data=f'review_{current_index - 1}')
    next_button = InlineKeyboardButton("Следующий Отзыв", callback_data=f'review_{current_index + 1}')
    
    keyboard.add(prev_button, next_button)
    return keyboard
