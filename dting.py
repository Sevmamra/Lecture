import logging
import random
from aiogram import Bot, Dispatcher, types
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
    CallbackQuery
)
from aiogram.dispatcher import FSMContext
from aiogram.utils import executor
from datetime import datetime, timedelta

API_TOKEN = 'YOUR BOT TOKEN'
CHANNEL_ID = -1002316557460
CHANNEL_LINK = 'https://t.me/+g-i8Vohdrv44NDRl'
ADMIN_ID = 7401896933

bot = Bot(token=API_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot)
logging.basicConfig(level=logging.INFO)

users = {}
waiting_list = []
referrals = {}
banned_users = set()

# Main menus and keyboards
main_menu = ReplyKeyboardMarkup(resize_keyboard=True)
main_menu.add("🎯 Find Random Partner", "👤 My Profile")
main_menu.add("👨 Find Male", "👩 Find Female")
main_menu.add("🧑‍🤝‍🧑 My Referrals", "⏱ Time Left", "🚫 Stop Chat")

gender_kb = ReplyKeyboardMarkup(resize_keyboard=True)
gender_kb.add("♂️ Male", "♀️ Female")

age_kb = ReplyKeyboardMarkup(resize_keyboard=True)
age_kb.add("18-22", "23-27", "28-35", "35+")

def is_profile_complete(user_id): 
    u = users.get(user_id, {}) 
    return "gender" in u and "age" in u

def get_partner(user_id): 
    return users.get(user_id, {}).get("partner")

