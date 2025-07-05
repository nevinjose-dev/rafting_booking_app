import sqlite3

conn = sqlite3.connect('bookings.db')
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    phone TEXT,
    booking_date TEXT,
    trip_date TEXT,
    slot_time TEXT,
    raft_no INTEGER,
    group_size INTEGER,
    status TEXT
)
""")

sample_bookings = [
    ("Nevin", "9876543210", "2025-07-04", "2025-07-14", "7:00 AM", 1, 5, "Confirmed"),
    ("Sherin", "9876543211", "2025-07-04", "2025-07-14", "7:00 AM", 2, 6, "Confirmed"),
    ("John", "9876543212", "2025-07-04", "2025-07-14", "7:00 AM", 5, 6, "Confirmed"),
    ("Arjun", "9876543213", "2025-07-04", "2025-07-14", "10:00 AM", 1, 5, "Confirmed"),
    ("Anu", "9876543214", "2025-07-04", "2025-07-14", "10:00 AM", 5, 6, "Confirmed"),
    ("Liya", "9876543215", "2025-07-04", "2025-07-14", "1:00 PM", 3, 7, "Confirmed"),
    ("Rahul", "9876543216", "2025-07-04", "2025-07-14", "3:30 PM", 2, 6, "Confirmed"),
    ("Nevin", "9876543217", "2025-07-04", "2025-07-15", "7:00 AM", 1, 7, "Confirmed")
]

cursor.executemany("""
INSERT INTO bookings (name, phone, booking_date, trip_date, slot_time, raft_no, group_size, status)
VALUES (?, ?, ?, ?, ?, ?, ?, ?)
""", sample_bookings)

conn.commit()
conn.close()
print("Database created and sample data inserted.")