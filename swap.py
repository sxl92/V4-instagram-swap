import telebot
import random
import time
import string
import requests
import json
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from datetime import datetime

# Bot configuration
BOT_TOKEN = "8571766239:AAFEdFhZV5r-zmKigkmJoInbZ9FCRtbZDUg"  # Replace with your token
DEFAULT_WEBHOOK_URL = "https://discord.com/api/webhooks/13588761041/-5MqmNYtm71bGnyH7Q5uxOcX"  # Replace
TELEGRAM_CHANNEL_ID = "-100"  # Replace with your channel ID

# Initialize bot
bot = telebot.TeleBot(BOT_TOKEN)

# Session data
session_data = {}
requests_count = 0
errors_count = 0
rate_limit_cooldowns = {}

def init_session_data(chat_id):
    if chat_id not in session_data:
        session_data[chat_id] = {
            "main": None, "main_username": None, "main_validated_at": None,
            "target": None, "target_username": None, "target_validated_at": None,
            "backup": None, "backup_username": None,
            "swap_webhook": None, "bio": None, "name": None,
            "swapper_threads": 1,
            "current_menu": "main",
            "previous_menu": None
        }

def clear_session_data(chat_id, session_type):
    if session_type == "main":
        session_data[chat_id]["main"] = None
        session_data[chat_id]["main_username"] = None
        session_data[chat_id]["main_validated_at"] = None
    elif session_type == "target":
        session_data[chat_id]["target"] = None
        session_data[chat_id]["target_username"] = None
        session_data[chat_id]["target_validated_at"] = None
    elif session_type == "backup":
        session_data[chat_id]["backup"] = None
        session_data[chat_id]["backup_username"] = None
    elif session_type == "close":
        session_data[chat_id]["main"] = None
        session_data[chat_id]["main_username"] = None
        session_data[chat_id]["main_validated_at"] = None
        session_data[chat_id]["target"] = None
        session_data[chat_id]["target_username"] = None
        session_data[chat_id]["target_validated_at"] = None

def check_cooldown(chat_id):
    if chat_id in rate_limit_cooldowns:
        cooldown_until = rate_limit_cooldowns[chat_id]
        if time.time() < cooldown_until:
            bot.send_message(chat_id, "<b> - Rate limit reached. Please wait 30 minutes.</b>", parse_mode='HTML')
            return False
    return True

def set_cooldown(chat_id):
    rate_limit_cooldowns[chat_id] = time.time() + 1800  # 30-minute cooldown

def create_reply_menu(buttons, row_width=2, add_back=True):
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=row_width)
    for i in range(0, len(buttons), row_width):
        row = [KeyboardButton(text) for text in buttons[i:i + row_width]]
        markup.add(*row)
    if add_back:
        markup.add(KeyboardButton("Back"))
    return markup

def validate_session(session_id, chat_id, session_type):
    print(f"Validating session for chat_id: {chat_id}, type: {session_type}, session_id: {session_id}")
    url = "https://i.instagram.com/api/v1/accounts/current_user/"
    headers = {
        "User-Agent": "Instagram 194.0.0.36.172 Android (28/9; 440dpi; 1080x1920; Google; Pixel 3; blueline; blueline; en_US)",
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "en-US",
        "X-IG-App-ID": "567067343352427",
        "X-IG-Capabilities": "3brTvw==",
        "X-IG-Connection-Type": "WIFI",
        "Cookie": f"sessionid={session_id}; csrftoken={''.join(random.choices(string.ascii_letters + string.digits, k=32))}",
        "Host": "i.instagram.com"
    }
    back_menu = "swapper" if session_type == "backup" else "main"
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"Validation response: {response.status_code}, {response.text[:100]}")
        if response.status_code == 200:
            data = response.json()
            if "user" in data and "username" in data["user"]:
                return data["user"]["username"]
            else:
                bot.send_message(chat_id, "<b> - Session valid but no username found</b>", parse_mode='HTML')
        elif response.status_code == 401:
            bot.send_message(chat_id, "<b> - Invalid or expired session ID</b>", parse_mode='HTML')
        elif response.status_code == 429:
            set_cooldown(chat_id)
            bot.send_message(chat_id, "<b> - Rate limit reached. Please wait 30 minutes.</b>", parse_mode='HTML')
        else:
            bot.send_message(chat_id, f"<b> - Unexpected response: {response.status_code}</b>", parse_mode='HTML')
    except requests.exceptions.Timeout:
        bot.send_message(chat_id, "<b> - Request timed out</b>", parse_mode='HTML')
    except Exception as e:
        bot.send_message(chat_id, f"<b> - Validation error: {str(e)}</b>", parse_mode='HTML')
    time.sleep(2)
    bot.send_message(chat_id, "<b> - Failed to log in</b>", parse_mode='HTML')
    clear_session_data(chat_id, session_type)
    session_data[chat_id]["current_menu"] = back_menu
    return None

