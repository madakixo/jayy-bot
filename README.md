# jayy-bot
telegram bot 


This guide will walk you through setting up and deploying the NigeriaConnect bot for production.
Part 1: Prerequisites
Python: Ensure you have Python 3.8+ installed.
Git: For version control and deployment.
Telegram Account: To create and manage your bot.
Google Cloud Account: To use the Google Drive API.
Paystack Account: To process payments.
Deployment Platform: A server or platform-as-a-service like Heroku or a VPS (e.g., DigitalOcean, Vultr).
Part 2: Local Setup & Configuration
Clone the Repository
Generated bash
git clone <your-repo-url>
cd <your-repo-directory>
Use code with caution.
Bash
Install Dependencies
Create a requirements.txt file:
Generated txt
python-telegram-bot[ext]
google-api-python-client
google-auth-httplib2
google-auth-oauthlib
Pillow
cryptography
requests
python-dotenv
Use code with caution.
Txt
Install them:
Generated bash
pip install -r requirements.txt
Use code with caution.
Bash
Telegram Bot Setup
a. Chat with @BotFather on Telegram.
b. Send /newbot, choose a name (e.g., "Nigeria Connect") and a username (e.g., NigeriaConnectBot).
c. Save the HTTP API Token it gives you. This is your TELEGRAM_TOKEN.
d. Set a description with /setdescription to inform users about the bot's purpose and data policy.
Google Drive & Service Account Setup (Production Method)
a. Go to the Google Cloud Console.
b. Create a new project (e.g., "Telegram Bot Connections").
c. Go to "APIs & Services" > "Enabled APIs & Services" and click "+ ENABLE APIS AND SERVICES". Search for and enable the Google Drive API.
d. Go to "APIs & Services" > "Credentials". Click "+ CREATE CREDENTIALS" and select "Service Account".
e. Give it a name (e.g., "drive-reader-bot") and click "Create and Continue". Grant it the "Viewer" role for basic access, then click "Done".
f. Find your new service account on the credentials page, click on it, go to the "KEYS" tab.
g. Click "ADD KEY" > "Create new key". Choose JSON and click "CREATE". A JSON file will be downloaded.
h. Rename this file to service_account.json and place it in your project's root directory. IMPORTANT: Add service_account.json to your .gitignore file to avoid committing it to version control.
i. Open the JSON file and find the client_email (e.g., ...iam.gserviceaccount.com).
j. In Google Drive, create your 37 state folders. For each folder, click "Share" and paste the service account's client_email, giving it "Viewer" access.
k. Get the ID for each folder from its URL (https://drive.google.com/drive/folders/THIS_IS_THE_ID) and update the DRIVE_FOLDER_IDS dictionary in bot.py.
Paystack Setup
a. Sign up or log in at Paystack.
b. Go to your Dashboard > Settings > "API Keys & Webhooks" tab.
c. Copy your Secret Key. This is your PAYSTACK_SECRET_KEY. Use the Test Secret Key for development.
d. You will set the Webhook URL later during deployment.
Environment Variables
Create a file named .env in your project's root directory. This file will hold your secrets locally. Add .env to your .gitignore!

'TELEGRAM_TOKEN="your_telegram_bot_token"
PAYSTACK_SECRET_KEY="your_paystack_secret_key"
# Generate this once with the script, then paste it here to make it permanent
ENCRYPTION_KEY="paste_the_generated_key_here"
ADMIN_USER_ID="your_telegram_user_id" # Get your ID from @userinfobot on Telegram
BOT_WEBHOOK_URL="https://your-app-name.herokuapp.com" # Example for Heroku'


Part 3: Deployment (Example with Heroku)
Webhooks are the preferred way to run a Telegram bot in production as they are more resource-efficient than polling.
Create a Procfile
This file tells Heroku how to run your app.
Generated code
web: python bot.py
