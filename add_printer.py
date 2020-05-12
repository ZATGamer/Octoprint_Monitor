from print_stall import db_setup, db_setup_connect


if __name__ == '__main__':
    db_file = './stats.db'
    conn = db_setup_connect(db_file)

    ip = input("What is the Printers IP?: ")
    number = input("What is the Printer Number?: ")
    api_key = input("What is the API Key?: ")
    data = (number, ip, api_key)
    sql = """ INSERT INTO state (printer_number, printer_ip, printer_api_key) VALUES(?,?,?); """
    cur = conn.cursor()
    cur.execute(sql, data)
    conn.commit()
    conn.close()