def send_discord_webhook(webhook_url, username, action, footer=None):
    if not webhook_url or not webhook_url.startswith("https://"):
        return False
    thumbnail_url = "https://cdn.discordapp.com/attachments/1358386363401244865/1367477276568191038/1c7d9a77eb7655559feab2d7c04b64a5.gif"
    title = "92 Swapper" if action == "Swapped" else "92 Swapped"
    description = f"Have A Fun.. {username}"
    color = 0xf30404 if action == "Swapped" else 0xf8f5f5
    embed = {
        "title": title,
        "description": description,
        "color": color,
        "thumbnail": {"url": thumbnail_url},
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "footer": {"text": f"By : {footer or '92 V4'}"}
    }
    payload = {"embeds": [embed]}
    try:
        response = requests.post(webhook_url, json=payload, timeout=5)
        return response.status_code == 204
    except:
        return False

def send_notifications(chat_id, username, action):
    footer = session_data[chat_id]["name"] or "92 V4"
    webhook_url = session_data[chat_id]["swap_webhook"] or DEFAULT_WEBHOOK_URL
    success = send_discord_webhook(webhook_url, username, action, footer)
    if not success and webhook_url != DEFAULT_WEBHOOK_URL:
        send_discord_webhook(DEFAULT_WEBHOOK_URL, username, action, footer)

def send_channel_notification(username, action):
    username_clean = username.lstrip('@')
    message = f"<b> - [#] {username} {action}.!\n - [#] [{username}](https://instagram.com/{username_clean})</b>"
    try:
        bot.send_message(TELEGRAM_CHANNEL_ID, message, parse_mode="Markdown")
    except:
        pass

def generate_random_username():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=16))

def change_username_account1(chat_id, session_id, csrf_token, random_username):
    global requests_count, errors_count
    url = 'https://www.instagram.com/api/v1/web/accounts/edit/'
    data = {
        'first_name': session_data[chat_id].get('name', 'Default Name'),
        'email': 'default@example.com',
        'username': random_username,
        'phone_number': '+0000000000',
        'biography': session_data[chat_id].get('bio', 'Default Bio'),
        'external_url': 'https://example.com',
        'chaining_enabled': 'on'
    }
    headers = {
        'accept': '*/*',
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'en-US,en;q=0.9',
        'content-type': 'application/x-www-form-urlencoded',
        'cookie': f'mid=YQvmcwAEAAFVrBezgjwUhwEQuv3c; csrftoken={csrf_token}; sessionid={session_id};',
        'origin': 'https://www.instagram.com',
        'referer': 'https://www.instagram.com/accounts/edit/',
        'sec-ch-ua': '"Chromium";v="130", "Google Chrome";v="130", "Not?A_Brand";v="99"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
        'x-asbd-id': '129477',
        'x-csrftoken': csrf_token,
        'x-ig-app-id': '936619743392459',
        'x-ig-www-claim': 'hmac.AR0EWvjix_XsqAIjAt7fjL3qLwQKCRTB8UMXTGL5j7pkgSqj',
        'x-instagram-ajax': '1014730915',
        'x-requested-with': 'XMLHttpRequest'
    }
    print(f"Changing username to {random_username} for session {session_id}")
    try:
        response = requests.post(url, headers=headers, data=data, timeout=10)
        requests_count += 1
        response_text = response.text[:500]  # Log first 500 chars
        print(f"Response: {response.status_code}, {response_text}")
        if response.status_code == 200:
            try:
                data = response.json()
                if data.get("status") == "ok":
                    return random_username
                else:
                    error_message = data.get("message", "Unknown error")
                    bot.send_message(chat_id, f"<b> - Failed to change username: {error_message}</b>", parse_mode='HTML')
                    print(f"Error in response: {data}")
                    return None
            except json.JSONDecodeError:
                bot.send_message(chat_id, "<b> - Invalid JSON response from Instagram</b>", parse_mode='HTML')
                print(f"Invalid JSON: {response_text}")
                return None
        elif response.status_code == 429:
            errors_count += 1
            set_cooldown(chat_id)
            bot.send_message(chat_id, "<b> - Rate limit reached. Please wait 30 minutes.</b>", parse_mode='HTML')
            return None
        elif response.status_code == 400:
            errors_count += 1
            bot.send_message(chat_id, "<b> - Invalid request (bad session or username)</b>", parse_mode='HTML')
            return None
        else:
            errors_count += 1
            bot.send_message(chat_id, f"<b> - Failed to change username: {response.status_code}</b>", parse_mode='HTML')
            return None
    except Exception as e:
        errors_count += 1
        bot.send_message(chat_id, f"<b> - Error with 92 Swap Target Session: {str(e)}</b>", parse_mode='HTML')
        print(f"Exception: {str(e)}")
        return None

