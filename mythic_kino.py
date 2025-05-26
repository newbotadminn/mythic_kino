import json
import os
import random
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, Message
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


API_TOKEN = '8196367118:AAE1ueNW6LngM2pE6tk486vAnp7hpeuCWxo'

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

DATA_FILE = 'users_data.json'
ADMIN_ID = 6891895481
symbols = ["🎰", "🎲", "💰", "🍒", "🍇", "🔔", "🃏", "🪙", "💎", "🍉", "⭐", "🐾", "🌟", "🎯", "🎉", "🏆", "🎊", "🃁", "🃑"]
VIP_USERS = {6891895481}
DAILY_BONUS = 20

def load_data():
    if not os.path.exists(DATA_FILE) or os.stat(DATA_FILE).st_size == 0:
        return {}
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as file:
            return json.load(file)
    except json.JSONDecodeError:
        return {}

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as file:
        json.dump(data, file, indent=4, ensure_ascii=False)

def ensure_user_data(user_id, data):
    if user_id not in data:
        data[user_id] = {
            "coins": 100,
            "last_bonus": None,
            "invited_by": None,
            "wins": 0,
            "losses": 0,
            "games_played": 0
        }
    else:
        if "wins" not in data[user_id]:
            data[user_id]["wins"] = 0
        if "losses" not in data[user_id]:
            data[user_id]["losses"] = 0
        if "games_played" not in data[user_id]:
            data[user_id]["games_played"] = 0

def load_users_data():
    return load_data()

users_data = load_users_data()

main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="💰 Kundalik bonus"), KeyboardButton(text="👤 Profil")],
        [KeyboardButton(text="🎮 O'yinlar"), KeyboardButton(text="🏆 Leaderboard")],
        [KeyboardButton(text="Shop"), KeyboardButton(text="💰 Pul ishlash")]
    ],
    resize_keyboard=True
)


back_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="⬅️ Orqaga")]],
    resize_keyboard=True
)


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    bot = message.bot  # bot obyektini olish
    user_id = message.from_user.id
    full_name = message.from_user.full_name
    username = message.from_user.username

    user_link = f"<b><a href='tg://user?id={user_id}'>{full_name}</a> (<code>{user_id}</code>)</b>"
    username_display = f" (@<a href='https://t.me/{username}'>{username}</a>)" if username else " (Username yo‘q)"

    data = load_data()
    args = message.text.split()
    referral_id = args[1] if len(args) > 1 else None

    GOLD_TO_SUM_RATE = 5
    INITIAL_BONUS = 1000
    REFERRAL_BONUS = 200

    bot_id = str(random.randint(10000, 99999))
    referral_bonus_text = ""

    if str(user_id) in data:
        bot_id = data[str(user_id)]["bot_id"]
        user_name = data[str(user_id)]["username"]
        welcome_text = (
            f"✨ <b>Assalomu alaykum, {user_link}! 🎉</b>\n\n"
            f"👤 <b>Ismingiz:</b> {user_name}\n"
            f"🆔 <b>Bot ID:</b> <code>{bot_id}</code>\n"
            f"💰 <b>Balansingiz:</b> <b>{data[str(user_id)]['coins']} 𐌆 GoldCoin</b>\n"
            f"💵 <b>So‘m ekvivalenti:</b> <b>{data[str(user_id)]['coins'] * GOLD_TO_SUM_RATE:,} so‘m</b> 💸\n\n"
            f"🎁 <b>Do‘stlaringizni taklif qiling va {REFERRAL_BONUS} GoldCoin mukofotga ega bo‘ling!</b>"
        )
    else:
        data[str(user_id)] = {
            "username": full_name,
            "coins": INITIAL_BONUS,
            "last_bonus": None,
            "invited_by": referral_id,
            "wins": 0,
            "losses": 0,
            "games_played": 0,
            "claimed_bonus": False,
            "bot_id": bot_id
        }

        if referral_id and str(referral_id) in data:
            data[str(referral_id)]["coins"] += REFERRAL_BONUS
            referral_bonus_text = f"🎉 Sizni taklif qilgan foydalanuvchi ham <b>{REFERRAL_BONUS} GoldCoin</b> qo‘lga kiritdi! 🥳\n\n"

        save_data(data)

        welcome_text = (
            f"✨ <b>Assalomu alaykum, {user_link}! 🎉</b>\n\n"
            f"👤 <b>Ismingiz:</b> {full_name}\n"
            f"🆔 <b>Bot ID:</b> <code>{bot_id}</code>\n"
            f"🎊 Siz muvaffaqiyatli ro‘yxatdan o‘tdingiz va <b>{INITIAL_BONUS} 𐌆 GoldCoin</b> yutib oldingiz! 🏆\n\n"
            f"{referral_bonus_text}"
            f"💰 <b>Balansingiz:</b> <b>{data[str(user_id)]['coins']} 𐌆 GoldCoin</b>\n"
            f"💵 <b>So‘m ekvivalenti:</b> <b>{data[str(user_id)]['coins'] * GOLD_TO_SUM_RATE:,} so‘m</b> 💸\n\n"
            f"🎁 <b>Do‘stlaringizni taklif qiling va {REFERRAL_BONUS} GoldCoin mukofotga ega bo‘ling!</b>"
        )

    # Foydalanuvchining profil rasmini olish
    photos = await bot.get_user_profile_photos(user_id)
    if photos.total_count > 0:
        photo = photos.photos[0][-1].file_id  # Eng katta formatdagi rasmni olish
        await message.answer_photo(photo, caption=welcome_text, reply_markup=main_keyboard, parse_mode="HTML")
    else:
        await message.answer(welcome_text, reply_markup=main_keyboard, parse_mode="HTML")


