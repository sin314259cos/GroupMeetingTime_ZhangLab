'''
对数据的组会时间进行排序
'''
import sqlite3

# 连接到SQLite数据库
conn = sqlite3.connect('meeting_times.db')
cursor = conn.cursor()

# 创建表（如果不存在）
cursor.execute('''
CREATE TABLE IF NOT EXISTS meeting_times (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    date TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    duration TEXT NOT NULL
)
''')

# 查询并排序所有数据
def get_sorted_meetings():
    cursor.execute('''
    SELECT * FROM meeting_times
    ORDER BY date ASC, start_time ASC
    ''')
    return cursor.fetchall()

# 创建一个新的表并插入排序后的数据
def create_sorted_table():
    # 创建一个临时表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS meeting_times_sorted (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        date TEXT NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        duration TEXT NOT NULL
    )
    ''')
    
    # 获取排序后的数据
    sorted_meetings = get_sorted_meetings()
    
    # 插入排序后的数据到临时表
    for meeting in sorted_meetings:
        cursor.execute('''
        INSERT INTO meeting_times_sorted (name, date, start_time, end_time, duration)
        VALUES (?, ?, ?, ?, ?)
        ''', (meeting[1], meeting[2], meeting[3], meeting[4], meeting[5]))
    
    # 提交事务
    conn.commit()

    # 删除旧表
    cursor.execute('DROP TABLE meeting_times')
    
    # 重命名新表
    cursor.execute('ALTER TABLE meeting_times_sorted RENAME TO meeting_times')
    
    # 提交事务
    conn.commit()

# 打印所有排序后的数据
def print_sorted_meetings():
    meetings = get_sorted_meetings()
    if meetings:
        print("Sorted Meetings by Date and Start Time:")
        for meeting in meetings:
            print(f"ID: {meeting[0]}, Name: {meeting[1]}, Date: {meeting[2]}, Start Time: {meeting[3]}, End Time: {meeting[4]}, Duration: {meeting[5]}")
    else:
        print("No meeting records found.")

# 创建排序后的表并更新数据库
create_sorted_table()

# 查询并打印所有排序后的数据
print_sorted_meetings()

# 关闭数据库连接
conn.close()