def revert_username(chat_id, session_id, csrf_token, original_username):
    url = 'https://www.instagram.com/api/v1/web/accounts/edit/'
    data = {
        'first_name': session_data[chat_id].get('name', 'Default Name'),
        'email': 'default@example.com',
        'username': original_username.lstrip('@'),
        'phone_number': '+0000000000',
        'biography': session_data[chat_id].get('bio', 'Default Bio'),
        'external_url': 'https://example.com',
        'chaining_enabled': 'on'
    }
    headers = {
        'accept': '*/*',
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'en-US,en;q=0.9',
        'content-type': 'application/x-www-form-urlencoded',
        'cookie': f'mid=YQvmcwAEAAFVrBezgjwUhwEQuv3c; csrftoken={csrf_token}; sessionid={session_id};',
        'origin': 'https://www.instagram.com',
        'referer': 'https://www.instagram.com/accounts/edit/',
        'sec-ch-ua': '"Chromium";v="130", "Google Chrome";v="130", "Not?A_Brand";v="99"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
        'x-asbd-id': '129477',
        'x-csrftoken': csrf_token,
        'x-ig-app-id': '936619743392459',
        'x-ig-www-claim': 'hmac.AR0EWvjix_XsqAIjAt7fjL3qLwQKCRTB8UMXTGL5j7pkgSqj',
        'x-instagram-ajax': '1014730915',
        'x-requested-with': 'XMLHttpRequest'
    }
    try:
        response = requests.post(url, headers=headers, data=data, timeout=10)
        return response.status_code == 200 and response.json().get("status") == "ok"
    except:
        return False