@dp.message(lambda message: message.text == "💰 Pul ishlash")
async def earn_money(message: types.Message):
    """ Referal tizimi orqali GoldCoin ishlash """

    user_id = str(message.from_user.id)
    referral_link = f"https://t.me/gold_coin_uzbot?start={user_id}"

    referral_bonus_text = (
        "👥 <b>Har bir taklif qilingan do‘stingiz</b> – <b>100 GoldCoin</b> oladi!\n"
        "🚀 <b>Siz esa</b> – <b>200 GoldCoin</b> mukofotga ega bo‘lasiz! 🏆💎\n\n"
    )

    text = (
        "🎉 <b>GoldCoin orqali pul ishlash imkoniyati!</b> 🎉\n\n"
        "💰 <b>O‘yin o‘ynang yoki do‘stlaringizni taklif qilib GoldCoin to‘plang!</b> 🎁\n\n"
        f"{referral_bonus_text}"
        "🔗 <b>Sizning referal havolangiz:</b>\n"
        f"<code>{referral_link}</code>\n\n"
        "📢 <i>Do‘stlaringizga ushbu havolani yuboring va ko‘proq mukofotlarga ega bo‘ling!</i> 💎\n\n"
        "🔥 <b>Ko‘proq do‘stlaringizni taklif qiling, ko‘proq mukofot oling!</b> 🔥\n\n"
        "🚀 <b>GoldCoin bilan cheksiz imkoniyatlardan foydalaning!</b> 🚀"
    )

    # Ulashish tugmasi inline havola bilan ishlaydi
    buttons = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📢 Do‘stlarga ulashish",
            switch_inline_query=f"💰 GoldCoin ishlash uchun ushbu havola orqali ro‘yxatdan o‘ting! 🎁\n\n"
                                f"🔗 Havola: {referral_link}\n\n"
                                "🎮 O‘yin o‘ynang, do‘stlaringizni taklif qiling va mukofotga ega bo‘ling! 🏆💎"
        )]
    ])

    await message.answer(text, reply_markup=buttons, parse_mode="HTML")

