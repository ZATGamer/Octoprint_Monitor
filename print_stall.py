# This will watch Octoprint for a print that has stalled. This will likely indicate a MMU Failure.

from requests.auth import HTTPDigestAuth
import requests
import time
import json
import sqlite3
import os
import datetime
from email_notification import send_email
from discord_webhook import send_discord_message


def get_discord_url(id):
    cur = conn.cursor()
    sql = '''SELECT discord_url FROM state WHERE id = {}'''.format(id)
    discord_url = cur.execute(sql)
    discord_url = discord_url.fetchone()
    return discord_url[0]


def get_all_printers(conn):
    # Get all printers out of the database to check
    cur = conn.cursor()
    sql = '''SELECT id, printer_number, printer_ip, printer_api_key, model FROM state'''
    printers = cur.execute(sql)
    printers = printers.fetchall()
    return printers


def compare_progress(conn, id, last, current, ip):
    # For the printer supplied, dig out past data from the database and then current data from Octoprint
    print("Printer: {}".format(ip))
    print("Last Progress: {}\nCurrent Progress: {}".format(last, current))

    if current != last:
        # Update last to current
        print("Yeah!! It's DIFFERENT")
        update_last_progress(conn, id, current)
        return 'different'
    else:
        # Print Stalled?
        print("Ut'oh... It's the SAME")
        return "same"


def print_started(conn, id, p_number, printer_state, job_name, job_progress):
    cur = conn.cursor()
    # Update Job name in DB
    # Update Progress in DB
    # Reset Completed Flag
    # Reset stall_start
    # Reset stalled
    # Reset stall_count
    # Reset stall_notified
    # Reset complete_notified

    sql = '''UPDATE state set printer_status = '{}',
                              job_name = '{}',
                              progress = {},
                              stall_start = null,
                              stalled = 0,
                              stall_count = 0,
                              stall_notified = 0,
                              completed = 0,
                              complete_notified = 0,
                              print_start_time = '{}' WHERE id = {}'''.format(printer_state, job_name, job_progress, datetime.datetime.now(), id)

    cur.execute(sql)
    conn.commit()
    # Send a start notice
    subject = "P{}, Job Started".format(p_number)
    discord_subject = "STARTED"
    message = "Printer {} has started printing of {}.".format(p_number, job_name)
    #message_sent = send_email(subject, message)
    message_sent = send_discord_message(discord_subject, message, p_number, get_discord_url(id))
    if message_sent:
        notified_sql = '''UPDATE state set started_notified = 1 where id = {}'''.format(id)
        cur.execute(notified_sql)
        conn.commit()


def print_completed(conn, id, p_number, printer_status, job_name):
    cur = conn.cursor()
    # Set the completed Flag
    complete_sql = '''UPDATE state set printer_status = '{}', completed = 1 WHERE id = {}'''.format(printer_status, id)
    cur.execute(complete_sql)
    conn.commit()
    # Send Notice
    subject = "P{}, Job Completed".format(p_number)
    discord_subject = "COMPLETED"
    message = "Printer {} has completed printing of {}.".format(p_number, job_name)
    #message_sent = send_email(subject, message)
    message_sent = send_discord_message(discord_subject, message, p_number, get_discord_url(id))
    # If the message success sent
    if message_sent:
        notified_sql = '''UPDATE state set complete_notified = 1, 
                          stall_start = null,
                          stalled = 0,
                          stall_count = 0,
                          stall_notified = 0 WHERE id = {}'''.format(id)
        cur.execute(notified_sql)
        conn.commit()


def set_stalled(conn, printer_id):
    cur = conn.cursor()
    sql = '''UPDATE state SET stalled = 1, stall_start = '{}', stall_count = 1 WHERE id = {}'''.format(datetime.datetime.now(), printer_id)
    cur.execute(sql)
    conn.commit()


