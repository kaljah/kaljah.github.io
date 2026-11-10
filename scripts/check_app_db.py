import sqlite3

conn = sqlite3.connect("new/server/ghg_app.db")
c = conn.cursor()
print("System Settings:")
for r in c.execute("SELECT * FROM system_settings").fetchall():
    print(" ", r)

print("\nUsers GWP preference:")
for r in c.execute("SELECT id, email, preferences FROM users WHERE id=1").fetchall():
    print(" ", r)

conn.close()
