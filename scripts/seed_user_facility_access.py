import sqlite3

conn = sqlite3.connect('new/server/ghg_app.db')
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS user_facility_access (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    facility_id INTEGER NOT NULL,
    role_at_facility VARCHAR(32) DEFAULT 'operator',
    created_at DATETIME,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(facility_id) REFERENCES facilities(id) ON DELETE CASCADE,
    CONSTRAINT uq_user_facility_access UNIQUE (user_id, facility_id)
);
''')

cursor.execute('CREATE INDEX IF NOT EXISTS ix_user_facility_access_user_id ON user_facility_access(user_id);')
cursor.execute('CREATE INDEX IF NOT EXISTS ix_user_facility_access_facility_id ON user_facility_access(facility_id);')

users = cursor.execute('SELECT id, email, role FROM users WHERE email IN (?, ?)', 
                       ('audit_superuser@ghg.com', 'audit_operator@ghg.com')).fetchall()
print('Found users:', users)

for u_id, email, role in users:
    fac_role = 'verifier' if role == 'superuser' else 'operator'
    for f_id in [37, 38]:
        cursor.execute('''
            INSERT OR IGNORE INTO user_facility_access (user_id, facility_id, role_at_facility, created_at)
            VALUES (?, ?, ?, datetime('now'))
        ''', (u_id, f_id, fac_role))

conn.commit()

rows = cursor.execute('''
    SELECT u.email, f.name, a.role_at_facility 
    FROM user_facility_access a 
    JOIN users u ON a.user_id = u.id 
    JOIN facilities f ON a.facility_id = f.id
''').fetchall()
print('Seeded UserFacilityAccess records:')
for r in rows:
    print(' ', r)
