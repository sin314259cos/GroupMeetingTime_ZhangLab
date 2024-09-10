import sqlite3
from datetime import datetime, timedelta

# 连接到SQLite数据库
conn = sqlite3.connect('meeting_times.db')
cursor = conn.cursor()

# 查询并计算每个人的平均duration和question_time
def get_average_durations_and_question_times(start_date, end_date):
    cursor.execute('''
    SELECT name,
           AVG((julianday(end_time) - julianday(start_time)) * 24 * 60 * 60) AS avg_duration,
           AVG((julianday(question_time) - julianday(end_time)) * 24 * 60 * 60) AS avg_question_time
    FROM meeting_times
    WHERE date BETWEEN ? AND ?
    GROUP BY name
    ''', (start_date, end_date))
    return cursor.fetchall()

# 按duration排序
def sort_by_duration(data):
    return sorted(data, key=lambda x: x[1], reverse=True)

# 按duration + question_time排序
def sort_by_total_time(data):
    return sorted(data, key=lambda x: x[1] + x[2], reverse=True)

# 打印结果
def print_results(data, title):
    print(title)
    for row in data:
        name, avg_duration, avg_question_time = row
        avg_duration_td = timedelta(seconds=avg_duration)
        avg_question_time_td = timedelta(seconds=avg_question_time)
        avg_total_time_td = timedelta(seconds=avg_duration+ avg_question_time) 
        print(f"Name: {name}, Average Duration: {avg_duration_td}, Average Question Time: {avg_question_time_td}, Average Question Time: {avg_total_time_td}")
    print()

# 主函数
def main():
    start_date = '2024-08-25'
    end_date = '2024-09-08'

    data = get_average_durations_and_question_times(start_date, end_date)

    sorted_by_duration = sort_by_duration(data)
    sorted_by_total_time = sort_by_total_time(data)

    print_results(sorted_by_duration, "Sorted by Average Duration")
    print_results(sorted_by_total_time, "Sorted by Average Duration + Question Time")

# 执行主函数
if __name__ == "__main__":
    main()

# 关闭数据库连接
conn.close()
