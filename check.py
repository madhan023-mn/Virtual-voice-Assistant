import sqlite3
c = sqlite3.connect('users.db')
print(c.execute('SELECT sql FROM sqlite_master WHERE type="table"').fetchall())