@dp.message(lambda message: message.text == "💰 Kundalik bonus")
async def daily_bonus(message: types.Message):
    user_id = str(message.from_user.id)
    data = load_data()

    ensure_user_data(user_id, data)

    last_bonus_time = data[user_id].get("last_bonus")
    if last_bonus_time:
        try:
            last_bonus_time = datetime.strptime(last_bonus_time, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            last_bonus_time = None

        if last_bonus_time and datetime.now() - last_bonus_time < timedelta(days=1):
            # Keyingi bonusni olish uchun qolgan vaqtni hisoblash
            time_remaining = timedelta(days=1) - (datetime.now() - last_bonus_time)
            hours, remainder = divmod(time_remaining.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)

            await message.answer(
                f"❌ Siz bugun allaqachon kundalik bonus oldingiz.\n"
                f"🔄 Ertaga qayta urinib ko'ring!\n\n"
                f"📅 Kundalik bonusni olish uchun {time_remaining.days} kun, "
                f"{hours} soat, {minutes} daqiqa, {seconds} soniya qoldi."
            )
            return

    bonus_amount = random.randint(10, 50)
    data[user_id]["coins"] += bonus_amount
    data[user_id]["last_bonus"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    save_data(data)

    await message.answer(
        f"🎉 Tabriklaymiz! Siz kundalik bonusni oldingiz! 🎁\n"
        f"💰 Sizga {bonus_amount} ta GoldCoin berildi.\n\n"
        f"🪙 Joriy balans: {data[user_id]['coins']} ta GoldCoin.\n\n"
        f"⏳ Keyingi bonusni olish uchun {24} soat qolgan. Ertaga yana bonus olish imkoniga ega bo'lasiz!"
    )


COIN_TO_SOM = 5

@dp.message(lambda message: message.text == "👤 Profil")
async def profile(message: Message):
    user_id = str(message.from_user.id)
    username = message.from_user.username or "Noma'lum"
    first_name = message.from_user.first_name

    data = load_data()
    ensure_user_data(user_id, data)

    user_data = data[user_id]
    bot_id = user_data.get("bot_id", "Noma’lum")
    coins = user_data.get("coins", 0)
    wins = user_data.get("wins", 0)
    losses = user_data.get("losses", 0)
    games_played = wins + losses  # ✅ O‘yinlar soni = G‘alaba + Mag‘lubiyat
    win_rate = (wins / games_played * 100) if games_played > 0 else 0
    loss_rate = (losses / games_played * 100) if games_played > 0 else 0
    win_rate = min(win_rate, 100)  # ✅ Maksimal 100% bo‘lishi uchun
    loss_rate = min(loss_rate, 100)  # ✅ Maksimal 100% bo‘lishi uchun

    # ✅ 100.00% emas, 100% bo‘lib chiqadi
    win_rate_text = f"{win_rate:.2f}".rstrip('0').rstrip('.')
    loss_rate_text = f"{loss_rate:.2f}".rstrip('0').rstrip('.')

    last_active = user_data.get("last_active", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    coin_value_in_som = coins * COIN_TO_SOM
    referrals = user_data.get("referrals", 0)  # ✅ Referallar soni
    uploads = user_data.get("uploads", 0)  # ✅ Yuklashlar soni

    sorted_users = sorted(data.items(), key=lambda x: x[1].get("coins", 0), reverse=True)
    user_rank = next((idx + 1 for idx, (uid, _) in enumerate(sorted_users) if uid == user_id), "Noma'lum")

    profile_text = (
        f"👤 <b>{first_name}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 <b>Bot ID:</b> <code>{bot_id}</code>\n"
        f"🆔 <b>Telegram ID:</b> <code>{user_id}</code>\n"
        f"🔗 <b>Telegram:</b> @{username if username != 'Noma\'lum' else 'Mavjud emas'}\n"
        f"📊 <b>Reyting:</b> <b>#{user_rank}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 <b>GoldCoin:</b> <b>{coins:,} 🪙</b>\n"
        f"💵 <b>Jami qiymati:</b> <b>{coin_value_in_som:,} so‘m</b>\n"
        f"👥 <b>Referallar soni:</b> {referrals} ta\n"
        f"📥 <b>Yuklashlar soni:</b> {uploads} ta\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🎮 <b>O‘yinlar:</b> {games_played} (🏆 {wins} | 😔 {losses})\n"
        f"📊 <b>G‘alaba foizi:</b> {win_rate_text}%\n"
        f"📊 <b>Yutqazish foizi:</b> {loss_rate_text}%\n"
        f"⏳ <b>Oxirgi faollik:</b> {last_active}\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )

    user_data["last_active"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    save_data(data)

    await message.answer(profile_text, parse_mode="HTML", reply_markup=back_keyboard)


@dp.message(lambda message: message.text == "🎮 O'yinlar")
async def games_menu(message: types.Message):
    game_keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🪙 Tanga tashlash"), KeyboardButton(text="🎰 Omadli Raqam")],
            [KeyboardButton(text="🎰 Slot mashinasi"), KeyboardButton(text="🎲 Zar o'yini")],
            [KeyboardButton(text="♠️ Blackjack"), KeyboardButton(text="🎯 Tugma bosish")],
            [KeyboardButton(text="⬅️ Orqaga")]
        ],
        resize_keyboard=True
    )
    await message.answer("Qaysi o'yinni o'ynaymiz?", reply_markup=game_keyboard)


BET_VALUES = {
    "coin_flip": 10,  # Masalan, 100 GoldCoin tikish
    "bet_10": 10,
    "bet_50": 10,
    "bet_100": 10,
}
WIN_MULTIPLIERS = {
    "slot_machine": {
        "three_same": 20,  # Oldingi 40 edi, pasaytirildi
        "two_same": 5,  # Oldingi 8 edi, pasaytirildi
        "special_symbol": 1  # Oldingi 2 edi, pasaytirildi
    }
}
WIN_PROBABILITIES = {
    "slot_machine": {
        "three_same": 0.02,  # Oldingi 0.03 edi, pasaytirildi
        "two_same": 0.08,  # Oldingi 0.12 edi, pasaytirildi
        "special_symbol": 0.05  # Oldingi 0.08 edi, pasaytirildi
    }
}


# ❌ Yutqazishda pul yo'qolishi (o'zgarmagan)
LOSS_MULTIPLIERS = {
    "coin_flip": 1,
    "guess_number": 1,
    "slot_machine": 1
}


VIP_WIN_MULTIPLIERS = {
    "coin_flip": 40,
    "guess_number": 25,
    "slot_machine": {
        "three_same": 80,
        "two_same": 30,
        "special_symbol": 90
    }
}


@dp.message(lambda message: message.text == "⬅️ Orqaga")
async def go_back(message: types.Message):
    await message.answer("Siz asosiy menyuga qaytdingiz!", reply_markup=main_keyboard)


@dp.message(lambda message: message.text == "🪙 Tanga tashlash")
async def coin_flip(message: types.Message):
    user_id = str(message.from_user.id)
    data = load_data()
    ensure_user_data(user_id, data)

    bet = BET_VALUES["coin_flip"]
    if data[user_id]["coins"] < bet:
        await message.answer("<b>❗ Sizda yetarli GoldCoin mavjud emas!</b>", parse_mode="HTML")
        return

    # Agar foydalanuvchi hali multiplier yaratmagan bo‘lsa, uni 1.0 ga tenglashtiramiz
    if "multiplier" not in data[user_id]:
        data[user_id]["multiplier"] = 1.0
    if "win_streak" not in data[user_id]:  # G‘alaba seriyasini kuzatish
        data[user_id]["win_streak"] = 0

    # Ketma-ket 100 marta yutgan bo‘lsa, avtomatik yutqazadi
    if data[user_id]["win_streak"] >= 100:
        result = "Dum"  # Majburiy yutqazish
    else:
        result = random.choices(
            ["Bosh", "Dum"],
            weights=[50, 50]  # Ehtimollarni rostlash
        )[0]

    # ✅ G‘alaba holati
    if result == "Bosh":
        winnings = bet * data[user_id]["multiplier"]
        data[user_id]["coins"] += winnings
        data[user_id]["wins"] += 1
        data[user_id]["win_streak"] += 1  # Ketma-ket g‘alabalar sonini oshirish

        # Multiplierni har safar 0.5 ga oshiramiz
        data[user_id]["multiplier"] += 0.5
        save_data(data)

        await message.answer(
            f"🪙 <b>Tanga havoga uloqtirildi...</b>\n🎉 <b>{result}!</b>\n"
            f"🏆 Siz <b>{winnings:.1f} GoldCoin</b> yutib oldingiz! (x{data[user_id]['multiplier']:.1f} multiplier)\n"
            f"🔥 <i>{data[user_id]['win_streak']} marta ketma-ket yutdingiz! Omadingizni yana sinab ko‘ring!</i>",
            parse_mode="HTML"
        )

    # ❌ Mag‘lubiyat holati (100 ga yetgan yoki tasodifiy mag‘lubiyat)
    elif result == "Dum":
        loss_amount = bet
        data[user_id]["coins"] -= loss_amount
        data[user_id]["losses"] += 1

        # Multiplier va win_streak ni reset qilamiz
        data[user_id]["multiplier"] = 1.0
        data[user_id]["win_streak"] = 0
        save_data(data)

        await message.answer(
            f"🪙 <b>Tanga havoga uloqtirildi...</b>\n❌ <b>{result}.</b>\n"
            f"😞 <b>-{loss_amount:.1f} GoldCoin</b> yo‘qotdingiz. ❗\n\n"
            f"💡 <i>Hech qisi yo‘q, yana urinib ko‘ring!</i>",
            parse_mode="HTML"
        )


def create_number_buttons():
    buttons = [InlineKeyboardButton(text=str(i), callback_data=f"lucky_{i}") for i in range(1, 51)]
    help_button = InlineKeyboardButton(text="🆘 Yordam", callback_data="help")
    keyboard = InlineKeyboardMarkup(inline_keyboard=[buttons[i:i+10] for i in range(0, len(buttons), 10)] + [[help_button]])
    return keyboard


@dp.message(lambda message: message.text.startswith("🎰 Omadli Raqam"))
async def lucky_number_start(message: types.Message):
    user_id = str(message.from_user.id)
    data = load_data()
    ensure_user_data(user_id, data)

    # ✅ 1 dan 50 gacha bo‘lgan tasodifiy raqam
    data[user_id]["bot_number"] = random.randint(1, 50)
    data[user_id]["remaining_attempts"] = 3  # Urinishlar soni
    save_data(data)

    await message.answer(
        "🎰 Omadli Raqam O'yiniga Xush Kelibsiz!\n\n"
        "Iltimos, biror raqamni tanlang.\n\n"
        "Tikish miqdori: 15 GoldCoin\n"
        "Sizda 3 ta urinish mavjud.",
        reply_markup=create_number_buttons()
    )


@dp.callback_query(lambda call: call.data.startswith("lucky_"))
async def lucky_number(call: types.CallbackQuery):
    user_id = str(call.from_user.id)
    data = load_data()
    ensure_user_data(user_id, data)

    if data[user_id]["remaining_attempts"] <= 0:
        await call.answer("❗ Sizning urinishlaringiz tugadi!", show_alert=True)
        return

    bet = 15  # ✅ Tikish miqdori o‘zgartirildi (15 GoldCoin)
    if data[user_id]["coins"] < bet:
        await call.answer("❗ Sizda yetarli GoldCoin mavjud emas!", show_alert=True)
        return

    user_number = int(call.data.split("_")[1])
    bot_number = data[user_id]["bot_number"]

    data[user_id]["remaining_attempts"] -= 1
    remaining_attempts = data[user_id]["remaining_attempts"]

    if user_number == bot_number:
        winnings = bet * 5
        data[user_id]["coins"] += winnings
        result_text = (
            f"🎉 G'ALABA!\n"
            f"Botning raqami: {bot_number}\n"
            f"Siz {winnings} GoldCoin yutdingiz! (5x)"
        )
        save_data(data)
        await call.message.edit_text(
            f"🎰 Omadli Raqam Natijasi:\n\n{result_text}"
        )
        return

    elif abs(user_number - bot_number) == 1:
        data[user_id]["coins"] -= bet
        result_text = (
            f"👌 Yaqin keldingiz!\n"
            f"Botning raqami: {bot_number}\n"
            f"Siz {bet} GoldCoin yo'qotdingiz."
        )
    else:
        data[user_id]["coins"] -= bet
        result_text = (
            f"❌ Afsus!\n"
            f"Botning raqami: {bot_number}\n"
            f"Siz {bet} GoldCoin yo'qotdingiz."
        )

    save_data(data)

    if remaining_attempts > 0:
        await call.message.edit_text(
            f"🎰 Omadli Raqam Natijasi:\n\n{result_text}\n"
            f"Qolgan urinishlar: {remaining_attempts}"
        )
    else:
        await call.message.edit_text(
            f"🎰 Omadli Raqam Natijasi:\n\n{result_text}\n"
            f"❗ Sizning urinishlaringiz tugadi!\n"
            f"Botning raqami: {bot_number}"
        )


@dp.callback_query(lambda call: call.data == "help")
async def help_button(call: types.CallbackQuery):
    user_id = str(call.from_user.id)
    data = load_data()
    ensure_user_data(user_id, data)

    help_cost = 10  # ✅ Yordam narxi 10 GoldCoin ga o‘zgartirildi
    if data[user_id]["coins"] < help_cost:
        await call.answer("❗ Sizda yetarli GoldCoin mavjud emas!", show_alert=True)
        return

    data[user_id]["coins"] -= help_cost
    bot_number = data[user_id]["bot_number"]

    if bot_number == 1:
        nearest = 2
    elif bot_number == 50:
        nearest = 49
    else:
        nearest = random.choice([bot_number - 1, bot_number + 1])

    hint_text = (
        "🤖 Yordam\n"
        "Botning raqami quyidagilar orasida:\n"
        f"➡️ {nearest}\n"
        "Yordam narxi: -10 GoldCoin"
    )

    save_data(data)
    await call.answer(hint_text, show_alert=True)



@dp.message(lambda message: message.text == "🎰 Slot mashinasi")
async def slot_machine(message: types.Message):
    user_id = str(message.from_user.id)
    data = load_data()
    ensure_user_data(user_id, data)

    bet_options = [100, 500, 1000, 5000, 10000, 50000, 100000, 500000, 1000000, 5000000]
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"{bet} GoldCoin", callback_data=f"bet_{bet}"),
             InlineKeyboardButton(text=f"{bet_options[i + 1]} GoldCoin", callback_data=f"bet_{bet_options[i + 1]}")]
            for i, bet in enumerate(bet_options[:-1:2])
        ]
    )
    await message.answer("🎰 O'ynash uchun stavka tanlang:", reply_markup=keyboard)


