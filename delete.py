import sqlite3
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

# 查询所有数据
def get_all_meetings():
    cursor.execute('SELECT * FROM meeting_times ORDER BY date ASC, start_time ASC')
    return cursor.fetchall()

# 删除特定条目的函数
def delete_meeting(meeting_id):
    cursor.execute('DELETE FROM meeting_times WHERE id = ?', (meeting_id,))
    conn.commit()

# GUI应用程序
class MeetingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Meeting Time Tracker")

        # 创建Listbox来显示条目
        self.meeting_listbox = Listbox(root, width=100, height=20)
        self.meeting_listbox.grid(row=0, column=0, columnspan=2)

        # 创建删除按钮
        self.delete_button = Button(root, text="Delete Selected Meeting", command=self.delete_selected_meeting)
        self.delete_button.grid(row=1, column=0, columnspan=2)

        # 加载并显示所有条目
        self.load_meetings()

    def load_meetings(self):
        self.meeting_listbox.delete(0, END)  # 清空Listbox
        meetings = get_all_meetings()
        for meeting in meetings:
            self.meeting_listbox.insert(END, f"ID: {meeting[0]}, Name: {meeting[1]}, Date: {meeting[2]}, Start Time: {meeting[3]}, End Time: {meeting[4]}, Duration: {meeting[5]}, Question Time: {meeting[6]}, Question Duration: {meeting[7]}")

    def delete_selected_meeting(self):
        selected_index = self.meeting_listbox.curselection()
        if selected_index:
            selected_meeting = self.meeting_listbox.get(selected_index)
            meeting_id = int(selected_meeting.split(",")[0].split(":")[1].strip())
            delete_meeting(meeting_id)
            messagebox.showinfo("Success", "Meeting deleted successfully!")
            self.load_meetings()
        else:
            messagebox.showwarning("Selection Error", "Please select a meeting to delete")

# 创建主窗口
root = Tk()
app = MeetingApp(root)
root.mainloop()

# 关闭数据库连接
conn.close()
