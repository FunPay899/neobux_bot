from aiogram.fsm.state import State, StatesGroup


class SupportStates(StatesGroup):
    waiting_for_message = State()


class ProfileStates(StatesGroup):
    waiting_for_roblox_username = State()
    waiting_for_roblox_username_before_payment = State()


class AdminProductStates(StatesGroup):
    waiting_title = State()
    waiting_description = State()
    waiting_price = State()
    waiting_robux_amount = State()
    editing_field = State()


class BroadcastStates(StatesGroup):
    waiting_content = State()


class AdminReplyStates(StatesGroup):
    waiting_reply = State()
