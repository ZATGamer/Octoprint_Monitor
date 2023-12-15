#!/usr/bin/python3

from flask import Flask, render_template, flash
from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, IntegerField, SelectField
from discord_webhook import send_discord_message
import sqlite3
import json


app = Flask(__name__)

app.config['SECRET_KEY'] = 'ca0xbKZ0qJ4Lxcgw8c7SDujOv1hZ0q5k'

Bootstrap(app)

@app.route('/', methods=['GET'])
def homepage():
    # lets create a home page with some basic links to the other parts of the app.
    pass


@app.route('/info', methods=['GET'])
def main():
    # Connect to the database
    db_file = './config/stats.db'
    conn = sqlite3.connect(db_file)

    # Do the query
    sql = '''SELECT printer_status, 
                    job_name,
                    progress,
                    completed,
                    stall_start,
                    stalled,
                    stall_count,
                    stall_notified,
                    complete_notified, 
                    started_notified FROM state'''
    cur = conn.cursor()
    last_state = cur.execute(sql)
    last_state = last_state.fetchall()

    # Convert to json
    last_state = json.dumps(last_state)
    conn.close()
    # Return It
    return last_state, 200


@app.route('/add_printer', methods=['GET', 'POST'])
def add_printer():
    form = AddPrinterForm()
    if form.validate_on_submit():
        number = form.number.data
        ip = form.ip.data
        api_key = form.api_key.data
        printer_user = form.printer_user.data
        printer_password = form.printer_password.data
        printer_model = form.printer_model.data
        discord_url = form.discord_url.data
        sql = """ INSERT INTO state (printer_number, printer_ip, printer_api_key, discord_url, printer_user, printer_password, model, printer_status) VALUES(?,?,?,?,?,?,?,?); """
        data = (number, ip, api_key, discord_url, printer_user, printer_password, printer_model, "FIRST")
        db_file = './config/stats.db'
        conn = sqlite3.connect(db_file)
        cur = conn.cursor()
        cur.execute(sql, data)
        conn.commit()
        conn.close()
        # print(type(number))
        subject = "Printer Added".format(number)
        message = "Printer {} has been added!".format(number)
        send_discord_message(subject, message, number, discord_url)

    return render_template('index.html', form=form)


@app.route('/delete_printer', methods=['GET', 'POST'])
def delete_printer():
    form = DeletePrintersForm()
    if form.validate_on_submit():
        printer_id = form.printer_id.data
        db_file = './config/stats.db'
        conn = sqlite3.connect(db_file)
        cur = conn.cursor()

        get_notification = '''SELECT discord_url FROM state WHERE id = {}'''.format(printer_id)
        discord_url = cur.execute(get_notification)
        discord_url = discord_url.fetchone()[0]

        sql = ''' DELETE FROM state WHERE id = {}'''.format(printer_id)
        cur.execute(sql)
        conn.commit()
        conn.close()

        subject = "Printer Removed"
        message = "Printer {} has been removed!".format(printer_id)
        send_discord_message(subject, message, printer_id, discord_url)

    return render_template('delete.html', form=form)


@app.route('/printers', methods=['GET'])
def list_printers():
    db_file = './config/stats.db'
    conn = sqlite3.connect(db_file)

    # Do the query
    sql = '''SELECT * FROM state'''
    cur = conn.cursor()
    last_state = cur.execute(sql)
    last_state = last_state.fetchall()

    # Convert to json
    last_state = json.dumps(last_state)
    conn.close()
    return last_state, 200


@app.route('/find_me', methods=['GET'])
def find_me():
    message = "FOUND ME!"
    return message, 200


@app.route('/discord', methods=['GET', 'POST'])
def config_discord():
    form = ConfigureDiscord()
    if form.validate_on_submit():
        url = form.url.data
        sql = """ INSERT INTO config  """
        data = (url)
        db_file = './config/stats.db'
        conn = sqlite3.connect(db_file)
        cur = conn.cursor()
        cur.execute(sql, data)
        conn.commit()
        conn.close()

    return render_template('index.html', form=form)


class AddPrinterForm(FlaskForm):
    number = IntegerField('Printer Number:')
    ip = StringField('Printer IP Address:')
    api_key = StringField('Printer API Key:')
    printer_user = StringField('Printer Username:')
    printer_password = StringField('Printer Password:')
    printer_model = SelectField('Printer Model:', choices=[('octo', 'Octoprint'),
                                                           ('mk4', 'Prusa Mk4'),
                                                           ('mk3s+', 'Prusa Mk3s+'),
                                                           ('mini+', 'Prusa Mini+')])
    discord_url = StringField('Discord Webhook URL:')
    submit = SubmitField('Submit')


class ConfigureDiscord(FlaskForm):
    url = StringField('Discord Webhook URL:')
    submit = SubmitField('Submit')


class DeletePrintersForm(FlaskForm):
    printer_id = IntegerField('Printer id:')
    submit = SubmitField('Submit')


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=7070)