@dp.callback_query(lambda call: call.data.startswith("bet_"))
async def process_bet(call: types.CallbackQuery):
    user_id = str(call.from_user.id)
    data = load_data()
    ensure_user_data(user_id, data)

    bet = int(call.data.split("_")[1])
    if data[user_id]["coins"] < bet:
        await call.message.edit_text("❌ Sizda yetarli GoldCoin mavjud emas!")
        return

    await call.message.edit_text(f"✅ Siz {bet} GoldCoin bilan o‘ynayapsiz...⏳")
    data[user_id]["coins"] -= bet  # ❗️ Tangalar oldindan yechib olinadi
    data[user_id]["games_played"] += 1
    save_data(data)

    slot_row = ["❓", "❓", "❓"]
    msg = await call.message.answer(f"🎰 | {' | '.join(slot_row)} |")

    for _ in range(7):
        slot_row = [random.choice(symbols) for _ in range(3)]
        await asyncio.sleep(0.1)
        await msg.edit_text(f"🎰 | {' | '.join(slot_row)} |")

    winnings, bonus_message, bonus_amount = calculate_winnings(slot_row, bet)

    if winnings > 0:
        total_winnings = bet + winnings
        data[user_id]["coins"] += total_winnings  # ✅ Yutgan bo‘lsa, qaytaramiz
        data[user_id]["wins"] += 1
        result_message = (f"\n🔥 <b>Epik G‘alaba!</b> 🎊\n"
                          f"━━━━━━━━━━━━━━━━━━\n"
                          f"📌 <b>Asosiy yutuq:</b> {bet} GoldCoin (+{bonus_amount} GoldCoin)\n"
                          f"🎁 <b>Bonus:</b> +{winnings} GoldCoin\n"
                          f"💰 <b>Jami yutuq:</b> {total_winnings} GoldCoin\n"
                          f"━━━━━━━━━━━━━━━━━━\n"
                          f"{bonus_message}")
    else:
        data[user_id]["losses"] += 1
        result_message = (f"😞 <b>Afsus, omad kelmadi...</b>\n"
                          f"{bet} GoldCoin yo‘qotildi.\n"
                          "🔄 Ammo unutmang, har bir tavakkal katta g‘alabaga yo‘l ochadi!")

    await msg.edit_text(f"🎰 | {' | '.join(slot_row)} |\n{result_message}", parse_mode="HTML")
    save_data(data)