def time_left(user_id): 
    expires = users.get(user_id, {}).get("chat_expire") 
    if not expires: 
        return 0 
    remaining = (expires - datetime.now()).total_seconds() 
    return max(0, int(remaining // 60))

async def is_joined(user_id):
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

async def match_users():
    random.shuffle(waiting_list)
    for user in waiting_list[:]:
        for other in waiting_list[:]:
            if user != other and not get_partner(user) and not get_partner(other):
                if users[user]["gender"] != users[other]["gender"]:
                    users[user]["partner"] = other
                    users[other]["partner"] = user
                    waiting_list.remove(user)
                    waiting_list.remove(other)
                    await bot.send_message(user, "🎉 Partner found! Say Hi 👋")
                    await bot.send_message(other, "🎉 Partner found! Say Hi 👋")
                    logging.info(f"Matched {user} with {other}")
                    return

async def find_gender_partner(user_id, target_gender):
    random.shuffle(waiting_list)
    for other in waiting_list:
        if user_id != other and users.get(other, {}).get("gender") == target_gender and not get_partner(other):
            users[user_id]["partner"] = other
            users[other]["partner"] = user_id
            waiting_list.remove(user_id)
            waiting_list.remove(other)
            await bot.send_message(user_id, "🎉 Partner found! Say Hi 👋")
            await bot.send_message(other, "🎉 Partner found! Say Hi 👋")
            logging.info(f"Matched {user_id} with {other}")
            return True
    return False

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    user_id = message.from_user.id
    args = message.get_args()

    if not await is_joined(user_id):
        join_btn = types.InlineKeyboardMarkup()
        join_btn.add(types.InlineKeyboardButton("📣 Join Channel", url=CHANNEL_LINK))
        await message.answer("🔐 You must join our channel to use this bot!", reply_markup=join_btn)
        return

    if user_id not in users:
        users[user_id] = {"chat_expire": datetime.now() + timedelta(hours=1)}
        if args.isdigit():
            ref = int(args)
            if ref != user_id:
                referrals.setdefault(ref, []).append(user_id)
                users[ref]["chat_expire"] = users[ref].get("chat_expire", datetime.now()) + timedelta(hours=1)
                await bot.send_message(ref, f"🎁 You got 1 hour for referring {message.from_user.full_name}!")

        await bot.send_message(ADMIN_ID, f"👤 New user joined: {message.from_user.full_name} ({user_id})")

    await message.answer("👋 Welcome to Dating Bot!\nPlease select your gender:", reply_markup=gender_kb)

@dp.message_handler(lambda m: m.text in ["♂️ Male", "♀️ Female"])
async def set_gender(message: types.Message):
    user_id = message.from_user.id
    users[user_id]["gender"] = message.text.replace("♂️", "").replace("♀️", "").strip()
    await message.answer("✅ Gender saved.\nNow choose your age:", reply_markup=age_kb)

@dp.message_handler(lambda m: m.text in ["18-22", "23-27", "28-35", "35+"])
async def set_age(message: types.Message):
    user_id = message.from_user.id
    users[user_id]["age"] = message.text
    await message.answer("✅ Profile completed!", reply_markup=main_menu)

@dp.message_handler(lambda m: m.text == "🎯 Find Random Partner")
async def find_partner(message: types.Message):
    user_id = message.from_user.id
    if not is_profile_complete(user_id):
        return await message.answer("❌ Please complete your profile first.", reply_markup=gender_kb)
    if time_left(user_id) == 0:
        return await message.answer(f"⏳ Your time is over.\n🎁 Refer friends to get +1 hour.\n🔗 https://t.me/{(await bot.get_me()).username}?start={user_id}")
    if user_id in waiting_list:
        return await message.answer("⏳ Already searching...")
    waiting_list.append(user_id)
    await message.answer("🔍 Looking for a random partner...")
    await match_users()

@dp.message_handler(lambda m: m.text == "👩 Find Female")
async def find_female(message: types.Message):
    user_id = message.from_user.id
    if not is_profile_complete(user_id):
        return await message.answer("❌ Complete your profile first.", reply_markup=gender_kb)
    if time_left(user_id) == 0:
        return await message.answer(f"⏳ Your time is over.\n🎁 Refer friends to get +1 hour.\n🔗 https://t.me/{(await bot.get_me()).username}?start={user_id}")
    if user_id in waiting_list:
        return await message.answer("⏳ Already searching...")
    waiting_list.append(user_id)
    success = await find_gender_partner(user_id, "Female")
    if not success:
        await message.answer("⏳ Searching for female users...")

@dp.message_handler(lambda m: m.text == "👨 Find Male")
async def find_male(message: types.Message):
    user_id = message.from_user.id
    if not is_profile_complete(user_id):
        return await message.answer("❌ Complete your profile first.", reply_markup=gender_kb)
    if time_left(user_id) == 0:
        return await message.answer(f"⏳ Your time is over.\n🎁 Refer friends to get +1 hour.\n🔗 https://t.me/{(await bot.get_me()).username}?start={user_id}")
    if user_id in waiting_list:
        return await message.answer("⏳ Already searching...")
    waiting_list.append(user_id)
    success = await find_gender_partner(user_id, "Male")
    if not success:
        await message.answer("⏳ Searching for male users...")

@dp.message_handler(lambda m: m.text == "👤 My Profile")
async def profile(message: types.Message):
    user_id = message.from_user.id
    if not is_profile_complete(user_id):
        await message.answer("❌ Please complete your profile.", reply_markup=gender_kb)
    else:
        u = users[user_id]
        await message.answer(f"👤 Your Profile:\nGender: {u['gender']}\nAge: {u['age']}\n⏱ Time Left: {time_left(user_id)} mins\n\nSend again to change:", reply_markup=gender_kb)

@dp.message_handler(lambda m: m.text == "🚫 Stop Chat")
async def stop_chat(message: types.Message):
    user_id = message.from_user.id
    partner_id = get_partner(user_id)
    if partner_id:
        users[user_id]["partner"] = None
        users[partner_id]["partner"] = None
        await bot.send_message(partner_id, "❌ Partner left the chat.", reply_markup=main_menu)
        await message.answer("✅ You left the chat.", reply_markup=main_menu)
    elif user_id in waiting_list:
        waiting_list.remove(user_id)
        await message.answer("❌ Removed from search queue.", reply_markup=main_menu)
    else:
        await message.answer("❌ Not in chat or queue.")

@dp.message_handler(lambda m: m.text == "🧑‍🤝‍🧑 My Referrals")
async def show_referrals(message: types.Message):
    user_id = message.from_user.id
    count = len(referrals.get(user_id, []))
    ref_link = f"https://t.me/{(await bot.get_me()).username}?start={user_id}"
    await message.answer(f"👥 Your Referrals: {count}\n🔗 Your Link:\n{ref_link}")

@dp.message_handler(lambda m: m.text == "⏱ Time Left")
async def check_time(message: types.Message):
    user_id = message.from_user.id
    await message.answer(f"⏱ Time Left: {time_left(user_id)} mins")

@dp.message_handler(content_types=types.ContentTypes.ANY)
async def relay_message(message: types.Message):
    user_id = message.from_user.id

    if user_id in banned_users:
        return await message.answer("❌ You are banned from using this bot.")

    partner_id = get_partner(user_id)
    if not partner_id:
        return await message.answer("⚠️ You are not currently in a chat. Use 🎯 Find Random Partner to see available users.")

    if time_left(user_id) == 0:
        return await message.answer("⏳ Your chat time has expired. Please refer friends to get more time.")

    try:
        # Relay all content types
        if message.text:
            await bot.send_message(partner_id, message.text)
        elif message.sticker:
            await bot.send_sticker(partner_id, message.sticker.file_id)
        elif message.photo:
            await bot.send_photo(partner_id, photo=message.photo[-1].file_id, caption=message.caption or "")
        elif message.video:
            await bot.send_video(partner_id, video=message.video.file_id, caption=message.caption or "")
        elif message.video_note:
            await bot.send_video_note(partner_id, video_note=message.video_note.file_id)
        elif message.voice:
            await bot.send_voice(partner_id, voice=message.voice.file_id, caption=message.caption or "")
        elif message.audio:
            await bot.send_audio(partner_id, audio=message.audio.file_id, caption=message.caption or "")
        elif message.document:
            await bot.send_document(partner_id, document=message.document.file_id, caption=message.caption or "")
        elif message.animation:
            await bot.send_animation(partner_id, animation=message.animation.file_id, caption=message.caption or "")
        elif message.location:
            await bot.send_location(partner_id, latitude=message.location.latitude, longitude=message.location.longitude)
        elif message.contact:
            await bot.send_contact(partner_id, phone_number=message.contact.phone_number,
                                   first_name=message.contact.first_name,
                                   last_name=message.contact.last_name or "")
        else:
            await message.answer("⚠️ Unsupported message type.")
    except Exception as e:
        logging.error(f"Relay failed: {e}")
        await message.answer("❌ Failed to send message to your partner.")

# Admin Panel Commands
@dp.message_handler(commands=['admin'])
async def admin_panel(message: types.Message):
    if message.from_user.id != 7401896933:
        return await message.answer("❌ Access denied.")
    
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("👥 View Users", callback_data='view_users'),
        InlineKeyboardButton("📢 Broadcast", callback_data='broadcast'),
        InlineKeyboardButton("➕ Add Time", callback_data='add_time'),
        InlineKeyboardButton("🚫 Ban User", callback_data='ban_user'),
    )
    await message.answer("🔐 Admin Panel", reply_markup=keyboard)


# Callback Handler
@dp.callback_query_handler(lambda c: c.data in ["view_users", "broadcast", "add_time", "ban_user"])
async def handle_admin_actions(call: CallbackQuery, state: FSMContext):
    await call.answer()
    
    if call.data == "view_users":
        # Dummy response (replace with actual DB logic)
        await call.message.answer("👥 Total users: 1234")
    
    elif call.data == "broadcast":
        await call.message.answer("📢 Send the broadcast message:")
        await state.set_state("awaiting_broadcast")

    elif call.data == "add_time":
        await call.message.answer("🕒 Send user ID and time to add (e.g. `123456789 2h`):")
        await state.set_state("awaiting_time_add")

    elif call.data == "ban_user":
        await call.message.answer("🚫 Send the user ID to ban:")
        await state.set_state("awaiting_ban")


# Broadcast Message Handler
@dp.message_handler(state="awaiting_broadcast")
async def process_broadcast(message: types.Message, state: FSMContext):
    await state.finish()
    # Broadcast logic — send to all users in your DB
    await message.answer("✅ Broadcast sent.")

# Add Time Handler
@dp.message_handler(state="awaiting_time_add")
async def process_add_time(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("✅ Time added successfully.")

# Ban User Handler
@dp.message_handler(state="awaiting_ban")
async def process_ban_user(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("🚫 User banned successfully.")
    
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
    