import smtplib
import configparser


def send_notification(subject, body):
    print("Sending Email")
    config = configparser.RawConfigParser()
    config.read('./config/email_config.ini')

    recipients_list = []
    recipients_list.append(config.get('EmailInfo', 'recipient'))

    message = \
        "From: {sender}\n" \
        "To: {receivers}\n" \
        "Subject: {subject}\n \n" \
        "{body}".format(sender=config.get('EmailInfo', 'sender'),
                        receivers=config.get('EmailInfo', 'recipient'),
                        subject=subject,
                        body=body)

    try:
        session = smtplib.SMTP(config.get('EmailInfo', 'server'), int(config.get('EmailInfo', 'port')))
        session.ehlo()
        session.starttls()
        session.ehlo()
        session.login(config.get('EmailInfo', 'sender'), config.get('EmailInfo', 'password'))
        session.sendmail(config.get('EmailInfo', 'sender'), recipients_list, message)
        session.quit()
        return 1
    except:
        print("Something Went Wrong")
        return 0


if __name__ == '__main__':
    send_notification('Printer X has Stalled', 'We shall see if this actually sends this time.')