def clear_stalled(conn, printer_id):
    cur = conn.cursor()
    sql = '''UPDATE state SET stalled = 0, stall_start = null, stall_count = 0, stall_notified = 0 WHERE id = {}'''.format(printer_id)
    cur.execute(sql)
    conn.commit()


def stalled(conn, printer_id, printer_number):
    cur = conn.cursor()
    get_info_sql = '''SELECT stall_start, stall_count, stall_notified FROM state WHERE id = {}'''.format(printer_id)
    info = cur.execute(get_info_sql)
    info = info.fetchone()
    stall_start = datetime.datetime.strptime(info[0], '%Y-%m-%d %H:%M:%S.%f')
    stall_count = info[1] + 1
    stall_notified = info[2]
    update_call_count_sql = '''UPDATE state SET stall_count = {}'''.format(stall_count)
    cur.execute(update_call_count_sql)
    conn.commit()

    if stall_start + datetime.timedelta(minutes=3) <= datetime.datetime.now():
        if not stall_notified:
            # If notice has NOT been sent yet...
            subject = "P{}, Stalled".format(printer_number)
            discord_subject = "!!!STALLED!!!"
            message = "P{} Appears to of stalled during the print.".format(printer_number)
            #message_sent = send_email(subject, message)
            print(get_discord_url(printer_id))
            message_sent = send_discord_message(discord_subject, message, printer_number, get_discord_url(printer_id))
            if message_sent:
                cur.execute('''UPDATE state SET stall_notified = 1 WHERE id = {}'''.format(printer_id))
                conn.commit()


def attention(conn, printer_id, printer_number):
    cur = conn.cursor()
    get_info_sql = '''SELECT stall_notified FROM state WHERE id = {}'''.format(printer_id)
    info = cur.execute(get_info_sql)
    info = info.fetchone()
    stall_notified = info[0]

    if not stall_notified:
        # If notice has NOT been sent yet...
        subject = "P{}, Attention Required".format(printer_number)
        discord_subject = "!!!ATTENTION!!!"
        message = "P{} Appears to be in an ATTENTION state, please check the printer.".format(printer_number)
        # message_sent = send_email(subject, message)
        print(get_discord_url(printer_id))
        message_sent = send_discord_message(discord_subject, message, printer_number, get_discord_url(printer_id))
        if message_sent:
            cur.execute('''UPDATE state SET stall_notified = 1 WHERE id = {}'''.format(printer_id))
            conn.commit()


def get_current_progress(ip, api_key):
    url = 'http://{}/api/job'.format(ip)
    headers = {"X-Api-Key": api_key}
    try:
        r_data = requests.get(url, headers=headers)
    except OSError:
        print("Printer {} is unreachable.".format(ip))
        return "-1"

    j_data = json.loads(r_data.content)
    current_progress = j_data['progress']['completion']
    return current_progress


def get_last_progress(conn, printer_id):
    cursor = conn.cursor()
    last_progress = cursor.execute("""SELECT progress FROM state WHERE id = {};""".format(printer_id))
    last_progress = last_progress.fetchone()[0]
    return last_progress


def update_last_progress(conn, printer_id, progress):
    cur = conn.cursor()
    sql = '''UPDATE state SET progress = {} WHERE id = {}'''.format(progress, printer_id)
    cur.execute(sql)
    conn.commit()


def db_setup(db):
    print("Creating the Database for the first time.")
    sql_create_state_table = """CREATE TABLE IF NOT EXISTS state (
                                    id integer PRIMARY KEY,
                                    printer_number integer,
                                    printer_ip text,
                                    printer_api_key text,
                                    printer_status text,
                                    job_name text,
                                    progress real,
                                    stall_start text,
                                    stalled integer,
                                    stall_count integer,
                                    stall_notified integer,
                                    completed integer,
                                    complete_notified integer,
                                    started_notified integer,
                                    discord_url text,
                                    printer_user text,
                                    printer_password text,
                                    model text,
                                    print_start_time text
                                ); """

    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute(sql_create_state_table)
    conn.commit()
    conn.close()


