import sqlite3

conn = sqlite3.connect("new/server/ghg_app.db")
c = conn.cursor()
c.execute("UPDATE system_settings SET value='\"AR4\"' WHERE key='gwp_standard'")
conn.commit()
print("GWP standard updated to AR4 in system_settings")
conn.close()