def calculate_winnings(slot_row, bet):
    winnings = 0
    bonus_message = ""
    bonus_amount = 0

    special_symbols = {"🎰", "💎", "💰", "🃏"}
    matching_specials = sum(1 for symbol in slot_row if symbol in special_symbols)

    # Agar kombinatsiyada 2 ta yoki undan kam maxsus belgi bo‘lmasa, hech narsa yutmasin
    if matching_specials < 2:
        return 0, "😞 Afsus, bu kombinatsiyada kamida 2 ta maxsus belgi bo‘lishi kerak.", 0

    symbol_counts = {symbol: slot_row.count(symbol) for symbol in set(slot_row)}

    for symbol, count in symbol_counts.items():
        if count == 1 and symbol in special_symbols:
            bonus = int(bet * 0.1)
            winnings += bonus
            bonus_amount += bonus
            bonus_message += f"{symbol} belgisi uchun +10%! "

    if len(symbol_counts) == 3:
        vals = list(symbol_counts.values())
        avg_bonus = (vals[0] * 10 + vals[1] * 15) / 2
        bonus = int(bet * (avg_bonus / 100))
        winnings += bonus
        bonus_amount += bonus
        bonus_message += "🔄 <b>Strategik kombinatsiya!</b> O‘rtacha bonus qo‘shildi! "

    if any(count == 3 for count in symbol_counts.values()):
        bonus = int(bet * 0.5)
        winnings += bonus
        bonus_amount += bonus
        bonus_message += "💎 <b>3ta bir xil maxsus belgi!</b> +50%! "

    return winnings, bonus_message, bonus_amount


