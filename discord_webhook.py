import requests
import json


def send_discord_message(subject, message, printer, webhook_base_url):
    # Color code chart
    colors = {
        "STARTED": 255,
        "COMPLETED": 65280,
        "!!!STALLED!!!": 16711680,
        "RECOVERED!!!": 16776960,
        "Printer Added": 255,
        "Printer Removed": 255,
    }
    data = {
        "username": "Printer {}".format(printer),
        #"content": "{}, {}".format(subject, message),
        #"color": 3553598,
        "embeds": [
            {
                "title": subject,
                "description": message,
                "color": colors[subject]
            },
           ],
        "tts": False
    }
    headers = {'Content-type': 'application/json'}

    print("Sending Discord Message")
    try:
        requests.post(webhook_base_url, data=json.dumps(data), headers=headers)
        return 1
    except:
        print("Something Went Wrong")
        return 0


if __name__ == '__main__':
    send_discord_message("STARTED", "teste", "T1")
    send_discord_message("COMPLETED", "teste", "T1")
    send_discord_message("!!!STALLED!!!", "teste", "T2")
    send_discord_message("RECOVERED!!!", "teste", "T3")