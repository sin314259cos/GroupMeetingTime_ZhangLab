"""A fast, visual desktop interface for recording ZhangLab meeting times."""

from __future__ import annotations

import sqlite3
import tkinter as tk
from datetime import date, datetime, timedelta
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from meeting_store import (
    Meeting,
    MeetingRepository,
    ValidationError,
    elapsed_seconds,
    format_duration,
    format_minutes,
)


APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "meeting_times.db"

COLORS = {
    "bg": "#F3F0E8",
    "card": "#FFFDF8",
    "ink": "#1D2A31",
    "muted": "#68767A",
    "line": "#DDD8CC",
    "accent": "#D8664B",
    "accent_dark": "#B94D36",
    "green": "#277567",
    "green_dark": "#1E5C52",
    "soft_green": "#E4F0EC",
    "soft_orange": "#F8E9DF",
    "soft_blue": "#E6EDF0",
}


class MeetingTimerApp(tk.Tk):
    def __init__(self, repository: MeetingRepository):
        super().__init__()
        self.repository = repository
        self.title("ZhangLab · 组会时间台")
        self.geometry("1240x800")
        self.minsize(1050, 700)
        self.configure(bg=COLORS["bg"])

        self._configure_styles()
        self._build_header()
        self.notebook = ttk.Notebook(self, style="App.TNotebook")
        self.notebook.pack(fill="both", expand=True, padx=28, pady=(0, 24))

        self.register_tab = RegisterTab(self.notebook, self)
        self.history_tab = HistoryTab(self.notebook, self)
        self.stats_tab = StatsTab(self.notebook, self)
        self.notebook.add(self.register_tab, text="  快速登记  ")
        self.notebook.add(self.history_tab, text="  历史记录  ")
        self.notebook.add(self.stats_tab, text="  统计概览  ")

        self.bind("<Control-s>", lambda _event: self.register_tab.save())
        self.bind("<Control-S>", lambda _event: self.register_tab.save())
        self.bind("<F5>", lambda _event: self.refresh_all())
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(120, self.refresh_all)

    def _configure_styles(self) -> None:
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")

        default_font = ("Microsoft YaHei UI", 10)
        self.option_add("*Font", default_font)
        self.option_add("*TCombobox*Listbox.font", default_font)

        style.configure(".", background=COLORS["bg"], foreground=COLORS["ink"], font=default_font)
        style.configure("Card.TFrame", background=COLORS["card"], relief="flat")
        style.configure("Header.TFrame", background=COLORS["ink"])
        style.configure("Title.TLabel", background=COLORS["ink"], foreground="#FFFFFF", font=("Microsoft YaHei UI", 19, "bold"))
        style.configure("Subtitle.TLabel", background=COLORS["ink"], foreground="#BEC8C8", font=("Microsoft YaHei UI", 9))
        style.configure("Clock.TLabel", background=COLORS["ink"], foreground="#FFFFFF", font=("Consolas", 18, "bold"))
        style.configure("CardTitle.TLabel", background=COLORS["card"], foreground=COLORS["ink"], font=("Microsoft YaHei UI", 13, "bold"))
        style.configure("CardText.TLabel", background=COLORS["card"], foreground=COLORS["muted"], font=("Microsoft YaHei UI", 9))
        style.configure("BigTime.TLabel", background=COLORS["card"], foreground=COLORS["ink"], font=("Consolas", 30, "bold"))
        style.configure("Status.TLabel", background=COLORS["soft_green"], foreground=COLORS["green_dark"], padding=(10, 5), font=("Microsoft YaHei UI", 9, "bold"))
        style.configure("DangerStatus.TLabel", background=COLORS["soft_orange"], foreground=COLORS["accent_dark"], padding=(10, 5), font=("Microsoft YaHei UI", 9, "bold"))
        style.configure("Field.TLabel", background=COLORS["card"], foreground=COLORS["muted"], font=("Microsoft YaHei UI", 9))
        style.configure("Hint.TLabel", background=COLORS["card"], foreground=COLORS["muted"], font=("Microsoft YaHei UI", 8))
        style.configure("Metric.TLabel", background=COLORS["soft_blue"], foreground=COLORS["ink"], padding=(12, 8), font=("Microsoft YaHei UI", 10, "bold"))

        style.configure("Accent.TButton", background=COLORS["accent"], foreground="#FFFFFF", borderwidth=0, padding=(18, 11), font=("Microsoft YaHei UI", 10, "bold"))
        style.map("Accent.TButton", background=[("active", COLORS["accent_dark"]), ("disabled", "#C8B9B3")])
        style.configure("Green.TButton", background=COLORS["green"], foreground="#FFFFFF", borderwidth=0, padding=(18, 11), font=("Microsoft YaHei UI", 10, "bold"))
        style.map("Green.TButton", background=[("active", COLORS["green_dark"]), ("disabled", "#AFC0BC")])
        style.configure("Soft.TButton", background=COLORS["soft_blue"], foreground=COLORS["ink"], borderwidth=0, padding=(12, 8))
        style.map("Soft.TButton", background=[("active", "#D5E1E5")])
        style.configure("Danger.TButton", background=COLORS["soft_orange"], foreground=COLORS["accent_dark"], borderwidth=0, padding=(12, 8))
        style.map("Danger.TButton", background=[("active", "#F0D5C5")])

        style.configure("TEntry", fieldbackground="#FFFFFF", bordercolor=COLORS["line"], lightcolor=COLORS["line"], darkcolor=COLORS["line"], padding=8)
        style.configure("TCombobox", fieldbackground="#FFFFFF", bordercolor=COLORS["line"], padding=7)
        style.configure("Treeview", background="#FFFFFF", fieldbackground="#FFFFFF", foreground=COLORS["ink"], rowheight=34, borderwidth=0)
        style.configure("Treeview.Heading", background=COLORS["soft_blue"], foreground=COLORS["ink"], relief="flat", padding=(8, 9), font=("Microsoft YaHei UI", 9, "bold"))
        style.map("Treeview", background=[("selected", COLORS["green"])], foreground=[("selected", "#FFFFFF")])
        style.configure("App.TNotebook", background=COLORS["bg"], borderwidth=0)
        style.configure("App.TNotebook.Tab", background=COLORS["bg"], foreground=COLORS["muted"], borderwidth=0, padding=(18, 11), font=("Microsoft YaHei UI", 10, "bold"))
        style.map("App.TNotebook.Tab", background=[("selected", COLORS["card"])], foreground=[("selected", COLORS["ink"])])

    def _build_header(self) -> None:
        header = ttk.Frame(self, style="Header.TFrame", padding=(28, 18))
        header.pack(fill="x")
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="ZhangLab 组会时间台", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(header, text="现场计时、补录、查询与统计都在这里", style="Subtitle.TLabel").grid(row=1, column=0, sticky="w", pady=(3, 0))
        self.header_clock = ttk.Label(header, style="Clock.TLabel")
        self.header_clock.grid(row=0, column=1, rowspan=2, sticky="e")
        self._tick_clock()

    def _tick_clock(self) -> None:
        self.header_clock.configure(text=datetime.now().strftime("%H:%M:%S"))
        self.after(1000, self._tick_clock)

    def refresh_all(self) -> None:
        self.register_tab.refresh()
        self.history_tab.refresh()
        self.stats_tab.refresh()

    def edit_meeting(self, meeting: Meeting) -> None:
        self.register_tab.load_for_edit(meeting)
        self.notebook.select(self.register_tab)

    def _on_close(self) -> None:
        if self.register_tab.is_timing and not messagebox.askyesno(
            "计时尚未保存", "当前正在计时，确定关闭吗？未保存的时间会丢失。", parent=self
        ):
            return
        self.destroy()


