import requests

BOT_TOKEN = "8661868720:AAGoXKdncFwDCOsw_lqweIKvn3EXvGuokSM"
CHAT_ID = "8240067274"

url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

response = requests.post(url, data={

    "chat_id": CHAT_ID,

    "text": "🚆 KTMB BOT TEST: GitHub Actions working"

})

print(response.status_code)

print(response.text)
