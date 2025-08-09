import sqlite3
import pandas as pd

conn = sqlite3.connect('data/hr.db')
df = pd.read_sql_query("SELECT * FROM audit_logs ORDER BY timestamp DESC", conn)
print(df.to_string(index=False))
conn.close()
df = pd.read_sql_query("""
SELECT a.id, a.action, a.user_id, u.username, u.name, a.obj_type, a.obj_id, a.note, a.timestamp
FROM audit_logs a
LEFT JOIN users u ON a.user_id = u.id
ORDER BY a.timestamp DESC
""", conn)
