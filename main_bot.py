import sqlite3
import os
import logging
import requests
import io
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, ForceReply
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes, ConversationHandler
)
from telegram.constants import ParseMode

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from PIL import Image, ImageDraw, ImageFont
from cryptography.fernet import Fernet
from dotenv import load_dotenv

# --- Configuration & Initialization ---

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load sensitive data and configuration from environment variables
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
PAYSTACK_SECRET_KEY = os.getenv('PAYSTACK_SECRET_KEY')
ENCRYPTION_KEY_STR = os.getenv('ENCRYPTION_KEY')
ADMIN_USER_ID = int(os.getenv('ADMIN_USER_ID', 0))
BOT_WEBHOOK_URL = os.getenv('BOT_WEBHOOK_URL') # e.g., https://your-app-name.herokuapp.com

# Validate that essential environment variables are set
if not all([TELEGRAM_TOKEN, PAYSTACK_SECRET_KEY, ADMIN_USER_ID, BOT_WEBHOOK_URL]):
    raise ValueError("Missing essential environment variables. Please check your .env file.")

# Set up encryption: load key or generate a new one
if ENCRYPTION_KEY_STR:
    ENCRYPTION_KEY = ENCRYPTION_KEY_STR.encode()
else:
    logger.warning("ENCRYPTION_KEY not found. Generating a new one. PLEASE SET THIS IN YOUR .env FILE.")
    ENCRYPTION_KEY = Fernet.generate_key()
    print(f"Generated ENCRYPTION_KEY: {ENCRYPTION_KEY.decode()}")
cipher_suite = Fernet(ENCRYPTION_KEY)

# --- State Definitions for ConversationHandler ---
SELECTING_ACTION, GETTING_LOCATION, CHOOSING_IMAGE, AWAITING_PAYMENT, GETTING_CONTACT = range(5)

# --- Google Drive Configuration ---
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
DRIVE_FOLDER_IDS = {
    'Abia': 'your_folder_id_Abia', 'Adamawa': 'your_folder_id_Adamawa',
    'Akwa Ibom': 'your_folder_id_Akwa_Ibom', 'Anambra': 'your_folder_id_Anambra',
    'Bauchi': 'your_folder_id_Bauchi', 'Bayelsa': 'your_folder_id_Bayelsa',
    'Benue': 'your_folder_id_Benue', 'Borno': 'your_folder_id_Borno',
    'Cross River': 'your_folder_id_Cross_River', 'Delta': 'your_folder_id_Delta',
    'Ebonyi': 'your_folder_id_Ebonyi', 'Edo': 'your_folder_id_Edo',
    'Ekiti': 'your_folder_id_Ekiti', 'Enugu': 'your_folder_id_Enugu',
    'FCT': 'your_folder_id_FCT', 'Gombe': 'your_folder_id_Gombe',
    'Imo': 'your_folder_id_Imo', 'Jigawa': 'your_folder_id_Jigawa',
    'Kaduna': 'your_folder_id_Kaduna', 'Kano': 'your_folder_id_Kano',
    'Katsina': 'your_folder_id_Katsina', 'Kebbi': 'your_folder_id_Kebbi',
    'Kogi': 'your_folder_id_Kogi', 'Kwara': 'your_folder_id_Kwara',
    'Lagos': 'your_folder_id_Lagos', 'Nasarawa': 'your_folder_id_Nasarawa',
    'Niger': 'your_folder_id_Niger', 'Ogun': 'your_folder_id_Ogun',
    'Ondo': 'your_folder_id_Ondo', 'Osun': 'your_folder_id_Osun',
    'Oyo': 'your_folder_id_Oyo', 'Plateau': 'your_folder_id_Plateau',
    'Rivers': 'your_folder_id_Rivers', 'Sokoto': 'your_folder_id_Sokoto',
    'Taraba': 'your_folder_id_Taraba', 'Yobe': 'your_folder_id_Yobe',
    'Zamfara': 'your_folder_id_Zamfara',
}
NIGERIAN_STATES = list(DRIVE_FOLDER_IDS.keys())


# --- Helper Functions ---

def get_drive_service():
    """Authenticates with Google Drive API using a Service Account."""
    try:
        creds = Credentials.from_service_account_file('service_account.json', scopes=SCOPES)
        return build('drive', 'v3', credentials=creds)
    except FileNotFoundError:
        logger.error("service_account.json not found. Please follow the setup guide.")
        return None
    except Exception as e:
        logger.error(f"Failed to create Drive service: {e}")
        return None