def change_username_account2(chat_id, session_id, csrf_token, target_username):
    global requests_count, errors_count
    url = 'https://www.instagram.com/api/v1/web/accounts/edit/'
    data = {
        'first_name': session_data[chat_id].get('name', 'Default Name'),
        'email': 'default@example.com',
        'username': target_username.lstrip('@'),
        'phone_number': '+0000000000',
        'biography': session_data[chat_id].get('bio', 'Default Bio'),
        'external_url': 'https://example.com',
        'chaining_enabled': 'on'
    }
    headers = {
        'accept': '*/*',
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'en-US,en;q=0.9',
        'content-type': 'application/x-www-form-urlencoded',
        'cookie': f'mid=YQvmcwAEAAFVrBezgjwUhwEQuv3c; csrftoken={csrf_token}; sessionid={session_id};',
        'origin': 'https://www.instagram.com',
        'referer': 'https://www.instagram.com/accounts/edit/',
        'sec-ch-ua': '"Chromium";v="130", "Google Chrome";v="130", "Not?A_Brand";v="99"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
        'x-asbd-id': '129477',
        'x-csrftoken': csrf_token,
        'x-ig-app-id': '936619743392459',
        'x-ig-www-claim': 'hmac.AR0EWvjix_XsqAIjAt7fjL3qLwQKCRTB8UMXTGL5j7pkgSqj',
        'x-instagram-ajax': '1014730915',
        'x-requested-with': 'XMLHttpRequest'
    }
    print(f"Changing username to {target_username} for session {session_id}")
    try:
        if not check_cooldown(chat_id):
            return False
        response = requests.post(url, headers=headers, data=data, timeout=10)
        requests_count += 1
        response_text = response.text[:500]
        print(f"Response: {response.status_code}, {response_text}")
        if response.status_code == 200:
            try:
                data = response.json()
                if data.get("status") == "ok":
                    return True
                else:
                    error_message = data.get("message", "Unknown error")
                    bot.send_message(chat_id, f"<b> - Failed to change username: {error_message}</b>", parse_mode='HTML')
                    print(f"Error in response: {data}")
                    return False
            except json.JSONDecodeError:
                bot.send_message(chat_id, "<b> - Invalid JSON response from Instagram</b>", parse_mode='HTML')
                print(f"Invalid JSON: {response_text}")
                return False
        elif response.status_code == 429:
            errors_count += 1
            set_cooldown(chat_id)
            bot.send_message(chat_id, "<b> - Rate limit reached. Please wait 30 minutes.</b>", parse_mode='HTML')
            return False
        elif response.status_code == 400:
            errors_count += 1
            bot.send_message(chat_id, "<b> - Invalid request (bad session or username)</b>", parse_mode='HTML')
            return False
        else:
            errors_count += 1
            bot.send_message(chat_id, f"<b> - Failed to change username: {response.status_code}</b>", parse_mode='HTML')
            return False
    except Exception as e:
        errors_count += 1
        bot.send_message(chat_id, f"<b> - Error changing username: {str(e)}</b>", parse_mode='HTML')
        print(f"Exception: {str(e)}")
        return False

def show_main_menu(chat_id):
    session_data[chat_id]["current_menu"] = "main"
    session_data[chat_id]["previous_menu"] = None
    buttons = [
        "Main Session", "Check Block", "Target Session",
        "Swapper", "Settings", "Close Bot"
    ]
    markup = create_reply_menu(buttons, row_width=2, add_back=False)
    bot.send_message(chat_id, "<b> - Choose A Mode</b>", parse_mode='HTML', reply_markup=markup)

def show_swapper_menu(chat_id):
    session_data[chat_id]["current_menu"] = "swapper"
    session_data[chat_id]["previous_menu"] = "main"
    buttons = ["Run Main Swap", "BackUp Mode", "Threads Swap"]
    markup = create_reply_menu(buttons, row_width=2)
    bot.send_message(chat_id, "<b> - Select Swapper Option</b>", parse_mode='HTML', reply_markup=markup)

def show_settings_menu(chat_id):
    session_data[chat_id]["current_menu"] = "settings"
    session_data[chat_id]["previous_menu"] = "main"
    buttons = ["Webhook", "Bio", "Name"]
    markup = create_reply_menu(buttons, row_width=2)
    bot.send_message(chat_id, "<b> - Select Settings Option</b>", parse_mode='HTML', reply_markup=markup)

@bot.message_handler(commands=["start"])
def start(message):
    chat_id = message.chat.id
    init_session_data(chat_id)
    show_main_menu(chat_id)

