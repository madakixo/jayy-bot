# jayy-bot
telegram bot 

krrptaConnect 
Telegram BotA Telegram bot designed to connect users with resources and services, 
integrated with Google Drive for file management and Paystack for payment processing.
This guide walks you through setting up and deploying the krrptaConnect bot for production.

Table of ContentsPrerequisites (#prerequisites)

Local Setup & Configuration (#local-setup--configuration)Clone the Repository (#clone-the-repository)

Install Dependencies (#install-dependencies)

Telegram Bot Setup (#telegram-bot-setup)

Google Drive & Service Account Setup (#google-drive--service-account-setup)

Paystack Setup (#paystack-setup)

Environment Variables (#environment-variables)

Deployment (Heroku Example) (#deployment-heroku-example)Create a Procfile (#create-a-procfile)

PrerequisitesBefore you begin, ensure you have the following:Python: Version 3.8 or higher installed.

Git: For version control and deployment.

Telegram Account: To create and manage your bot.

Google Cloud Account: To use the Google Drive API.

Paystack Account: To process payments.

Deployment Platform: A server or platform-as-a-service (e.g., Heroku, DigitalOcean, Vultr).


Local Setup & ConfigurationClone the RepositoryClone the project repository to your local machine:bash

git clone <your-repo-url>
cd <your-repo-directory>

Caution: Replace <your-repo-url> and <your-repo-directory> with your actual repository URL and directory name.
Install DependenciesCreate a requirements.txt file in your project root with the following content:txt

python-telegram-bot[ext]
google-api-python-client
google-auth-httplib2
google-auth-oauthlib
Pillow
cryptography
requests
python-dotenv

Install the dependencies:bash

pip install -r requirements.txt

Caution: Ensure your Python environment is activated before running the above command.
Telegram Bot SetupOpen Telegram and chat with @BotFather
.
Send /newbot to create a new bot.
Choose a name (e.g., "Nigeria Connect") and a username (e.g., @NigeriaConnectBot).
Save the HTTP API Token provided by BotFather. This is your TELEGRAM_TOKEN.
Set a bot description using /setdescription to inform users about the bot’s purpose and data policy.

Google Drive & Service Account SetupTo enable the bot to access Google Drive folders, follow these steps:Go to the Google Cloud Console.
Create a new project (e.g., "Telegram Bot Connections").
Navigate to APIs & Services > Enabled APIs & Services, click + ENABLE APIS AND SERVICES, 
and enable the Google Drive API.
Go to APIs & Services > Credentials, click + CREATE CREDENTIALS, and select Service Account.
Name the service account (e.g., "drive-reader-bot") and click Create and Continue. 
Assign the Viewer role for basic access, then click Done.
Locate the service account in the Credentials page, go to the KEYS tab, and click ADD KEY > Create new key. 
Select JSON and click CREATE. A JSON file will download.
Rename the downloaded file to service_account.json and place it in your project’s root directory.
Important: Add service_account.json to your .gitignore file to avoid committing sensitive data.

Open service_account.json and copy the client_email (e.g., ...@iam.gserviceaccount.com).
In Google Drive, create 37 state folders. For each folder:Click Share and paste the service account’s client_email, granting Viewer access.

Copy the folder IDs from each folder’s URL (e.g., https://drive.google.com/drive/folders/THIS_IS_THE_ID) 
and update the DRIVE_FOLDER_IDS dictionary in bot.py.

Paystack SetupSign up or log in to your Paystack Dashboard.
Navigate to Settings > API Keys & Webhooks tab.
Copy your Secret Key. This is your PAYSTACK_SECRET_KEY. Use the Test Secret Key for development.
The Webhook URL will be configured later during deployment.

Environment VariablesCreate a .env file in your project’s root directory to store sensitive information.
Add the following variables to .env:env


TELEGRAM_TOKEN="your_telegram_bot_token"

PAYSTACK_SECRET_KEY="your_paystack_secret_key"

ENCRYPTION_KEY="paste_the_generated_key_here"

ADMIN_USER_ID="your_telegram_user_id"

BOT_WEBHOOK_URL="https://your-app-name.herokuapp.com"

Notes:Replace your_telegram_bot_token with the token from BotFather.
Replace your_paystack_secret_key with your Paystack Secret Key.
Generate the ENCRYPTION_KEY using the provided script and paste it here.
Get your Telegram ADMIN_USER_ID by chatting with @userinfobot
 on Telegram.
Update BOT_WEBHOOK_URL with your deployment URL (e.g., Heroku app URL).
Add .env to your .gitignore file to prevent committing sensitive data.

Deployment (Heroku Example)Webhooks are the recommended method for running Telegram bots in production due to their resource efficiency compared to polling.
Create a ProcfileCreate a Procfile in your project’s root directory to instruct Heroku how to run your application:txt

web: python bot.py

Deploy your application to Heroku:Install the Heroku CLI.
Log in to Heroku: heroku login.
Create a new Heroku app: heroku create your-app-name.
Push your code to Heroku: git push heroku main.
Set environment variables on Heroku using:bash

`heroku config:set TELEGRAM_TOKEN="your_telegram_bot_token"'
heroku config:set PAYSTACK_SECRET_KEY="your_paystack_secret_key"
heroku config:set ENCRYPTION_KEY="your_encryption_key"
heroku config:set ADMIN_USER_ID="your_telegram_user_id"
heroku config:set BOT_WEBHOOK_URL="https://your-app-name.herokuapp.com"`

Configure the Paystack Webhook URL in your Paystack Dashboard to point to your deployed app’s webhook endpoint (e.g., https://your-app-name.herokuapp.com/webhook).

NotesEnsure all sensitive files (e.g., service_account.json, .env) are added to .gitignore to avoid exposing secrets.
Test the bot thoroughly in development mode before deploying to production.
For alternative deployment platforms (e.g., DigitalOcean, Vultr), adapt the deployment steps accordingly.

