import requests
import json

def send_discord_message(subject, message, printer):
    print("TEST")
    # Color code chart
    colors = {
        "STARTED": 255,
        "COMPLETED": 5701887,
        "!!!STALLED!!!": 16711680,
        "RECOVERED!!!": 65280
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


    webhook_base_url = "https://discord.com/api/webhooks/803386709735768144/V3zdiPK-wcaa-VcdEE_h9XcTFQkCEslD1UyE9U-DlwjjQPPHO_rGRkfxLp1XIBXXVtkY"
    print("Sending Discord Message")
    try:
        test = requests.post(webhook_base_url, data=json.dumps(data), headers=headers)
        print(test.status_code)
        return 1
    except:
        print("Something Went Wrong")
        return 0


if __name__ == '__main__':
    send_discord_message("STARTED", "teste", "T1")
    send_discord_message("COMPLETED", "teste", "T1")
    send_discord_message("!!!STALLED!!!", "teste", "T2")
    send_discord_message("RECOVERED!!!", "teste", "T3")