@bot.message_handler(func=lambda message: message.text in [
    "Main Session", "Check Block", "Target Session", "Swapper", "Settings", "Close Bot",
    "Run Main Swap", "BackUp Mode", "Threads Swap", "Webhook", "Bio", "Name", "Back", "Stop 92"
])
def handle_menu_navigation(message):
    chat_id = message.chat.id
    init_session_data(chat_id)
    text = message.text
    print(f"Chat ID: {chat_id}, Current Menu: {session_data[chat_id]['current_menu']}, Text: {text}")

    if text == "Back":
        previous_menu = session_data[chat_id]["previous_menu"]
        if previous_menu == "main":
            show_main_menu(chat_id)
        elif previous_menu == "swapper":
            show_swapper_menu(chat_id)
        elif previous_menu == "settings":
            show_settings_menu(chat_id)
        return

    if text == "Stop 92":
        bot.send_message(chat_id, "<b> - 92 Stopped</b>", parse_mode='HTML')
        show_swapper_menu(chat_id)
        return

    if session_data[chat_id]["current_menu"] == "main":
        if text == "Main Session":
            session_data[chat_id]["current_menu"] = "main_session_input"
            markup = create_reply_menu([], add_back=True)
            bot.send_message(chat_id, "<b> - Send Main Session</b>", parse_mode='HTML', reply_markup=markup)
            bot.register_next_step_handler_by_chat_id(chat_id, save_main_session)
        elif text == "Check Block":
            session_data[chat_id]["current_menu"] = "check_block_input"
            markup = create_reply_menu([], add_back=True)
            bot.send_message(chat_id, "<b> - Do You Want To Check Block (Y/N) :</b>", parse_mode='HTML', reply_markup=markup)
            bot.register_next_step_handler_by_chat_id(chat_id, process_check_block)
        elif text == "Target Session":
            session_data[chat_id]["current_menu"] = "target_session_input"
            markup = create_reply_menu([], add_back=True)
            bot.send_message(chat_id, "<b> - Send Target Session</b>", parse_mode='HTML', reply_markup=markup)
            bot.register_next_step_handler_by_chat_id(chat_id, save_target_session)
        elif text == "Swapper":
            show_swapper_menu(chat_id)
        elif text == "Settings":
            show_settings_menu(chat_id)
        elif text == "Close Bot":
            clear_session_data(chat_id, "close")
            bot.send_message(chat_id, "<b> - Main and Target Sessions Reset</b>", parse_mode='HTML')
            show_main_menu(chat_id)

    elif session_data[chat_id]["current_menu"] == "swapper":
        if text == "Run Main Swap":
            run_main_swap(chat_id)
        elif text == "BackUp Mode":
            session_data[chat_id]["current_menu"] = "backup_session_input"
            markup = create_reply_menu([], add_back=True)
            bot.send_message(chat_id, "<b> - Send Backup Session</b>", parse_mode='HTML', reply_markup=markup)
            bot.register_next_step_handler_by_chat_id(chat_id, save_backup_session)
        elif text == "Threads Swap":
            session_data[chat_id]["current_menu"] = "threads_input"
            markup = create_reply_menu([], add_back=True)
            bot.send_message(chat_id, "<b> - Send Me Now The Threads, Recommended =30+</b>", parse_mode='HTML', reply_markup=markup)
            bot.register_next_step_handler_by_chat_id(chat_id, save_swapper_threads)

    elif session_data[chat_id]["current_menu"] == "settings":
        if text == "Webhook":
            session_data[chat_id]["current_menu"] = "webhook_input"
            markup = create_reply_menu([], add_back=True)
            bot.send_message(chat_id, "<b> - Send Swap Webhook URL</b>", parse_mode='HTML', reply_markup=markup)
            bot.register_next_step_handler_by_chat_id(chat_id, save_swap_webhook)
        elif text == "Bio":
            session_data[chat_id]["current_menu"] = "bio_input"
            markup = create_reply_menu([], add_back=True)
            bot.send_message(chat_id, "<b> - Send Bio Text</b>", parse_mode='HTML', reply_markup=markup)
            bot.register_next_step_handler_by_chat_id(chat_id, save_bio)
        elif text == "Name":
            session_data[chat_id]["current_menu"] = "name_input"
            markup = create_reply_menu([], add_back=True)
            bot.send_message(chat_id, "<b> - Send Webhook Footer Name</b>", parse_mode='HTML', reply_markup=markup)
            bot.register_next_step_handler_by_chat_id(chat_id, save_name)

def save_main_session(message):
    chat_id = message.chat.id
    init_session_data(chat_id)
    session_id = message.text.strip()
    username = validate_session(session_id, chat_id, "main")
    if username:
        session_data[chat_id]["main"] = session_id
        session_data[chat_id]["main_username"] = f"@{username}"
        session_data[chat_id]["main_validated_at"] = time.time()
        bot.send_message(chat_id, f"<b> - Main Session Logged @{username}</b>", parse_mode='HTML')
    session_data[chat_id]["current_menu"] = "main"
    show_main_menu(chat_id)