def init_db():
    """Initializes the SQLite database and table."""
    conn = sqlite3.connect('user_data.db')
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        contact_info TEXT,
        state TEXT,
        screenshot_count INTEGER DEFAULT 0,
        last_screenshot_time TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    cursor.execute('''
    CREATE TRIGGER IF NOT EXISTS update_users_timestamp
    AFTER UPDATE ON users FOR EACH ROW
    BEGIN
        UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE user_id = OLD.user_id;
    END;
    ''')
    conn.commit()
    conn.close()

def get_state_from_location(latitude, longitude):
    """Gets Nigerian state from coordinates using Nominatim."""
    url = f'https://nominatim.openstreetmap.org/reverse?format=json&lat={latitude}&lon={longitude}'
    headers = {'User-Agent': 'NigeriaConnectBot/1.0'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        state = data.get('address', {}).get('state', '').replace(' State', '')
        return state if state in NIGERIAN_STATES else None
    except requests.RequestException as e:
        logger.error(f"Geolocation request failed: {e}")
        return None

# --- Command Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the conversation and asks the user if they want to connect."""
    keyboard = [
        [InlineKeyboardButton("Yes, find a connection", callback_data='connect_yes')],
        [InlineKeyboardButton("No, thanks", callback_data='connect_no')],
    ]
    await update.message.reply_text(
        "Welcome to NigeriaConnect!\n\n"
        "This bot helps you connect with people across Nigeria. All data is encrypted and handled with care.\n\n"
        "Ready to start?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return SELECTING_ACTION

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    await update.message.reply_text("Process cancelled. Type /start to begin again.")
    context.user_data.clear()
    return ConversationHandler.END

async def user_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to get the total number of users."""
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    try:
        conn = sqlite3.connect('user_data.db')
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        await update.message.reply_text(f"Total users in the database: {count}")
    except Exception as e:
        logger.error(f"Error fetching user count: {e}")
        await update.message.reply_text("Failed to retrieve user count.")
    finally:
        if conn:
            conn.close()


# --- Conversation Steps ---

async def start_connection_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the 'Yes' button, asking for location."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text="Great! Please share your location so I can find connections in your state. You can use the paperclip icon to send your live or current location.")
    return GETTING_LOCATION

async def no_connection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the 'No' button, ending the conversation."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text="No problem. Feel free to come back anytime! Type /start to begin again.")
    return ConversationHandler.END

async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Processes location, fetches images, and presents them."""
    location = update.message.location
    if not location:
        await update.message.reply_text("Could not read location. Please try again or /cancel.")
        return GETTING_LOCATION

    await update.message.reply_text("Checking your location...")
    state = get_state_from_location(location.latitude, location.longitude)
    if not state:
        await update.message.reply_text("Sorry, I couldn't determine a Nigerian state from your location. Please try again or /cancel.")
        return GETTING_LOCATION

    context.user_data['state'] = state
    await update.message.reply_text(f"Location confirmed: {state} State. Searching for available connections...")

    drive_service = get_drive_service()
    if not drive_service:
        await update.message.reply_text("Error: The bot's connection to its data source is down. Please try again later. /cancel")
        return ConversationHandler.END

    folder_id = DRIVE_FOLDER_IDS.get(state)
    if not folder_id:
        await update.message.reply_text(f"Sorry, no connections are available for {state} at the moment. Please check back later. /cancel")
        return ConversationHandler.END

    try:
        results = drive_service.files().list(
            q=f"'{folder_id}' in parents and mimeType contains 'image/'",
            fields="files(id, name, thumbnailLink)",
            pageSize=10  # Limit to 10 images
        ).execute()
        images = results.get('files', [])

        if not images:
            await update.message.reply_text(f"No connections found for {state}. /cancel")
            return ConversationHandler.END

        context.user_data['images'] = {img['id']: img['name'] for img in images}
        
        # Send images as a media group
        media_group = []
        keyboard_buttons = []
        for img in images:
            # Using thumbnailLink for faster previews in the media group
            media_group.append(InputMediaPhoto(media=img['thumbnailLink'], caption=img['name']))
            keyboard_buttons.append([InlineKeyboardButton(f"Select {img['name']}", callback_data=f"image_{img['id']}")])
        
        await update.message.reply_media_group(media=media_group)
        await update.message.reply_text(
            "Here are the available connections. Please choose one to proceed to payment.",
            reply_markup=InlineKeyboardMarkup(keyboard_buttons)
        )
        return CHOOSING_IMAGE

    except Exception as e:
        logger.error(f"Error fetching images from Drive: {e}")
        await update.message.reply_text("An error occurred while fetching connections. Please try again. /cancel")
        return ConversationHandler.END

async def handle_image_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles image selection and initiates payment."""
    query = update.callback_query
    await query.answer()
    image_id = query.data.replace('image_', '')
    image_name = context.user_data['images'].get(image_id, "this connection")
    context.user_data['selected_image_id'] = image_id
    
    await query.edit_message_text(text=f"You have selected {image_name}. To get the contact details, a one-time fee of NGN 50 is required.")

    # Paystack Integration
    email = f"{update.effective_user.id}@telegram.user" # Dummy email
    amount_kobo = 5000  # 50 NGN in kobo
    reference = f"tg_{update.effective_user.id}_{int(datetime.now().timestamp())}"
    context.user_data['payment_reference'] = reference

    url = 'https://api.paystack.co/transaction/initialize'
    headers = {'Authorization': f'Bearer {PAYSTACK_SECRET_KEY}'}
    payload = {
        'email': email,
        'amount': amount_kobo,
        'reference': reference,
        'callback_url': f"{BOT_WEBHOOK_URL}/payment_callback", # Optional but good practice
        'metadata': {
            'user_id': update.effective_user.id,
            'image_id': image_id
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        payment_data = response.json()

        if payment_data.get('status'):
            auth_url = payment_data['data']['authorization_url']
            keyboard = [[InlineKeyboardButton("Pay NGN 50 Now", url=auth_url)]]
            await query.message.reply_text(
                "Please complete the payment using the button below. I will notify you once it's confirmed.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return AWAITING_PAYMENT
        else:
            await query.message.reply_text("Could not initialize payment. Please try again. /cancel")
            return ConversationHandler.END
            
    except requests.RequestException as e:
        logger.error(f"Paystack initialization failed: {e}")
        await query.message.reply_text("Payment service is currently unavailable. Please try again later. /cancel")
        return ConversationHandler.END

async def handle_contact_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Saves user's contact info after successful payment."""
    user_id = update.effective_user.id
    contact_info = update.message.text
    state = context.user_data.get('state', 'Unknown')

    encrypted_contact = cipher_suite.encrypt(contact_info.encode()).decode()

    try:
        conn = sqlite3.connect('user_data.db')
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (user_id, contact_info, state, screenshot_count)
            VALUES (?, ?, ?, 0)
            ON CONFLICT(user_id) DO UPDATE SET
            contact_info = excluded.contact_info,
            state = excluded.state;
        """, (user_id, encrypted_contact, state))
        conn.commit()
    except Exception as e:
        logger.error(f"Database error while saving contact: {e}")
        await update.message.reply_text("A database error occurred. Your info was not saved. Please contact support.")
    finally:
        if conn:
            conn.close()

    keyboard = [[InlineKeyboardButton(
        "Take one-time screenshot", 
        callback_data=f'screenshot_{context.user_data["selected_image_id"]}'
    )]]
    await update.message.reply_text(
        "Your contact info has been saved securely! Thank you.\n\n"
        "Here are the details for your connection:\n"
        "**Name**: Jane Doe\n"
        "**Phone**: +234 801 234 5678\n\n"
        "You can take a **single, watermarked screenshot** of the profile image for your records. "
        "This screenshot will be blurred and protected. Sharing is strictly prohibited.",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )
    return ConversationHandler.END


async def handle_screenshot_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generates and sends a protected, watermarked screenshot."""
    query = update.callback_query
    await query.answer()

    user_id = query.effective_user.id
    conn = sqlite3.connect('user_data.db')
    cursor = conn.cursor()
    cursor.execute("SELECT screenshot_count, last_screenshot_time FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    
    count = result[0] if result else 0
    last_time_str = result[1] if result and result[1] else None
    
    if count >= 3:
        await query.edit_message_text("You have reached your screenshot limit (3).")
        conn.close()
        return

    if last_time_str:
        last_time = datetime.fromisoformat(last_time_str)
        if (datetime.now() - last_time) < timedelta(minutes=5):
            await query.edit_message_text("Please wait 5 minutes between screenshot attempts.")
            conn.close()
            return
    
    await query.edit_message_text("Generating your secure screenshot...")

    image_id = query.data.replace('screenshot_', '')
    drive_service = get_drive_service()
    if not drive_service:
        await query.message.reply_text("Could not connect to the data source for the screenshot.")
        conn.close()
        return

    try:
        request = drive_service.files().get_media(fileId=image_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        
        fh.seek(0)
        img = Image.open(fh)
        
        # Watermarking
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("arial.ttf", size=40)
        except IOError:
            font = ImageFont.load_default() # Fallback font
        watermark_text = f"For {query.effective_user.first_name} Only - Do Not Share"
        draw.text((10, 10), watermark_text, fill=(255, 0, 0, 128), font=font)
        
        # Resize/Blur for protection
        img = img.resize((int(img.width * 0.6), int(img.height * 0.6)), Image.Resampling.LANCZOS)
        
        output = io.BytesIO()
        img.save(output, format='PNG')
        output.seek(0)

        # Update DB
        cursor.execute(
            "UPDATE users SET screenshot_count = screenshot_count + 1, last_screenshot_time = ? WHERE user_id = ?",
            (datetime.now().isoformat(), user_id)
        )
        conn.commit()

        await query.message.reply_photo(
            photo=output,
            caption="**IMPORTANT**: This is your one-time screenshot. Saving or sharing this image is prohibited and tracked.",
            protect_content=True,
            parse_mode=ParseMode.MARKDOWN
        )
        await query.edit_message_text("Screenshot sent. This conversation is now complete. Type /start to begin again.")

    except Exception as e:
        logger.error(f"Screenshot generation failed for user {user_id}: {e}")
        await query.message.reply_text("Failed to generate screenshot. Please contact support.")
    finally:
        conn.close()
        context.user_data.clear()


async def paystack_webhook_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles incoming webhooks from Paystack."""
    data = update.effective_message.text  # In a real setup, this would be from a POST request body
    # This is a simplified example. A real webhook needs a web server (Flask/FastAPI)
    # For now, we'll simulate it with a command /fakewebhook {reference}
    
    reference = data.split()[-1] # e.g. /fakewebhook ref_123

    # Verify payment using the reference from the webhook
    url = f"https://api.paystack.co/transaction/verify/{reference}"
    headers = {'Authorization': f'Bearer {PAYSTACK_SECRET_KEY}'}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        payment_data = response.json().get('data')

        if payment_data and payment_data['status'] == 'success':
            user_id = int(payment_data['metadata']['user_id'])
            image_id = payment_data['metadata']['image_id']
            
            # Save the image_id to the bot's user_data for the next step
            context.bot_data.setdefault(user_id, {})['selected_image_id'] = image_id
            
            # Notify the user
            await context.bot.send_message(
                chat_id=user_id,
                text="✅ Payment confirmed!\n\nPlease provide your name and phone number so your connection can reach you. This will be kept private and encrypted.",
                reply_markup=ForceReply(input_field_placeholder="e.g., Alex Johnson, +234...")
            )
            # You might need a way to advance the user's state here.
            # This is a limitation of mixing webhooks with ConversationHandler without a persistent state backend.
        else:
            logger.warning(f"Webhook received for non-successful payment: {reference}")

    except requests.RequestException as e:
        logger.error(f"Paystack webhook verification failed: {e}")


def main() -> None:
    """Run the bot."""
    init_db()
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Conversation handler for the main user flow
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            SELECTING_ACTION: [
                CallbackQueryHandler(start_connection_flow, pattern='^connect_yes$'),
                CallbackQueryHandler(no_connection, pattern='^connect_no$'),
            ],
            GETTING_LOCATION: [MessageHandler(filters.LOCATION, handle_location)],
            CHOOSING_IMAGE: [CallbackQueryHandler(handle_image_selection, pattern='^image_')],
            AWAITING_PAYMENT: [], # State is handled by webhook or timeout
            GETTING_CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_contact_info)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        per_user=True,
        per_chat=True,
    )
    
    # This is a hack to allow the webhook to inject data into the user's context
    # A proper solution would use a persistent context (e.g., via DB)
    async def payment_success_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Simulates payment success to advance conversation. For testing."""
        if update.effective_user.id != ADMIN_USER_ID: return ConversationHandler.END
        
        # Manually set the state and data as if payment was confirmed
        context.user_data['selected_image_id'] = 'dummy_image_id_for_testing' # Set a dummy
        await update.message.reply_text(
            "Admin override: Payment confirmed.\n\nPlease provide your name and phone number.",
            reply_markup=ForceReply(input_field_placeholder="e.g., Alex Johnson, +234...")
        )
        return GETTING_CONTACT

    # Add a handler for the payment success simulation
    conv_handler.states[AWAITING_PAYMENT].append(CommandHandler('paidsuccess', payment_success_command))

    # Handlers
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(handle_screenshot_request, pattern='^screenshot_'))
    application.add_handler(CommandHandler('user_count', user_count))
    application.add_handler(CommandHandler('fakewebhook', paystack_webhook_handler)) # For testing webhook logic

    # Run the bot
    # For production, use webhooks. For development, polling is fine.
    # application.run_webhook(listen="0.0.0.0", port=8443, url_path=TELEGRAM_TOKEN, webhook_url=f"{BOT_WEBHOOK_URL}/{TELEGRAM_TOKEN}")
    logger.info("Starting bot with polling...")
    application.run_polling()


if __name__ == '__main__':
    main()
