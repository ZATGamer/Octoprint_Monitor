import requests


def send_discord_message(subject, message, printer):
    print("TEST")
    data = {
        "username": "Printer {}".format(printer),
        "content": "{}, {}".format(subject, message),
        #"color": 3553598,
        # "embeds": [
        #     {
        #         "author": {
        #             "name": "Captain Hook"
        #         },
        #         "title": "My new embed",
        #         "description": "This is a cool-looking Discord embed, sent directly from JavaScript!",
        #         "color": 3553598
        #     },
        # ],
        "tts": False
    }
    headers = {'Content-type': 'application/json'}


    webhook_base_url = "https://discord.com/api/webhooks/803386709735768144/V3zdiPK-wcaa-VcdEE_h9XcTFQkCEslD1UyE9U-DlwjjQPPHO_rGRkfxLp1XIBXXVtkY"
    print("Sending Discord Message")
    try:
        test = requests.post(webhook_base_url, data=data)
        print(test.status_code)
        return 1
    except:
        print("Something Went Wrong")
        return 0


if __name__ == '__main__':
    send_discord_message("TestE", "teste", "T1")
