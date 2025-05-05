import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import time
from twilio.rest import Client
import os
from dotenv import load_dotenv
import json
from pytz import timezone #For fixing time in IST
import sys #For taking input via crontab
#For hiding keys and token IDs
load_dotenv()

        ## Read Clean Data

# Google sheet Read-Only Authentication
SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_PATH")
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets.readonly',
    'https://www.googleapis.com/auth/drive.readonly'
]

creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
client = gspread.authorize(creds)

SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME") 
sheet = client.open(SHEET_NAME).sheet1
records = sheet.get_all_records()

#Feedback form whole data in df
df = pd.DataFrame(records)

columns_to_keep = ['Name', 'Mobile No.', 'Birthday Date', 'Marriage  Anniversary', 'Date of Visit', 'Timestamp']
df = df[[col for col in columns_to_keep if col in df.columns]]

#For Missing date of visit data

if 'Timestamp' in df.columns:
    df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce', dayfirst=True)
if 'Date of Visit' in df.columns:
    df['Date of Visit'] = pd.to_datetime(df['Date of Visit'], errors='coerce', dayfirst=True)

# Fill missing Date of Visit using date part of Timestamp
df['Date of Visit'] = df['Date of Visit'].fillna(df['Timestamp']).dt.date

df.drop(columns=['Timestamp'], inplace=True, errors='ignore')

#drop invalid phone number data
df = df[df['Mobile No.'].astype(str).str.match(r'^\d{10}$')]

#for unnamed customers
df['Name'] = df['Name'].replace(r'^\s*$', None, regex=True).fillna('Customer')


df_clean = df.copy()

        ## Filter Events today

def clean_date_column(series):
    return pd.to_datetime(series, errors='coerce', dayfirst=True).dt.strftime('%d/%m')

# Normalize the birthday and anniversary columns
df_clean['Birthday'] = clean_date_column(df_clean['Birthday Date'])
df_clean['Anniversary'] = clean_date_column(df_clean['Marriage  Anniversary'])

IST = timezone('Asia/Kolkata')
now = datetime.now(IST)
#now = now.replace(year = 2025, month = 5, day = 7)
today_str = now.strftime('%d/%m')
current_time = now.strftime('%H:%M')


#Seprate data for seprate events for today
birthday_today = df_clean[(df_clean['Birthday'] ==today_str) & (df_clean['Anniversary'] !=today_str)].copy()
anniversary_today = df_clean[(df_clean['Birthday'] !=today_str) & (df_clean['Anniversary'] ==today_str)].copy()
both_today = df_clean[(df_clean['Birthday'] ==today_str) & (df_clean['Anniversary'] ==today_str)].copy()

        ## Send WhatsApp Messages
#Twilio account details
account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
from_whatsapp_number = os.getenv("FROM_WHATSAPP_NUMBER")

client = Client(account_sid, auth_token)

#Content to send
birthday_template_sid = os.getenv("BIRTHDAY_TEMPLATE_SID")
anniversary_template_sid = os.getenv("ANNIVERSARY_TEMPLATE_SID")
both_template_sid = os.getenv("BOTH_TEMPLATE_SID")

#Message sending function
def send_whatsapp_message(recipient_number, customer_name, template_sid):
    try:
        variables = {
            "1": customer_name
        }
        content_variables = json.dumps(variables)

        message = client.messages.create(
            from_=from_whatsapp_number,
            to=f'whatsapp:+91{recipient_number}',
            content_sid=template_sid,
            content_variables=content_variables
        )

        print(f"Sent to {customer_name} ({recipient_number})")

    except Exception as e:
        print(f"Failed to send to {customer_name} ({recipient_number}) | Error: {e}")

# Wait until 9:30
target_time_str = "9:30" #default time
if len(sys.argv) > 1:
	target_time_str = sys.argv[1]   #if time is provided via crontab
target_hour_str, target_min_str = target_time_str.split(":")

target_time = datetime.strptime(target_time_str, "%H:%M").time()

print(target_time)
# Calculate minutes left to 9:30
minutes_to_target = ((target_time.hour - now.hour) * 60) + (target_time.minute - now.minute)

if minutes_to_target < 0:
    minutes_to_target += 1440

print("="*60)
print(f"Today is: {today_str}")
print(f"Current Time: {now.strftime('%H:%M')}")
print(f"Target Time: {target_time_str}")
print(f"Minutes left to {target_time_str}: {minutes_to_target}")

if 0 <= minutes_to_target <= 5:
    while now.strftime('%H:%M') != target_time_str :
        
        now = datetime.now(IST)

        target_time = IST.localize(datetime(now.year, now.month, now.day, int(target_hour_str), int(target_min_str)))
        seconds_left = (target_time - now).total_seconds()
        minutes_left = int(seconds_left // 60) + 1
        print(f"Waiting for {target_time_str} ... {minutes_left} minutes left.")
        time.sleep(60)
    print(f"Starting to send messages at {now.strftime('%H:%M')}.")
else:
    print(f"Not within 5 minutes of {target_time_str}. Exiting without sending messages.")
    print("="*60)
    print("\n")
    print("\n")
    print("\n")
    exit()

# After reaching 9:30, send messages
print("\n")
print(f"Starting to send messages at {target_time_str}.")

if not birthday_today.empty:
    print("Sending Birthday Messages:")
    for index, row in birthday_today.iterrows():
        name = row['Name']
        mobile_number = row['Mobile No.']
        send_whatsapp_message(mobile_number, name, birthday_template_sid)
    print("-"*30)
    print(f"Total Customers having Birthday Today: {len(birthday_today)}")
    print("-"*30)

else:
    print("No customers have Birthday today.")


if not anniversary_today.empty:
    print("Sending Anniversary Messages:")
    for index, row in anniversary_today.iterrows():
        name = row['Name']
        mobile_number = row['Mobile No.']
        send_whatsapp_message(mobile_number, name, anniversary_template_sid)
    print("-"*30)
    print(f"Total Customers having Marriage Anniversary Today: {len(anniversary_today)}")
    print("-"*30)
else:
    print("No customers have Anniversary today.")

if not both_today.empty:
    print("Sending Both Birthday and Anniversary Messages:")
    both_customers = 0
    for index, row in both_today.iterrows():
        name = row['Name']
        mobile_number = row['Mobile No.']
        send_whatsapp_message(mobile_number, name, both_template_sid)
    print("-"*30)
    print(f"Total Customers having Both Birthday and Marriage Anniversary Today: {len(both_today)}")
    print("-"*30)
else:
    print("No customers have both Birthday and Anniversary today.")

print("All messages processed.")
print("="*60)
print("\n")
print("\n")
print("\n")