@dp.message(lambda message: message.text == "🎁 Kunlik bonus")
async def daily_bonus(message: types.Message):
    user_id = str(message.from_user.id)
    data = load_data()
    ensure_user_data(user_id, data)

    today = datetime.now().strftime("%Y-%m-%d")

    if data[user_id]["last_bonus"] == today:
        await message.answer("❌ Siz bugungi bonusni oldingiz! Ertaga qaytib keling.")
    else:
        data[user_id]["coins"] += DAILY_BONUS
        data[user_id]["last_bonus"] = today
        save_data(data)
        await message.answer(f"🎁 Siz {DAILY_BONUS} GoldCoin oldingiz! Ertaga qaytib keling.")



    await message.answer("Bosh menyu:", reply_markup=main_keyboard)
# Tugma bosish o'yini
@dp.message(lambda message: message.text == "🎯 Tugma bosish")
async def button_click_game(message: types.Message):
    user_id = str(message.from_user.id)
    data = load_data()

    ensure_user_data(user_id, data)

    if data[user_id]["coins"] < 10:
        await message.answer("Sizda yetarli GoldCoin mavjud emas! Minimal stavka 10 GoldCoin.")
        return

    data[user_id]["coins"] -= 10
    data[user_id]["games_played"] += 1
    save_data(data)

    chance = random.randint(1, 100)
    if chance <= 30:
        winnings = 30
        data[user_id]["coins"] += winnings
        data[user_id]["wins"] += 1
        save_data(data)
        await message.answer(f"🎉 Siz yutdingiz! Sizga {winnings} ta GoldCoin berildi.")
    else:
        data[user_id]["losses"] += 1
        save_data(data)
        await message.answer("❌ Siz yutqazdingiz. 10 ta GoldCoin ayrildi.")