class RegisterTab(ttk.Frame):
    def __init__(self, parent: ttk.Notebook, app: MeetingTimerApp):
        super().__init__(parent, padding=18, style="Card.TFrame")
        self.app = app
        self.repository = app.repository
        self.editing_id: int | None = None
        self.stage: str | None = None
        self.stage_started_at: datetime | None = None

        self.name_var = tk.StringVar()
        self.date_var = tk.StringVar(value=date.today().isoformat())
        self.start_var = tk.StringVar()
        self.end_var = tk.StringVar()
        self.question_var = tk.StringVar()
        self.preview_var = tk.StringVar(value="填写时间后自动计算时长")
        self.banner_var = tk.StringVar(value="准备登记")
        self.elapsed_var = tk.StringVar(value="00:00")
        self.edit_note_var = tk.StringVar()

        self.columnconfigure(0, weight=1, uniform="main")
        self.columnconfigure(1, weight=1, uniform="main")
        self.rowconfigure(0, weight=1)
        self._build_timer_card()
        self._build_form_card()
        for variable in (self.start_var, self.end_var, self.question_var):
            variable.trace_add("write", lambda *_args: self._update_preview())
        self.after(1000, self._tick_elapsed)

    @property
    def is_timing(self) -> bool:
        return self.stage in {"report", "question"}

    def _build_timer_card(self) -> None:
        card = ttk.Frame(self, style="Card.TFrame", padding=(22, 18))
        card.grid(row=0, column=0, sticky="nsew", padx=(0, 9))
        card.columnconfigure(0, weight=1)

        ttk.Label(card, text="现场计时", style="CardTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(card, text="按组会进程依次点击，最后一步会直接写入数据库", style="CardText.TLabel").grid(row=1, column=0, sticky="w", pady=(3, 14))
        self.status_label = ttk.Label(card, textvariable=self.banner_var, style="Status.TLabel")
        self.status_label.grid(row=2, column=0, sticky="w")
        ttk.Label(card, textvariable=self.elapsed_var, style="BigTime.TLabel").grid(row=3, column=0, sticky="w", pady=(12, 20))

        self.start_button = ttk.Button(card, text="1   开始报告", style="Green.TButton", command=self.start_report)
        self.start_button.grid(row=4, column=0, sticky="ew", pady=5)
        self.question_button = ttk.Button(card, text="2   报告结束 · 进入提问", style="Soft.TButton", command=self.start_questions)
        self.question_button.grid(row=5, column=0, sticky="ew", pady=5)
        self.finish_button = ttk.Button(card, text="3   提问结束 · 保存记录", style="Accent.TButton", command=self.finish_and_save)
        self.finish_button.grid(row=6, column=0, sticky="ew", pady=5)

        ttk.Separator(card).grid(row=7, column=0, sticky="ew", pady=18)
        ttk.Label(card, text="最近登记", style="CardTitle.TLabel").grid(row=8, column=0, sticky="w")
        self.recent_tree = ttk.Treeview(card, columns=("date", "name", "report", "question"), show="headings", height=6)
        headings = {"date": "日期", "name": "汇报人", "report": "报告", "question": "提问"}
        widths = {"date": 100, "name": 90, "report": 80, "question": 80}
        for key in headings:
            self.recent_tree.heading(key, text=headings[key])
            self.recent_tree.column(key, width=widths[key], anchor="center")
        self.recent_tree.grid(row=9, column=0, sticky="nsew", pady=(10, 0))
        card.rowconfigure(9, weight=1)

    def _build_form_card(self) -> None:
        card = ttk.Frame(self, style="Card.TFrame", padding=(22, 18))
        card.grid(row=0, column=1, sticky="nsew", padx=(9, 0))
        card.columnconfigure(0, weight=1)
        card.columnconfigure(1, weight=1)

        ttk.Label(card, text="登记信息", style="CardTitle.TLabel").grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(card, text="也可以直接填写时间，用于补录或修正记录", style="CardText.TLabel").grid(row=1, column=0, columnspan=2, sticky="w", pady=(3, 14))
        ttk.Label(card, textvariable=self.edit_note_var, style="DangerStatus.TLabel").grid(row=2, column=0, columnspan=2, sticky="w", pady=(0, 10))

        ttk.Label(card, text="汇报人", style="Field.TLabel").grid(row=3, column=0, sticky="w", padx=(0, 6))
        ttk.Label(card, text="组会日期", style="Field.TLabel").grid(row=3, column=1, sticky="w", padx=(6, 0))
        self.name_box = ttk.Combobox(card, textvariable=self.name_var)
        self.name_box.grid(row=4, column=0, sticky="ew", padx=(0, 6), pady=(4, 12))
        date_row = ttk.Frame(card, style="Card.TFrame")
        date_row.grid(row=4, column=1, sticky="ew", padx=(6, 0), pady=(4, 12))
        date_row.columnconfigure(0, weight=1)
        ttk.Entry(date_row, textvariable=self.date_var).grid(row=0, column=0, sticky="ew")
        ttk.Button(date_row, text="今天", style="Soft.TButton", command=lambda: self.date_var.set(date.today().isoformat())).grid(row=0, column=1, padx=(6, 0))

        self._time_field(card, 5, "报告开始", self.start_var, self.use_previous_end)
        self._time_field(card, 7, "报告结束 / 提问开始", self.end_var, lambda: self.set_now(self.end_var))
        self._time_field(card, 9, "提问结束", self.question_var, lambda: self.set_now(self.question_var))

        ttk.Label(card, textvariable=self.preview_var, style="Metric.TLabel").grid(row=11, column=0, columnspan=2, sticky="ew", pady=(10, 16))
        action_row = ttk.Frame(card, style="Card.TFrame")
        action_row.grid(row=12, column=0, columnspan=2, sticky="ew")
        action_row.columnconfigure(0, weight=1)
        action_row.columnconfigure(1, weight=1)
        ttk.Button(action_row, text="清空", style="Soft.TButton", command=self.clear_form).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.save_button = ttk.Button(action_row, text="保存记录  Ctrl+S", style="Accent.TButton", command=self.save)
        self.save_button.grid(row=0, column=1, sticky="ew", padx=(6, 0))
        ttk.Label(card, text="提示：如果没有提问环节，可将“提问结束”留空。", style="Hint.TLabel").grid(row=13, column=0, columnspan=2, sticky="w", pady=(12, 0))

    def _time_field(self, parent: ttk.Frame, row: int, label: str, variable: tk.StringVar, command) -> None:
        ttk.Label(parent, text=label, style="Field.TLabel").grid(row=row, column=0, columnspan=2, sticky="w")
        line = ttk.Frame(parent, style="Card.TFrame")
        line.grid(row=row + 1, column=0, columnspan=2, sticky="ew", pady=(4, 12))
        line.columnconfigure(0, weight=1)
        ttk.Entry(line, textvariable=variable, font=("Consolas", 12)).grid(row=0, column=0, sticky="ew")
        button_text = "接上位结束" if variable is self.start_var else "现在"
        ttk.Button(line, text=button_text, style="Soft.TButton", command=command).grid(row=0, column=1, padx=(6, 0))

    def set_now(self, variable: tk.StringVar) -> None:
        variable.set(datetime.now().strftime("%H:%M"))

    def use_previous_end(self) -> None:
        try:
            previous = self.repository.latest_end_time(self.date_var.get())
        except ValidationError as exc:
            messagebox.showwarning("日期有误", str(exc), parent=self)
            return
        if previous:
            self.start_var.set(previous)
            self._set_banner(f"已接续上一位的结束时间 {previous}")
        else:
            self.set_now(self.start_var)
            self._set_banner("当天还没有记录，已使用当前时间")

    def start_report(self) -> None:
        if not self.name_var.get().strip():
            messagebox.showwarning("请先选择汇报人", "现场计时前，请先选择或填写汇报人。", parent=self)
            self.name_box.focus_set()
            return
        self.set_now(self.start_var)
        self.end_var.set("")
        self.question_var.set("")
        self.stage = "report"
        self.stage_started_at = datetime.now()
        self._set_banner(f"{self.name_var.get().strip()} 正在汇报", active=True)

    def start_questions(self) -> None:
        if not self.start_var.get().strip():
            messagebox.showwarning("尚未开始", "请先点击“开始报告”，或手动填写报告开始时间。", parent=self)
            return
        self.set_now(self.end_var)
        self.stage = "question"
        self.stage_started_at = datetime.now()
        self._set_banner("报告结束，正在提问", active=True)

    def finish_and_save(self) -> None:
        if not self.end_var.get().strip():
            messagebox.showwarning("尚未进入提问", "请先点击“报告结束 · 进入提问”。", parent=self)
            return
        self.set_now(self.question_var)
        self.save(clear_after=True)

    def _set_banner(self, text: str, active: bool = False) -> None:
        self.banner_var.set(text)
        self.status_label.configure(style="DangerStatus.TLabel" if active else "Status.TLabel")

    def _tick_elapsed(self) -> None:
        if self.is_timing and self.stage_started_at:
            seconds = int((datetime.now() - self.stage_started_at).total_seconds())
            minutes, secs = divmod(max(0, seconds), 60)
            self.elapsed_var.set(f"{minutes:02d}:{secs:02d}")
        self.after(1000, self._tick_elapsed)

    def _update_preview(self) -> None:
        start = self.start_var.get().strip()
        end = self.end_var.get().strip()
        question = self.question_var.get().strip()
        if not start or not end:
            self.preview_var.set("填写时间后自动计算时长")
            return
        try:
            report = elapsed_seconds(start, end)
            q_and_a = elapsed_seconds(end, question) if question else 0
        except ValidationError:
            self.preview_var.set("时间格式示例：09:05")
            return
        self.preview_var.set(f"报告 {format_minutes(report)}   ·   提问 {format_minutes(q_and_a)}   ·   共 {format_minutes(report + q_and_a)}")

    def save(self, clear_after: bool = False) -> None:
        try:
            meeting_id = self.repository.save(
                name=self.name_var.get(),
                meeting_date=self.date_var.get(),
                start_time=self.start_var.get(),
                end_time=self.end_var.get(),
                question_time=self.question_var.get(),
                meeting_id=self.editing_id,
            )
        except (ValidationError, OSError, sqlite3.Error) as exc:
            messagebox.showerror("无法保存", str(exc), parent=self)
            return

        was_editing = self.editing_id is not None
        saved_name = self.name_var.get().strip()
        self.stage = None
        self.stage_started_at = None
        self.elapsed_var.set("00:00")
        self.editing_id = None
        self.edit_note_var.set("")
        self.save_button.configure(text="保存记录  Ctrl+S")
        self.app.refresh_all()
        if clear_after or not was_editing:
            self.clear_form(keep_date=True)
            if not clear_after:
                self.name_var.set(saved_name)
        self._set_banner("修改已保存" if was_editing else f"记录 #{meeting_id} 已保存")

    def clear_form(self, keep_date: bool = False) -> None:
        self.stage = None
        self.stage_started_at = None
        self.editing_id = None
        self.elapsed_var.set("00:00")
        self.edit_note_var.set("")
        self.save_button.configure(text="保存记录  Ctrl+S")
        self.name_var.set("")
        if not keep_date:
            self.date_var.set(date.today().isoformat())
        self.start_var.set("")
        self.end_var.set("")
        self.question_var.set("")
        self._set_banner("准备登记")

    def load_for_edit(self, meeting: Meeting) -> None:
        self.stage = None
        self.editing_id = meeting.id
        self.name_var.set(meeting.name)
        self.date_var.set(meeting.date)
        self.start_var.set(meeting.start_time)
        self.end_var.set(meeting.end_time)
        self.question_var.set(meeting.question_time)
        self.edit_note_var.set(f"正在修改记录 #{meeting.id}")
        self.save_button.configure(text="保存修改  Ctrl+S")
        self._set_banner("修改模式")

    def refresh(self) -> None:
        self.name_box.configure(values=self.repository.names())
        for item in self.recent_tree.get_children():
            self.recent_tree.delete(item)
        for meeting in self.repository.list_meetings(limit=6):
            self.recent_tree.insert(
                "",
                "end",
                values=(
                    meeting.date[5:],
                    meeting.name,
                    format_minutes(meeting.report_seconds),
                    format_minutes(meeting.question_seconds),
                ),
            )


class HistoryTab(ttk.Frame):
    def __init__(self, parent: ttk.Notebook, app: MeetingTimerApp):
        super().__init__(parent, padding=18, style="Card.TFrame")
        self.app = app
        self.repository = app.repository
        self.search_var = tk.StringVar()
        self.start_var = tk.StringVar()
        self.end_var = tk.StringVar()
        self.count_var = tk.StringVar()
        self.current_rows: list[Meeting] = []

        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        self._build_filters()
        self._build_table()
        self._build_actions()

    def _build_filters(self) -> None:
        ttk.Label(self, text="历史记录", style="CardTitle.TLabel").grid(row=0, column=0, sticky="w")
        filters = ttk.Frame(self, style="Card.TFrame")
        filters.grid(row=1, column=0, sticky="ew", pady=(12, 12))
        filters.columnconfigure(1, weight=1)
        ttk.Label(filters, text="汇报人", style="Field.TLabel").grid(row=0, column=0, padx=(0, 6))
        search = ttk.Entry(filters, textvariable=self.search_var, width=16)
        search.grid(row=0, column=1, sticky="ew", padx=(0, 14))
        search.bind("<Return>", lambda _event: self.refresh())
        ttk.Label(filters, text="从", style="Field.TLabel").grid(row=0, column=2, padx=(0, 6))
        ttk.Entry(filters, textvariable=self.start_var, width=13).grid(row=0, column=3, padx=(0, 12))
        ttk.Label(filters, text="到", style="Field.TLabel").grid(row=0, column=4, padx=(0, 6))
        ttk.Entry(filters, textvariable=self.end_var, width=13).grid(row=0, column=5, padx=(0, 12))
        ttk.Button(filters, text="查询", style="Green.TButton", command=self.refresh).grid(row=0, column=6)
        ttk.Button(filters, text="清除筛选", style="Soft.TButton", command=self.clear_filters).grid(row=0, column=7, padx=(8, 0))

    def _build_table(self) -> None:
        container = ttk.Frame(self, style="Card.TFrame")
        container.grid(row=2, column=0, sticky="nsew")
        container.columnconfigure(0, weight=1)
        container.rowconfigure(0, weight=1)
        columns = ("id", "date", "name", "range", "report", "question", "total")
        self.tree = ttk.Treeview(container, columns=columns, show="headings", selectmode="browse")
        labels = {
            "id": "ID",
            "date": "日期",
            "name": "汇报人",
            "range": "时间段",
            "report": "报告时长",
            "question": "提问时长",
            "total": "总时长",
        }
        widths = {"id": 55, "date": 110, "name": 90, "range": 190, "report": 110, "question": 110, "total": 110}
        for column in columns:
            self.tree.heading(column, text=labels[column])
            self.tree.column(column, width=widths[column], anchor="center", stretch=column == "range")
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.bind("<Double-1>", lambda _event: self.edit_selected())

    def _build_actions(self) -> None:
        actions = ttk.Frame(self, style="Card.TFrame")
        actions.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        actions.columnconfigure(0, weight=1)
        ttk.Label(actions, textvariable=self.count_var, style="CardText.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Button(actions, text="备份数据库", style="Soft.TButton", command=self.backup_database).grid(row=0, column=1, padx=4)
        ttk.Button(actions, text="导出当前列表", style="Soft.TButton", command=self.export_current).grid(row=0, column=2, padx=4)
        ttk.Button(actions, text="编辑所选", style="Green.TButton", command=self.edit_selected).grid(row=0, column=3, padx=4)
        ttk.Button(actions, text="删除所选", style="Danger.TButton", command=self.delete_selected).grid(row=0, column=4, padx=(4, 0))

    def selected_meeting(self) -> Meeting | None:
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("请选择记录", "请先在表格中选择一条记录。", parent=self)
            return None
        meeting_id = int(self.tree.item(selection[0], "values")[0])
        meeting = self.repository.get(meeting_id)
        if not meeting:
            messagebox.showwarning("记录已变化", "这条记录已不存在，列表将自动刷新。", parent=self)
            self.refresh()
        return meeting

    def edit_selected(self) -> None:
        meeting = self.selected_meeting()
        if meeting:
            self.app.edit_meeting(meeting)

    def delete_selected(self) -> None:
        meeting = self.selected_meeting()
        if not meeting:
            return
        if not messagebox.askyesno(
            "确认删除",
            f"确定删除 {meeting.date} · {meeting.name} 的记录吗？\n\n删除后无法在界面中撤销。",
            parent=self,
        ):
            return
        if self.repository.delete(meeting.id):
            self.app.refresh_all()

    def clear_filters(self) -> None:
        self.search_var.set("")
        self.start_var.set("")
        self.end_var.set("")
        self.refresh()

    def refresh(self) -> None:
        try:
            self.current_rows = self.repository.list_meetings(
                search=self.search_var.get(),
                start_date=self.start_var.get(),
                end_date=self.end_var.get(),
            )
        except ValidationError as exc:
            messagebox.showwarning("筛选日期有误", str(exc), parent=self)
            return
        for item in self.tree.get_children():
            self.tree.delete(item)
        for meeting in self.current_rows:
            self.tree.insert(
                "",
                "end",
                values=(
                    meeting.id,
                    meeting.date,
                    meeting.name,
                    f"{meeting.start_time} → {meeting.end_time} → {meeting.question_time}",
                    format_minutes(meeting.report_seconds),
                    format_minutes(meeting.question_seconds),
                    format_minutes(meeting.total_seconds),
                ),
            )
        self.count_var.set(f"当前显示 {len(self.current_rows)} 条记录 · 双击可编辑")

    def backup_database(self) -> None:
        suggested = f"meeting_times_backup_{datetime.now():%Y%m%d_%H%M}.db"
        path = filedialog.asksaveasfilename(
            parent=self,
            title="备份数据库",
            initialfile=suggested,
            defaultextension=".db",
            filetypes=[("SQLite 数据库", "*.db"), ("所有文件", "*.*")],
        )
        if path:
            self.repository.backup_to(path)
            messagebox.showinfo("备份完成", "数据库备份已保存。", parent=self)

    def export_current(self) -> None:
        path = filedialog.asksaveasfilename(
            parent=self,
            title="导出记录",
            initialfile=f"meeting_times_{date.today().isoformat()}.csv",
            defaultextension=".csv",
            filetypes=[("CSV 表格", "*.csv")],
        )
        if path:
            self.repository.export_csv(self.current_rows, path)
            messagebox.showinfo("导出完成", "当前列表已导出为 CSV。", parent=self)


class StatsTab(ttk.Frame):
    def __init__(self, parent: ttk.Notebook, app: MeetingTimerApp):
        super().__init__(parent, padding=18, style="Card.TFrame")
        self.repository = app.repository
        today = date.today()
        self.start_var = tk.StringVar(value=f"{today.year}-01-01")
        self.end_var = tk.StringVar(value=today.isoformat())
        self.summary_var = tk.StringVar()

        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)
        self._build_controls()
        self._build_table()

    def _build_controls(self) -> None:
        ttk.Label(self, text="统计概览", style="CardTitle.TLabel").grid(row=0, column=0, sticky="w")
        controls = ttk.Frame(self, style="Card.TFrame")
        controls.grid(row=1, column=0, sticky="ew", pady=(12, 12))
        ttk.Label(controls, text="统计区间", style="Field.TLabel").grid(row=0, column=0, padx=(0, 8))
        ttk.Entry(controls, textvariable=self.start_var, width=14).grid(row=0, column=1)
        ttk.Label(controls, text="至", style="Field.TLabel").grid(row=0, column=2, padx=8)
        ttk.Entry(controls, textvariable=self.end_var, width=14).grid(row=0, column=3)
        ttk.Button(controls, text="近 90 天", style="Soft.TButton", command=self.last_90_days).grid(row=0, column=4, padx=(12, 4))
        ttk.Button(controls, text="全部", style="Soft.TButton", command=self.all_time).grid(row=0, column=5, padx=4)
        ttk.Button(controls, text="更新统计", style="Green.TButton", command=self.refresh).grid(row=0, column=6, padx=(4, 0))

        ttk.Label(self, textvariable=self.summary_var, style="Metric.TLabel").grid(row=2, column=0, sticky="ew", pady=(0, 12))

    def _build_table(self) -> None:
        columns = ("rank", "name", "count", "report", "question", "total")
        self.tree = ttk.Treeview(self, columns=columns, show="headings")
        labels = {"rank": "排名", "name": "汇报人", "count": "次数", "report": "平均报告", "question": "平均提问", "total": "平均总时长"}
        widths = {"rank": 70, "name": 130, "count": 90, "report": 150, "question": 150, "total": 160}
        for column in columns:
            self.tree.heading(column, text=labels[column])
            self.tree.column(column, width=widths[column], anchor="center", stretch=column == "name")
        self.tree.grid(row=3, column=0, sticky="nsew")

    def last_90_days(self) -> None:
        today = date.today()
        self.start_var.set((today - timedelta(days=89)).isoformat())
        self.end_var.set(today.isoformat())
        self.refresh()

    def all_time(self) -> None:
        self.start_var.set("")
        self.end_var.set("")
        self.refresh()

    def refresh(self) -> None:
        try:
            statistics = self.repository.statistics(self.start_var.get(), self.end_var.get())
        except ValidationError as exc:
            messagebox.showwarning("统计日期有误", str(exc), parent=self)
            return
        for item in self.tree.get_children():
            self.tree.delete(item)
        for rank, item in enumerate(statistics, start=1):
            self.tree.insert(
                "",
                "end",
                values=(
                    rank,
                    item.name,
                    item.count,
                    format_minutes(item.average_report_seconds),
                    format_minutes(item.average_question_seconds),
                    format_minutes(item.average_total_seconds),
                ),
            )
        total_count = sum(item.count for item in statistics)
        weighted_total = sum(item.average_total_seconds * item.count for item in statistics)
        average_total = weighted_total / total_count if total_count else 0
        self.summary_var.set(
            f"{total_count} 次汇报   ·   {len(statistics)} 位汇报人   ·   平均总时长 {format_minutes(average_total)}"
        )


def main() -> None:
    try:
        repository = MeetingRepository(DB_PATH)
    except (OSError, sqlite3.Error) as exc:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("无法打开数据库", f"无法打开 {DB_PATH.name}：\n{exc}", parent=root)
        root.destroy()
        return
    MeetingTimerApp(repository).mainloop()


if __name__ == "__main__":
    main()
