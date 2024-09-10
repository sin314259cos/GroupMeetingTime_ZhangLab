import sqlite3
from datetime import datetime
from tkinter import *
from tkinter import messagebox

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
    duration TEXT NOT NULL,
    question_time TEXT,
    question_duration TEXT
)
''')

# 插入数据的函数
def insert_meeting(name, date, start_time, end_time, question_time):
    # 计算持续时间
    start_dt = datetime.strptime(start_time, '%H:%M')
    end_dt = datetime.strptime(end_time, '%H:%M')
    duration = end_dt - start_dt

    # 计算提问时间
    question_dt = datetime.strptime(question_time, '%H:%M')
    question_duration = question_dt - end_dt

    # 将日期改为2024年
    date_2024 = '2024-' + str(date)

    # 插入数据
    cursor.execute('''
    INSERT INTO meeting_times (name, date, start_time, end_time, duration, question_time, question_duration)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (name, date_2024, start_time, end_time, str(duration), question_time, str(question_duration)))

    # 提交事务
    conn.commit()

# GUI应用程序
class MeetingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Meeting Time Tracker")

        # 输入框
        self.name_label = Label(root, text="Name, e.g. zz")
        self.name_label.grid(row=0, column=0)
        self.name_entry = Entry(root)
        self.name_entry.grid(row=0, column=1)

        self.date_label = Label(root, text="Date (MM-DD), e.g. 10-01")
        self.date_label.grid(row=1, column=0)
        self.date_entry = Entry(root)
        self.date_entry.grid(row=1, column=1)

        self.start_time_label = Label(root, text="Start Time (HH:MM), e.g.18:00")
        self.start_time_label.grid(row=2, column=0)
        self.start_time_entry = Entry(root)
        self.start_time_entry.grid(row=2, column=1)

        self.end_time_label = Label(root, text="End Time (HH:MM), e.g.18:20")
        self.end_time_label.grid(row=3, column=0)
        self.end_time_entry = Entry(root)
        self.end_time_entry.grid(row=3, column=1)

        self.question_time_label = Label(root, text="Question Time (HH:MM), e.g.18:40")
        self.question_time_label.grid(row=4, column=0)
        self.question_time_entry = Entry(root)
        self.question_time_entry.grid(row=4, column=1)

        # 按钮
        self.add_button = Button(root, text="Add Meeting", command=self.add_meeting)
        self.add_button.grid(row=5, column=0, columnspan=2)

    def add_meeting(self):
        name = self.name_entry.get()
        date = self.date_entry.get()
        start_time = self.start_time_entry.get()
        end_time = self.end_time_entry.get()
        question_time = self.question_time_entry.get()

        if name and date and start_time and end_time and question_time:
            insert_meeting(name, date, start_time, end_time, question_time)
            messagebox.showinfo("Success", "Meeting added successfully!")
            self.clear_entries()
        else:
            messagebox.showwarning("Input Error", "Please fill all fields")

    def clear_entries(self):
        self.name_entry.delete(0, END)
        # self.date_entry.delete(0, END)
        self.start_time_entry.delete(0, END)
        self.end_time_entry.delete(0, END)
        self.question_time_entry.delete(0, END)

# 创建主窗口
root = Tk()
app = MeetingApp(root)
root.mainloop()

# 关闭数据库连接
conn.close()