@dp.message(lambda message: message.text == "🏆 Leaderboard")
async def leaderboard(message: types.Message):
    data = load_data()
    user_id = str(message.from_user.id)

    sorted_users = sorted(data.items(), key=lambda x: x[1].get("coins", 0), reverse=True)
    top_10 = sorted_users[:10]

    if not top_10:
        await message.answer("<b>📛 Hozircha reyting mavjud emas.</b>", parse_mode="HTML")
        return

    leaderboard_text = (
        "<b>🏆 LEADERBOARD - TOP 10</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
    )

    medal_emojis = ["🥇", "🥈", "🥉"] + ["🎗"] * 7
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])

    user_rank, user_coins = None, 0
    for idx, (uid, user_data) in enumerate(sorted_users, start=1):
        if uid == user_id:
            user_rank = idx
            user_coins = user_data.get("coins", 0)
            break

    for idx, (uid, user_data) in enumerate(top_10, start=1):
        medal = medal_emojis[idx - 1]
        username = user_data.get("username", "Noma’lum")
        coins = user_data.get("coins", 0)

        leaderboard_text += (
            f"{medal} <b>{idx}-o‘rin</b>\n"
            f"   ├ 👤 <b>{username}</b>\n"
            f"   ├ 💰 <b>{coins} GoldCoin</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
        )

        button_text = "⭐ Siz" if uid == user_id else f"{idx}-o‘rin | 👤 {username}"
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text=button_text, callback_data=f"user_info_{uid}")
        ])

    if user_rank and user_rank > 10:
        leaderboard_text += (
            f"🔰 <b>Siz:</b> {user_rank}-o‘rin | 💰 <b>{user_coins} GoldCoin</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
        )
    elif not user_rank:
        leaderboard_text += "<i>😔 Siz hali reytingda emassiz. Ko‘proq GoldCoin to‘plang! 🚀</i>"

    await message.answer(leaderboard_text, reply_markup=keyboard, parse_mode="HTML")

@dp.callback_query(lambda call: call.data.startswith("user_info_"))
async def user_info(call: types.CallbackQuery):
    data = load_data()
    user_id = call.data.split("_")[2]

    if user_id not in data:
        await call.answer("<b>❌ Foydalanuvchi topilmadi!</b>", show_alert=True, parse_mode="HTML")
        return

    user_data = data[user_id]
    username = user_data.get("username", "Noma’lum")
    coins = user_data.get("coins", 0)
    games_played = user_data.get("games_played", 0)
    wins = user_data.get("wins", 0)
    losses = user_data.get("losses", 0)
    bot_id = user_data.get("bot_id", "Noma’lum")

    user_info_text = (
        f"<b>📌 Foydalanuvchi Ma’lumoti</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>Ismi:</b> {username}\n"
        f"🆔 <b>ID:</b> <code>{user_id}</code>\n"
        f"🤖 <b>Bot ID:</b> {bot_id}\n"
        f"💰 <b>Balans:</b> {coins} GoldCoin\n"
        f"🏆 <b>O‘yinlar:</b> {games_played} ta\n"
        f"✅ <b>G‘alabalar:</b> {wins} ta\n"
        f"❌ <b>Yutqazishlar:</b> {losses} ta\n"
        "━━━━━━━━━━━━━━━━━━━━━"
    )

    await call.message.answer(user_info_text, parse_mode="HTML")
    await call.answer()


@dp.message(lambda message: message.text == "/id")
async def send_user_id(message: types.Message):
    user_id = str(message.from_user.id)
    data = load_data()
    bot_id = data.get(user_id, {}).get("bot_id", "Noma’lum")
    username = data.get(user_id, {}).get("username", "Noma’lum")
    profile_photos = await bot.get_user_profile_photos(user_id)

    caption = (
        f"<b>🔍 Foydalanuvchi Ma’lumotlari</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>Ismi:</b> {username}\n"
        f"🆔 <b>Telegram ID:</b> <code>{user_id}</code>\n"
        f"🤖 <b>Bot ID:</b> <code>{bot_id}</code>\n"
        "━━━━━━━━━━━━━━━━━━━━━"
    )

    if profile_photos.total_count > 0:
        photo = profile_photos.photos[0][0].file_id
        await message.answer_photo(photo=photo, caption=caption, parse_mode="HTML")
    else:
        await message.answer(caption, parse_mode="HTML")


@dp.message(lambda message: message.text == "Shop")
async def shop(message: types.Message):
    shop_keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💸 Pul yechib olish")],
            [KeyboardButton(text="🔙 Orqaga")]
        ],
        resize_keyboard=True
    )
    await message.answer("🏦 Do'konga xush kelibsiz! Nima sotib olmoqchisiz?", reply_markup=shop_keyboard)

