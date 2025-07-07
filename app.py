from flask import Flask, render_template, request, redirect, url_for, jsonify, make_response
from datetime import datetime, date as dt_date
import sqlite3, os, csv

app = Flask(__name__)

# Utility for smart group splitting
def smart_split(group_size, ideal_sizes=[6, 5]):
    result = []

    def backtrack(remain, path):
        if remain == 0:
            result.append(path[:])
            return
        for choice in ideal_sizes:
            if choice <= remain:
                path.append(choice)
                backtrack(remain - choice, path)
                path.pop()

    backtrack(group_size, [])
    if result:
        result.sort(key=lambda x: (len(x), -sum(sorted(x, reverse=True))))
        return result[0]
    else:
        return [group_size]

# DB Setup
def init_db():
    os.makedirs("database", exist_ok=True)
    conn = sqlite3.connect('database/booking.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, phone TEXT, place TEXT, date TEXT, slot TEXT,
        people INTEGER, raft_no INTEGER, advance INTEGER, total INTEGER, status TEXT, booking_time TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS locked_slots (
        id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, slot TEXT, reason TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS raft_assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT, booking_id INTEGER, raft_no INTEGER, people INTEGER
    )''')
    conn.commit()
    conn.close()

@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/book-now')
def booking_form():
    return render_template('index.html')

@app.route('/book', methods=['POST'])
def book():
    name = request.form['name']
    phone = request.form['phone']
    place = request.form['place']
    date = request.form['date']
    slot = request.form['slot']
    people = int(request.form['people'])

    if people < 5:
        return "❌ Minimum group size is 5."
    if people > 30:
        return "❌ Group too large! You will be split into two time slots."
    if datetime.strptime(date, '%Y-%m-%d').date() <= dt_date.today():
        return "❌ Booking date must be in the future."

    conn = sqlite3.connect('database/booking.db')
    c = conn.cursor()

    c.execute("SELECT * FROM locked_slots WHERE date=? AND slot=?", (date, slot))
    if c.fetchone():
        conn.close()
        return "❌ This slot is locked by admin."

    c.execute("SELECT SUM(people) FROM bookings WHERE date=? AND slot=? AND status='confirmed'", (date, slot))
    already = c.fetchone()[0] or 0
    if already + people > 30:
        return f"❌ Only {30 - already} seat(s) left for {slot} on {date}."

    c.execute("""
        SELECT ra.raft_no, SUM(ra.people) 
        FROM raft_assignments ra
        JOIN bookings b ON ra.booking_id = b.id
        WHERE b.date=? AND b.slot=? AND b.status='confirmed'
        GROUP BY ra.raft_no
    """, (date, slot))
    current = {i: 0 for i in range(1, 6)}
    for raft_no, count in c.fetchall():
        current[raft_no] = count

    assignments = []
    splits = smart_split(people)

    for group_size in splits:
        found = False
        for raft_id in sorted(current, key=lambda r: current[r]):
            if current[raft_id] + group_size <= 6 and current[raft_id] not in [5, 6]:
                assignments.append((group_size, raft_id))
                current[raft_id] += group_size
                found = True
                break
        if not found:
            conn.close()
            return f"❌ Cannot allocate {group_size} members due to raft limits. Try another slot."

    # Pricing
    is_weekend = datetime.strptime(date, '%Y-%m-%d').weekday() in [5, 6]
    rate = 1400 if is_weekend else 1300
    total = people * rate
    advance = (people * 1400) // 2 if is_weekend else 1000 if people <= 6 else 2000 if people <= 12 else 3000

    booking_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    c.execute("""INSERT INTO bookings 
                 (name, phone, place, date, slot, people, raft_no, advance, total, status, booking_time) 
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
              (name, phone, place, date, slot, people, assignments[0][1], advance, total, 'confirmed', booking_time))
    booking_id = c.lastrowid

    for p, r in assignments:
        c.execute("INSERT INTO raft_assignments (booking_id, raft_no, people) VALUES (?, ?, ?)", (booking_id, r, p))

    conn.commit()
    conn.close()

    return render_template("confirmation.html",
        booking_id=booking_id,
        name=name,
        phone=phone,
        date=date,
        slot=slot,
        total=total,
        advance=advance,
        remaining=total - advance,
        raft_assignments=assignments
    )

@app.route('/admin')
def admin():
    conn = sqlite3.connect('database/booking.db')
    c = conn.cursor()
    c.execute("SELECT * FROM bookings")
    bookings = c.fetchall()

    c.execute("""
        SELECT b.date, b.slot, ra.raft_no, SUM(ra.people)
        FROM bookings b
        JOIN raft_assignments ra ON b.id = ra.booking_id
        WHERE b.status='confirmed'
        GROUP BY b.date, b.slot, ra.raft_no
    """)
    rows = c.fetchall()
    summary_table = {}

    for d, s, r, p in rows:
        key = (d, s)
        if key not in summary_table:
            summary_table[key] = {i: 0 for i in range(1, 6)}
            summary_table[key]['total'] = 0
        summary_table[key][r] = p
        summary_table[key]['total'] += p

    conn.close()
    return render_template('admin.html', bookings=bookings, summary_table=summary_table)

@app.route('/cancel/<int:booking_id>')
def cancel(booking_id):
    conn = sqlite3.connect('database/booking.db')
    c = conn.cursor()
    c.execute("UPDATE bookings SET status='cancelled' WHERE id=?", (booking_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

@app.route('/delete/<int:booking_id>', methods=['POST'])
def delete_booking(booking_id):
    conn = sqlite3.connect('database/booking.db')
    c = conn.cursor()
    c.execute("DELETE FROM raft_assignments WHERE booking_id=?", (booking_id,))
    c.execute("DELETE FROM bookings WHERE id=? AND status='cancelled'", (booking_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

@app.route('/edit/<int:booking_id>', methods=['GET', 'POST'])
def edit_booking(booking_id):
    conn = sqlite3.connect('database/booking.db')
    c = conn.cursor()

    if request.method == 'POST':
        people = int(request.form['people'])
        raft_no = request.form['raft']
        total = int(request.form['remaining'])

        c.execute("UPDATE bookings SET people=?, raft_no=?, total=?, status='edited' WHERE id=?",
                  (people, raft_no, total, booking_id))

        c.execute("DELETE FROM raft_assignments WHERE booking_id=?", (booking_id,))
        c.execute("INSERT INTO raft_assignments (booking_id, raft_no, people) VALUES (?, ?, ?)",
                  (booking_id, raft_no, people))

        conn.commit()
        conn.close()
        return redirect(url_for('admin'))

    booking = c.execute("SELECT * FROM bookings WHERE id=?", (booking_id,)).fetchone()
    conn.close()
    return render_template('edit.html', booking=booking)
@app.route('/reset-db')
def reset_db():
    try:
        os.remove('database/booking.db')
        init_db()
        return "✅ Database reset successful."
    except Exception as e:
        return f"❌ Error: {e}"


@app.route('/remaining-seats', methods=['POST'])
def remaining_seats():
    data = request.get_json()
    date = data['date']
    slot = data['slot']

    conn = sqlite3.connect('database/booking.db')
    c = conn.cursor()
    c.execute("""
        SELECT ra.raft_no, SUM(ra.people)
        FROM bookings b
        JOIN raft_assignments ra ON b.id = ra.booking_id
        WHERE b.date=? AND b.slot=? AND b.status='confirmed'
        GROUP BY ra.raft_no
    """, (date, slot))
    rafts = c.fetchall()
    conn.close()

    current = {i: 0 for i in range(1, 6)}
    for raft_no, count in rafts:
        current[raft_no] = count

    remaining = 0
    for count in current.values():
        if count == 0:
            remaining += 6
        elif count < 5:
            remaining += (6 - count)

    return jsonify({'remaining': remaining})

@app.route('/export-bookings')
def export_bookings():
    conn = sqlite3.connect('database/booking.db')
    c = conn.cursor()
    c.execute("SELECT * FROM bookings")
    bookings = c.fetchall()
    conn.close()

    output = []
    header = ['ID', 'Name', 'Phone', 'Place', 'Date', 'Slot', 'People', 'Raft No', 'Advance', 'Total', 'Status', 'Booking Time']
    output.append(header)

    for row in bookings:
        output.append([str(item) for item in row])

    si = '\n'.join([','.join(line) for line in output])
    response = make_response(si)
    response.headers["Content-Disposition"] = "attachment; filename=bookings.csv"
    response.headers["Content-type"] = "text/csv"
    return response

import sys

if __name__ == '__main__':
    if 'init-only' in sys.argv:
        init_db()
        print("✅ Database initialized and exited.")
    else:
        init_db()
        app.run(debug=True)