def db_update(db):
    print("Updating database to new schema")
    sql_add_user = """ALTER TABLE state ADD COLUMN printer_user text"""
    sql_add_password = """ALTER TABLE state ADD COLUMN printer_password text"""
    sql_add_model = """ALTER TABLE state ADD COLUMN model text"""

    sqls = [sql_add_user, sql_add_password, sql_add_model]
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    for sql in sqls:
        cursor.execute(sql)
    conn.commit()
    conn.close()


def db_update2(db):
    print("Updating Database to add print_start_time column")
    sql_add_start_time = """ALTER TABLE state ADD COLUMN print_start_time text"""
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute(sql_add_start_time)
    conn.commit()
    conn.close()


def db_setup_connect(db_file):
    if not os.path.exists(db_file):
        db_setup(db_file)

    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    columns = [i[1] for i in cur.execute('PRAGMA table_info(state)')]

    if 'printer_user' not in columns:
        db_update(db_file)

    if 'print_start_time' not in columns:
        db_update2(db_file)

    return conn


def collect_current_print_data_prusalink(printer_info):
    if printer_info['model'] == 'mini+':
        job_url = 'http://{}/api/job'.format(printer_info['ip'])
        prusalink = create_session(printer_info)
        try:
            r_data = prusalink.get(job_url)
            # first check is to see if the stats code is 200, if it is anything else. The printer is not printing or even connected.
            if r_data.status_code == 200:
                j_data = json.loads(r_data.content)
                printer_status = j_data['state']
                if 'job' in j_data.keys():
                    job_name = j_data['job']['file']['name']
                else:
                    job_name = "None"
                if 'progress' in j_data.keys():
                    progress = j_data['progress']['printTimeLeft']
                else:
                    progress = 0

                return printer_status, job_name, progress
            else:
                print("Printer {}: No 3D Printer Connected".format(printer_info['ip']))
                return "Unknown", "Unknown", -1
        except OSError:
            print("Printer {} Unreachable.".format(printer_info['ip']))
            return "Unknown", "Unknown", -1
        except json.decoder.JSONDecodeError:
            print("No JSON for Printer {}".format(printer_info['ip']))
            return "Unknown", "Unknown", -1
    else:
        status_url = 'http://{}/api/v1/status'.format(printer_info['ip'])
        job_url = 'http://{}/api/v1/job'.format(printer_info['ip'])
        prusalink = create_session(printer_info)
        try:
            r_data = prusalink.get(status_url)
            # first check is to see if the stats code is 200, if it is anything else. The printer is not printing or even connected.
            if r_data.status_code == 200:
                j_data = json.loads(r_data.content)
                printer_status = j_data['printer']['state']
                if 'job' in j_data.keys():
                    prusa_job = prusalink.get(job_url)
                    prusa_job = json.loads(prusa_job.content)
                    if 'display_name' in prusa_job['file'].keys():
                        job_name = prusa_job['file']['display_name']
                    else:
                        job_name = "None"
                    if 'time_remaining' in j_data['job'].keys():
                        progress = j_data['job']['time_remaining']
                    else:
                        progress = 0
                else:
                    job_name = "NONE"
                    progress = 0
                return printer_status, job_name, progress
            else:
                print("Printer {}: No 3D Printer Connected".format(printer_info['ip']))
                return "Unknown", "Unknown", -1
        except OSError:
            print("Printer {} Unreachable.".format(printer_info['ip']))
            return "Unknown", "Unknown", -1
        except json.decoder.JSONDecodeError:
            print("No JSON for Printer {}".format(printer_info['ip']))
            return "Unknown", "Unknown", -1