# Pul yechib olish tugmasi
@dp.message(lambda message: message.text == "💸 Pul yechib olish")
async def withdraw_coins(message: types.Message):
    user_id = str(message.from_user.id)
    data = load_data()

    ensure_user_data(user_id, data)

    if data[user_id]["coins"] < 10000:
        await message.answer("⚠️ Sizda yetarli GoldCoin mavjud emas! Minimal 10,000 ta GoldCoin kerak.")
        return

    inline_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="10,000", callback_data="withdraw_10000"),
            InlineKeyboardButton(text="50,000", callback_data="withdraw_50000"),
            InlineKeyboardButton(text="100,000", callback_data="withdraw_100000"),
        ],
        [
            InlineKeyboardButton(text="500,000", callback_data="withdraw_500000"),
            InlineKeyboardButton(text="1,000,000", callback_data="withdraw_1000000"),
            InlineKeyboardButton(text="Max", callback_data="withdraw_max"),
        ]
    ])

    await message.answer("💰 Qancha GoldCoin yechib olmoqchisiz?", reply_markup=inline_keyboard)

# Pul yechish miqdorini tanlash
@dp.callback_query(lambda query: query.data.startswith("withdraw_"))
async def process_withdraw(query: types.CallbackQuery):
    user_id = str(query.from_user.id)
    data = load_data()

    ensure_user_data(user_id, data)

    amount_str = query.data.split("_")[1]
    amount = data[user_id]["coins"] if amount_str == "max" else int(amount_str)

    if amount > data[user_id]["coins"]:
        await query.answer("⚠️ Sizda yetarli GoldCoin yo'q!", show_alert=True)
        return

    som_amount = (amount // 10000) * 50000

    data[user_id]["withdraw_request"] = {"amount": amount, "som": som_amount}
    save_data(data)

    await query.message.answer("💳 Karta raqamingizni yuboring (16 xonali):")
    await query.answer()

# Karta raqamini qabul qilish
@dp.message(lambda message: message.text.isdigit() and len(message.text) == 16)
async def process_card_number(message: types.Message):
    user_id = str(message.from_user.id)
    data = load_data()

    if "withdraw_request" not in data[user_id]:
        await message.answer("⚠️ Pul yechib olish so‘rovi topilmadi. Iltimos, qaytadan urinib ko‘ring.")
        return

    data[user_id]["withdraw_request"]["card"] = message.text
    save_data(data)

    card_types_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="UzCard 💳", callback_data="card_UzCard"),
         InlineKeyboardButton(text="Humo 💳", callback_data="card_Humo"),
         InlineKeyboardButton(text="Visa 💳", callback_data="card_Visa")],
    ])

    await message.answer("🏦 Karta turini tanlang:", reply_markup=card_types_keyboard)

# Karta turini tanlash
@dp.callback_query(lambda query: query.data.startswith("card_"))
async def process_card_type(query: types.CallbackQuery):
    user_id = str(query.from_user.id)
    data = load_data()

    if "withdraw_request" not in data[user_id]:
        await query.answer("⚠️ So‘rov topilmadi.", show_alert=True)
        return

    data[user_id]["withdraw_request"]["card_type"] = query.data.split("_")[1]
    save_data(data)

    withdraw_info = data[user_id]["withdraw_request"]

    withdraw_message = (
        f"📝 *Pul yechish so‘rovi:*\n"
        f"👤 *ID:* `{user_id}`\n"
        f"💰 *GoldCoin:* `{withdraw_info['amount']}`\n"
        f"💵 *So‘m miqdori:* `{withdraw_info['som']}`\n"
        f"💳 *Karta:* `{withdraw_info['card']}` ({withdraw_info['card_type']})"
    )

    admin_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"approve_{user_id}")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"cancel_{user_id}")]
    ])

    await bot.send_message(chat_id=ADMIN_ID, text=withdraw_message, reply_markup=admin_keyboard, parse_mode="Markdown")
    await query.message.answer("📩 *So‘rovingiz adminga yuborildi. Tasdiqlanishini kuting!*", parse_mode="Markdown")
    await query.answer()

# Admin tasdiqlashi
@dp.callback_query(lambda query: query.data.startswith(("approve_", "cancel_")))
async def admin_response(query: types.CallbackQuery):
    action, user_id = query.data.split("_")
    data = load_data()

    if user_id not in data:
        await query.answer("⚠️ Foydalanuvchi topilmadi!", show_alert=True)
        return

    if action == "approve":
        amount = data[user_id]["withdraw_request"]["amount"]
        data[user_id]["coins"] -= amount
        save_data(data)
        await bot.send_message(chat_id=user_id, text="✅ *So‘rovingiz tasdiqlandi!*", parse_mode="Markdown")
    else:
        await bot.send_message(chat_id=user_id, text="❌ *So‘rovingiz bekor qilindi!*", parse_mode="Markdown")

    await query.message.edit_text("✅ *Admin javobi yuborildi!*", parse_mode="Markdown")
    await query.answer()




@dp.message(lambda message: message.text == "🔙 Orqaga")
async def back_to_main_menu(message: types.Message):
    await message.answer("🏠 Bosh menyu:", reply_markup=main_keyboard)


# Botni ishga tushirish
if __name__ == '__main__':
    import asyncio

    async def main():
        await dp.start_polling(bot)

    asyncio.run(main())
