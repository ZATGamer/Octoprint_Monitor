# This will watch Octoprint for a print that has stalled. This will likely indicate a MMU Failure.

import requests
import time
import json
import sqlite3
import os
import datetime
from email_notification import send_notification


def get_all_printers(conn):
    # Get all printers out of the database to check
    cur = conn.cursor()
    sql = '''SELECT id, printer_number, printer_ip, printer_api_key FROM state'''
    printers = cur.execute(sql)
    printers = printers.fetchall()
    return printers


def compare_progress(conn, id, last, current):
    # For the printer supplied, dig out past data from the database and then current data from Octoprint

    print("Last Progress: {}\nCurrent Progress: {}".format(last, current))

    if current != last:
        # Update last to current
        print("DIFFERENT")
        update_last_progress(conn, id, current)
        return 'different'
    else:
        # Print Stalled?
        print("SAME?")
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
                              complete_notified = 0 WHERE id = {}'''.format(printer_state, job_name, job_progress, id)

    cur.execute(sql)
    conn.commit()
    # Send a start notice
    subject = "P{}, Job Started".format(p_number)
    message = "Printer {} has started printing of {}.".format(p_number, job_name)
    message_sent = send_notification(subject, message)
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
    message = "Printer {} has completed printing of {}.".format(p_number, job_name)
    message_sent = send_notification(subject, message)
    # If the message success sent
    if message_sent:
        notified_sql = '''UPDATE state set complete_notified = 1 where id = {}'''.format(id)
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


def stalled(conn, printer_id):
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
            subject = "P{}, Stalled".format(printer_id)
            message = "P{} Appears to of stalled during the print.".format(printer_id)
            message_sent = send_notification(subject, message)
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
                                    started_notified
                                ); """
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute(sql_create_state_table)
    conn.commit()
    conn.close()


def db_setup_connect(db_file):
    if not os.path.exists(db_file):
        db_setup(db_file)

    return sqlite3.connect(db_file)


def collect_current_print_data(ip, api_key):
    url = 'http://{}/api/job'.format(ip)
    headers = {"X-Api-Key": api_key}
    try:
        r_data = requests.get(url, headers=headers)
        j_data = json.loads(r_data.content)
        printer_status = j_data['state']
        job_name = j_data['job']['file']['name']
        progress = j_data['progress']['completion']
        return printer_status, job_name, progress
    except OSError:
        print("Printer {} Unreachable.".format(ip))
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
                            started_notified FROM state WHERE id = {}'''.format(id)
    cur = conn.cursor()
    last_state = cur.execute(sql)
    last_state = last_state.fetchone()
    return last_state


def status_changed(conn, db_status, c_status, id, number, c_job_name, db_job_name, c_progress):
    if db_status != 'Printing' and c_status == 'Printing':
        # Print Started
        print_started(conn, id, number, c_status, c_job_name, c_progress)
        print("Print Started")
    elif db_status == 'Printing' and c_status != 'Printing':
        # Print Completed
        print_completed(conn, id, number, c_status, db_job_name)
        print("Completed")
    else:
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
        # First thing to do is collect the data from the DB and from the Printer to run compares on.
        # DB Data
        db_data = collect_last_print_data(id)
        c_status, c_job_name, c_progress = collect_current_print_data(ip, api_key)

        db_status = db_data[0]
        db_job_name = db_data[1]
        db_progress = db_data[2]
        db_stalled = db_data[5]

        # Now that we have the data we will start doing our checks
        # First we will compare the DB vs Current and see if they are the same for state
        if c_status != db_status:
            # The Status has changed. We should now figure out what to do.
            status_changed(conn, db_status, c_status, id, number, c_job_name, db_job_name, c_progress)

        # If the stats is printing. Then do stall checks
        if c_status == 'Printing':
            job_progress = compare_progress(conn, id, db_progress, c_progress)
            # if the job progress says same
            if job_progress == 'same':
                # was it same before
                if not db_stalled:
                    # if that database shows the print as not stalled, then set stalled
                    set_stalled(conn, id)
                elif db_stalled:
                    # If the database does show stalled preform stalled logic
                    stalled(conn, id)
            elif job_progress == 'different':
                # was it before
                if db_stalled:
                    # if the DB says it was stalled before, lets clear it now.
                    clear_stalled(conn, id)
                else:
                    # Just putting this here to be able to do something later.
                    pass

        else:
            # Was it printing?
            # Should Notification be sent?
            pass


def main(conn):
    monitor_prints(conn)


def test(conn):
    #print_started(conn, 1, 1, 'Printing', "TEST", "0.0000")
    #set_stalled(conn, 1)
    clear_stalled(conn, 1)
    stalled(conn, 1, '192.168.1.201', "07DD84BBBD1F46B884F37C75F5780A7B")
    exit(0)


if __name__ == '__main__':
    while True:
        db_file = './stats.db'
        conn = db_setup_connect(db_file)

        print("-------------------------------")
        main(conn)
        # test(conn)
        conn.close()
        time.sleep(10)
