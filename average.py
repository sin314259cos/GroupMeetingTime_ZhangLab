'''
统计每个人的平均组会时间
'''
import sqlite3
from datetime import datetime, timedelta

# 连接到SQLite数据库
conn = sqlite3.connect('meeting_times.db')
cursor = conn.cursor()

# 查询每个人的平均持续时间和计入统计的次数
def get_average_durations():
    cursor.execute('''
    SELECT name, COUNT(*) as count, AVG(
        (julianday(end_time) - julianday(start_time)) * 24 * 60 * 60
    ) as avg_duration
    FROM meeting_times
    GROUP BY name
    ORDER BY avg_duration DESC
    ''')
    return cursor.fetchall()

# 打印每个人的平均持续时间和计入统计的次数
def print_average_durations():
    average_durations = get_average_durations()
    if average_durations:
        print("Average Meeting Durations (from longest to shortest):")
        for name, count, avg_duration in average_durations:
            avg_duration_td = timedelta(seconds=avg_duration)
            print(f"Name: {name}, Average Duration: {avg_duration_td}, Count: {count}")
    else:
        print("No meeting records found.")

# 查询并打印每个人的平均持续时间和计入统计的次数
print_average_durations()

# 关闭数据库连接
conn.close()