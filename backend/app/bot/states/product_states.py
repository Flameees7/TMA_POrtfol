from aiogram.fsm.state import State, StatesGroup


class ProductAddState(StatesGroup):
    """FSM states for creating a new product via Telegram bot."""
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_price = State()
    waiting_for_photos = State()
    waiting_for_status = State()


class ProductEditState(StatesGroup):
    """FSM states for editing an existing product."""
    waiting_for_new_price = State()
    waiting_for_new_photo = State()