def collect_current_print_data(ip, api_key):
    url = 'http://{}/api/job'.format(ip)
    headers = {"X-Api-Key": api_key}
    try:
        r_data = requests.get(url, headers=headers)
        # first check is to see if the stats code is 200, if it is anything else. The printer is not printing or even connected.
        if r_data.status_code == 200:
            j_data = json.loads(r_data.content)
            printer_status = j_data['state']
            job_name = j_data['job']['file']['name']
            progress = j_data['progress']['completion']
            return printer_status, job_name, progress
        else:
            print("Printer {}: No 3D Printer Connected".format(ip))
            return "Unknown", "Unknown", -1
    except OSError:
        print("Printer {} Unreachable.".format(ip))
        return "Unknown", "Unknown", -1
    except json.decoder.JSONDecodeError:
        print("No JSON for Printer {}".format(ip))
        return "Unknown", "Unknown", -1


def collect_last_print_data(id):
    sql = '''SELECT printer_status, 
                            job_name,
                            progress,
                            completed,
                            stall_start,
                            stalled,
                            stall_count,
                            stall_notified,
                            complete_notified, 
                            started_notified,
                            print_start_time FROM state WHERE id = {}'''.format(id)
    cur = conn.cursor()
    last_state = cur.execute(sql)
    last_state = last_state.fetchone()
    return last_state


def status_changed(conn, db_status, c_status, id, number, c_job_name, db_job_name, c_progress):
    if c_status.lower() == 'attention':
        # Printer is in Attention state and needs you to check on it
        attention(conn, id, number)
        print("Printer in ATTENTION state")
    elif db_status.lower() != 'printing' and c_status.lower() == 'printing':
        # Print Started
        print_started(conn, id, number, c_status, c_job_name, c_progress)
        print("Print Started")
    elif db_status.lower() == 'printing' and c_status.lower() != 'printing':
        # Print Completed
        print_completed(conn, id, number, c_status, db_job_name)
        print("Completed")
    elif c_status.startswith("Offline"):
        # This is to fix the crash when the USB is unplugged from the printer.
        cur = conn.cursor()
        cur.execute('''UPDATE state set printer_status = '{}' WHERE id = {}'''.format("Offline", id))
        conn.commit()
        print("Printer Offline")
    else:
        # TODO: Handel the Unknown State
        # TODO: Handel Canceling State
        cur = conn.cursor()
        cur.execute('''UPDATE state set printer_status = '{}' WHERE id = {}'''.format(c_status, id))
        conn.commit()


