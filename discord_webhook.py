import requests

def send_discord_message(subject, message):
    print("TEST")
    data = {
        "content": "{}, {}".format(subject, message),
        "tts": False,
        "embed": [{
            "name": "Hello, Embed!",
            "description": "This is an embedded message."
        }]
    }

    webhook_base_url = "https://discord.com/api/webhooks/803386709735768144/V3zdiPK-wcaa-VcdEE_h9XcTFQkCEslD1UyE9U-DlwjjQPPHO_rGRkfxLp1XIBXXVtkY"
    print("Sending Discord Message")
    try:
        requests.post(webhook_base_url, data=data)
        return 1
    except:
        print("Something Went Wrong")
        return 0


if __name__ == '__main__':
    send_discord_message("Test", "test")
