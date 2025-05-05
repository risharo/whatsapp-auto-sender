# WhatsApp Auto-Sender using Twilio, Google Sheets, and AWS

This project automates customer engagement through personalized WhatsApp messages for birthdays and anniversaries. It connects to a live Google Sheet to fetch updated customer details, filters them based on the current date, and sends templated messages using the Twilio API. The automation runs daily on an AWS EC2 instance and uses `crontab` to handle scheduled execution and logging.

The system was initially tested from **03 May 2025 to 05 May 2025**. On the first day, it was executed manually at **09:00 AM** for functional validation. From the next day onward, the project was set to run automatically using `crontab` at **09:28 AM**, with message dispatch scheduled at **09:30 AM**. Logs were redirected to a `log.txt` file, with the **most recent log output appearing at the top**, thanks to a custom crontab setup. This enables quick visibility of current results without scrolling through old logs. A basic HTTP server is also hosted on the instance to access this log file in real-time *(IP hidden for privacy)*.

> **Note**: The project uses only sample customer data and sanitized logs. All phone numbers and names are fake placeholders created for demonstration purposes.