def monitor_prints(conn):
    # This is the Monitor for the printers.

    # First thing is to get a list of all the printers
    printers = get_all_printers(conn)

    # Next we will loop though all the printers and do some checks on them.
    # Later on I will make this multi threaded to speed up the checks.
    for printer in printers:
        id = printer[0]
        number = printer[1]
        ip = printer[2]
        api_key = printer[3]
        model = printer[4]
        # First thing to do is collect the data from the DB and from the Printer to run compares on.
        # DB Data
        db_data = collect_last_print_data(id)

        # TODO Add in a check to see if PrusaLink or Octoprint
        prusalink_printers = ['mini+', 'mk4', 'mk3s+']
        if model in prusalink_printers:
            cur = conn.cursor()
            printer_info = cur.execute('''SELECT model,
                                                 printer_user,
                                                 printer_password,
                                                 printer_ip,
                                                 printer_api_key FROM state WHERE printer_ip = "{}"'''.format(ip))
            printer_info = printer_info.fetchone()
            printer_info = {'model': printer_info[0],
                            'user': printer_info[1],
                            'password': printer_info[2],
                            'ip': printer_info[3],
                            'api_key': printer_info[4]}
            c_status, c_job_name, c_progress = collect_current_print_data_prusalink(printer_info)
        else:
            c_status, c_job_name, c_progress = collect_current_print_data(ip, api_key)

        db_status = db_data[0]
        db_job_name = db_data[1]
        db_progress = db_data[2]
        db_stalled = db_data[5]
        db_stalled_notified = db_data[7]
        db_print_start_time = db_data[10]

        # Now that we have the data we will start doing our checks
        # First we will compare the DB vs Current and see if they are the same for state
        if c_status.lower() != db_status.lower():
            # The Status has changed. We should now figure out what to do.
            status_changed(conn, db_status, c_status, id, number, c_job_name, db_job_name, c_progress)

        # If the stats is printing. Then do stall checks
        if c_status.lower() == 'printing':
            job_progress = compare_progress(conn, id, db_progress, c_progress, ip)
            # if the job progress says same
            if job_progress == 'same':
                # was it same before
                if not db_stalled:
                    # if that database shows the print as not stalled, then set stalled
                    if datetime.datetime.strptime(db_print_start_time, '%Y-%m-%d %H:%M:%S.%f') + datetime.timedelta(minutes=5) <= datetime.datetime.now():
                        set_stalled(conn, id)
                    else:
                        print("Not Starting Stall time. First 5 min of the print.")
                elif db_stalled:
                    # If the database does show stalled preform stalled logic
                    stalled(conn, id, number)
            elif job_progress == 'different':
                # was it before
                if db_stalled:
                    # if the DB says it was stalled before, lets clear it now.
                    # But first was a notice sent, if so send a stall clear notice then clear the db.
                    if db_stalled_notified:
                        subject = "P{}, Recovered!".format(number)
                        discord_subject = "RECOVERED!!!"
                        message = "Printer {} has recovered from a stall!".format(number)
                        #send_email(subject, message)
                        send_discord_message(discord_subject, message, number, get_discord_url(id))
                    clear_stalled(conn, id)
                else:
                    # Just putting this here to be able to do something later.
                    pass
        elif c_status.lower() == "attention":
            if not db_stalled:
                set_stalled(conn, id)
                attention(conn, id, number)
        else:
            # Was it printing?
            # Should Notification be sent?
            pass


def create_session(printer):
    # print(printer)
    # print("Opening Session to {} which is a {} printer".format(printer['ip'], printer['model']))

    api_auth = ['mk3s+', 'mini+']
    user_pass_auth = ['mk4']

    s = requests.Session()
    if printer['model'] in user_pass_auth:
        s.auth = HTTPDigestAuth(printer['user'], printer['password'])
        s.headers.update({'Accept': 'application/json',
                          'Connection': 'keep-alive'
                          })
        return s
    elif printer['model'] in api_auth:
        s.headers.update({'Accept': 'application/json',
                          'Connection': 'keep-alive',
                          'X-Api-Key': printer['api_key']
                          })
        return s


def clean_up():
    db_file = './config/stats.db'
    conn = db_setup_connect(db_file)
    printers = get_all_printers(conn)

    for printer in printers:
        id = printer[0]
        sql = '''UPDATE state set printer_status = 'Unknown',
                                      job_name = 'none',
                                      progress = 0,
                                      stall_start = null,
                                      stalled = 0,
                                      stall_count = 0,
                                      stall_notified = 0,
                                      completed = 0,
                                      complete_notified = 0,
                                      started_notified = 0,
                                      print_start_time = null WHERE id = {}'''.format(id)
        cur = conn.cursor()
        cur.execute(sql)
        conn.commit()

def main(conn):
    monitor_prints(conn)


# def test(conn):
#     #print_started(conn, 1, 1, 'Printing', "TEST", "0.0000")
#     #set_stalled(conn, 1)
#     clear_stalled(conn, 1)
#     stalled(conn, 1, '192.168.1.201', "07DD84BBBD1F46B884F37C75F5780A7B")
#     exit(0)


if __name__ == '__main__':
    clean_up()

    while True:
        db_file = './config/stats.db'
        conn = db_setup_connect(db_file)
        print("-------------------------------")
        print(datetime.datetime.now())
        print("-------------------------------")
        main(conn)
        # test(conn)
        conn.close()
        time.sleep(10)
