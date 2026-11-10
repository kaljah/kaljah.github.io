import sqlite3

conn = sqlite3.connect("new/server/ghg_app.db")
c = conn.cursor()
c.execute("DELETE FROM emissions WHERE id=61483")
conn.commit()
print("Cleaned up test record 61483")
conn.close()
