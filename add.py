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
    duration TEXT NOT NULL
)
''')

# 插入数据的函数
def insert_meeting(name, date, start_time, end_time):
    # 计算持续时间
    start_dt = datetime.strptime(start_time, '%H:%M')
    end_dt = datetime.strptime(end_time, '%H:%M')
    duration = end_dt - start_dt
    #之后25年了把这个改成2025
    date_2024='2024-'+str(date)

    # 插入数据
    cursor.execute('''
    INSERT INTO meeting_times (name, date, start_time, end_time, duration)
    VALUES (?, ?, ?, ?, ?)
    ''', (name, date_2024, start_time, end_time, str(duration)))

    # 提交事务
    conn.commit()


# GUI应用程序
class MeetingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Meeting Time Tracker")

        # 输入框
        self.name_label = Label(root, text="Name")
        self.name_label.grid(row=0, column=0)
        self.name_entry = Entry(root)
        self.name_entry.grid(row=0, column=1)

        self.date_label = Label(root, text="Date (MM-DD)")
        self.date_label.grid(row=1, column=0)
        self.date_entry = Entry(root)
        self.date_entry.grid(row=1, column=1)

        self.start_time_label = Label(root, text="Start Time (HH:MM)")
        self.start_time_label.grid(row=2, column=0)
        self.start_time_entry = Entry(root)
        self.start_time_entry.grid(row=2, column=1)

        self.end_time_label = Label(root, text="End Time (HH:MM)")
        self.end_time_label.grid(row=3, column=0)
        self.end_time_entry = Entry(root)
        self.end_time_entry.grid(row=3, column=1)

        # 按钮
        self.add_button = Button(root, text="Add Meeting", command=self.add_meeting)
        self.add_button.grid(row=4, column=0, columnspan=2)


    def add_meeting(self):
        name = self.name_entry.get()
        date = self.date_entry.get()
        start_time = self.start_time_entry.get()
        end_time = self.end_time_entry.get()

        if name and date and start_time and end_time:
            insert_meeting(name, date, start_time, end_time)
            messagebox.showinfo("Success", "Meeting added successfully!")
            self.clear_entries()
        else:
            messagebox.showwarning("Input Error", "Please fill all fields")


    def clear_entries(self):
        self.name_entry.delete(0, END)
        # self.date_entry.delete(0, END)
        self.start_time_entry.delete(0, END)
        self.end_time_entry.delete(0, END)

# 创建主窗口
root = Tk()
app = MeetingApp(root)
root.mainloop()

# 关闭数据库连接
conn.close()