def process_check_block(message):
    chat_id = message.chat.id
    init_session_data(chat_id)
    response = message.text.strip().lower()
    if response == 'y':
        bot.send_message(chat_id, "<b> - Your Account Is Swappable!</b>", parse_mode='HTML')
    elif response == 'n':
        bot.send_message(chat_id, "<b> - Your Account Doesn't Swappable!</b>", parse_mode='HTML')
    else:
        bot.send_message(chat_id, "<b> - Please send 'Y' or 'N'</b>", parse_mode='HTML')
        bot.register_next_step_handler_by_chat_id(chat_id, process_check_block)
        return
    session_data[chat_id]["current_menu"] = "main"
    show_main_menu(chat_id)

def save_target_session(message):
    chat_id = message.chat.id
    init_session_data(chat_id)
    session_id = message.text.strip()
    username = validate_session(session_id, chat_id, "target")
    if username:
        session_data[chat_id]["target"] = session_id
        session_data[chat_id]["target_username"] = f"@{username}"
        session_data[chat_id]["target_validated_at"] = time.time()
        bot.send_message(chat_id, f"<b> - Target Session Logged @{username}</b>", parse_mode='HTML')
    session_data[chat_id]["current_menu"] = "main"
    show_main_menu(chat_id)

def save_backup_session(message):
    chat_id = message.chat.id
    init_session_data(chat_id)
    session_id = message.text.strip()
    username = validate_session(session_id, chat_id, "backup")
    if username:
        session_data[chat_id]["backup"] = session_id
        session_data[chat_id]["backup_username"] = f"@{username}"
        bot.send_message(chat_id, f"<b> - Backup Session Logged @{username}</b>", parse_mode='HTML')
    session_data[chat_id]["current_menu"] = "swapper"
    show_swapper_menu(chat_id)

def save_swapper_threads(message):
    chat_id = message.chat.id
    init_session_data(chat_id)
    try:
        threads = int(message.text)
        if threads >= 1:
            session_data[chat_id]["swapper_threads"] = threads
            bot.send_message(chat_id, f"<b> - Threads Saved: {threads}</b>", parse_mode='HTML')
        else:
            bot.send_message(chat_id, "<b> - Enter a number greater than or equal to 1</b>", parse_mode='HTML')
            bot.register_next_step_handler_by_chat_id(chat_id, save_swapper_threads)
            return
    except ValueError:
        bot.send_message(chat_id, "<b> - Enter a valid number</b>", parse_mode='HTML')
        bot.register_next_step_handler_by_chat_id(chat_id, save_swapper_threads)
        return
    session_data[chat_id]["current_menu"] = "swapper"
    show_swapper_menu(chat_id)

def save_swap_webhook(message):
    chat_id = message.chat.id
    init_session_data(chat_id)
    webhook = message.text.strip()
    session_data[chat_id]["swap_webhook"] = webhook
    bot.send_message(chat_id, "<b> - Swap Webhook Set</b>", parse_mode='HTML')
    session_data[chat_id]["current_menu"] = "settings"
    show_settings_menu(chat_id)

def save_bio(message):
    chat_id = message.chat.id
    init_session_data(chat_id)
    bio = message.text.strip()
    session_data[chat_id]["bio"] = bio
    bot.send_message(chat_id, "<b> - Bio Set</b>", parse_mode='HTML')
    session_data[chat_id]["current_menu"] = "settings"
    show_settings_menu(chat_id)

def save_name(message):
    chat_id = message.chat.id
    init_session_data(chat_id)
    name = message.text.strip()
    session_data[chat_id]["name"] = name
    bot.send_message(chat_id, "<b> - Done Adding Name</b>", parse_mode='HTML')
    session_data[chat_id]["current_menu"] = "settings"
    show_settings_menu(chat_id)

