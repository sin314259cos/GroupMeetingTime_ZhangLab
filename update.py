import sqlite3

# 连接到SQLite数据库
conn = sqlite3.connect('meeting_times.db')
cursor = conn.cursor()

# 添加新的question_duration列
def add_question_duration_column():
    try:
        cursor.execute('ALTER TABLE meeting_times ADD COLUMN question_duration TEXT')
        conn.commit()
        print("Column 'question_duration' added successfully.")
    except sqlite3.OperationalError as e:
        print(f"Error: {e}")

# 更新现有数据的question_duration列
def update_question_duration():
    try:
        # 示例：将所有question_duration列设置为默认值 '00:00'
        cursor.execute('UPDATE meeting_times SET question_duration = "00:00"')
        conn.commit()
        print("Column 'question_duration' updated successfully.")
    except sqlite3.OperationalError as e:
        print(f"Error: {e}")

# 执行添加列和更新数据的操作
add_question_duration_column()
update_question_duration()

# 查询并打印所有数据，验证更新
cursor.execute('SELECT * FROM meeting_times')
rows = cursor.fetchall()
for row in rows:
    print(row)

# 关闭数据库连接
conn.close()
