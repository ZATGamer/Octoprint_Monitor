#!/usr/bin/python3

from flask import Flask, render_template
from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, IntegerField
from discord_webhook import send_discord_message
import sqlite3
import json


app = Flask(__name__)

app.config['SECRET_KEY'] = 'ca0xbKZ0qJ4Lxcgw8c7SDujOv1hZ0q5k'

Bootstrap(app)

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
        discord_url = form.discord_url.data
        sql = """ INSERT INTO state (printer_number, printer_ip, printer_api_key, discord_url) VALUES(?,?,?,?); """
        data = (number, ip, api_key, discord_url)
        db_file = './config/stats.db'
        conn = sqlite3.connect(db_file)
        cur = conn.cursor()
        cur.execute(sql, data)
        conn.commit()
        conn.close()
        print(type(number))
        Subject = "Printer Added".format(number)
        message = "Printer {} has been added!".format(number)
        send_discord_message(Subject, message, number, discord_url)

    return render_template('index.html', form=form)


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
    discord_url = StringField('Discord Webhook URL:')
    submit = SubmitField('Submit')


class ConfigureDiscord(FlaskForm):
    url = StringField('Discord Webhook URL:')
    submit = SubmitField('Submit')


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=7070)