def run_main_swap(chat_id):
    global requests_count, errors_count
    init_session_data(chat_id)
    print(f"Starting swap for chat_id: {chat_id}, main: {session_data[chat_id]['main']}, target: {session_data[chat_id]['target']}, requests_count: {requests_count}")
    if not session_data[chat_id]["main"] or not session_data[chat_id]["target"]:
        bot.send_message(
            chat_id, "<b> - Set Main and Target Sessions first.</b>", parse_mode='HTML',
            reply_markup=create_reply_menu([], add_back=True)
        )
        session_data[chat_id]["current_menu"] = "swapper"
        return
    main_valid = session_data[chat_id]["main_username"].lstrip('@') if session_data[chat_id]["main_validated_at"] and time.time() - session_data[chat_id]["main_validated_at"] < 3600 else validate_session(session_data[chat_id]["main"], chat_id, "main")
    target_valid = session_data[chat_id]["target_username"].lstrip('@') if session_data[chat_id]["target_validated_at"] and time.time() - session_data[chat_id]["target_validated_at"] < 3600 else validate_session(session_data[chat_id]["target"], chat_id, "target")
    print(f"Main valid: {main_valid}, Target valid: {target_valid}")
    if not main_valid or not target_valid:
        bot.send_message(
            chat_id, "<b> - Invalid Main or Target Session.</b>", parse_mode='HTML',
            reply_markup=create_reply_menu([], add_back=True)
        )
        session_data[chat_id]["current_menu"] = "swapper"
        return
    try:
        # Send initial message
        progress_message = bot.send_message(chat_id, "<b> - Starting swap...</b>", parse_mode='HTML')
        message_id = progress_message.message_id

        # Animation frames for progress
        animation_frames = [
            "<b> - Swapping username... █</b>",
            "<b> - Swapping username... ██</b>",
            "<b> - Swapping username... ███</b>",
            "<b> - Swapping username... ████</b>"
        ]
        
        csrf_token = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
        target_session = session_data[chat_id]["target"]
        target_username = session_data[chat_id]["target_username"]
        random_username = generate_random_username()

        # Step 1: Change target to random username
        bot.edit_message_text(
            "<b> - Changing target to random username...</b>", chat_id, message_id, parse_mode='HTML'
        )
        for i in range(4):  # Animate for ~2 seconds
            bot.edit_message_text(animation_frames[i], chat_id, message_id, parse_mode='HTML')
            time.sleep(0.5)
        time.sleep(2)  # Existing delay
        random_username_full = change_username_account1(chat_id, target_session, csrf_token, random_username)
        if not random_username_full:
            bot.edit_message_text(
                f"<b> - Failed to update target {target_username}.</b>", chat_id, message_id, parse_mode='HTML'
            )
            clear_session_data(chat_id, "main")
            clear_session_data(chat_id, "target")
            show_swapper_menu(chat_id)
            return

        # Step 2: Change main to target username
        bot.edit_message_text(
            f"<b> - Setting main to {target_username}...</b>", chat_id, message_id, parse_mode='HTML'
        )
        for i in range(4):  # Animate for ~2 seconds
            bot.edit_message_text(animation_frames[i], chat_id, message_id, parse_mode='HTML')
            time.sleep(0.5)
        time.sleep(2)  # Existing delay
        success = change_username_account2(chat_id, session_data[chat_id]["main"], csrf_token, target_username)
        if success:
            bot.edit_message_text(
                f"<b> - Main Swap\n - {target_username}\n - Success!</b>", chat_id, message_id, parse_mode='HTML'
            )
            release_time = datetime.now().strftime("%I:%M:%S %p")
            bot.send_message(
                chat_id, f"<b> - {target_username} Released [{release_time}]</b>", parse_mode='HTML'
            )
            send_notifications(chat_id, target_username, "Swapped")
            send_channel_notification(target_username, "Swapped")
        else:
            bot.edit_message_text(
                f"<b> - Swap failed for {target_username}.</b>", chat_id, message_id, parse_mode='HTML'
            )
            if revert_username(chat_id, target_session, csrf_token, target_username):
                bot.send_message(
                    chat_id, f"<b> - Successfully reverted to {target_username}.</b>", parse_mode='HTML'
                )
            else:
                bot.send_message(
                    chat_id, f"<b> - Warning: Could not revert to {target_username}.</b>", parse_mode='HTML'
                )
        clear_session_data(chat_id, "main")
        clear_session_data(chat_id, "target")
    except Exception as e:
        bot.edit_message_text(
            f"<b> - Error during swap: {str(e)}</b>", chat_id, message_id, parse_mode='HTML'
        )
    show_swapper_menu(chat_id)

# Start the bot
bot.polling(none_stop=True)
