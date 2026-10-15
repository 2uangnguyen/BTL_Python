"""Dashboard: thống kê tổng quan, biểu đồ, việc sắp đến hạn."""
from __future__ import annotations

from datetime import date, datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget

from ..models import (
    PRIORITIES, STATUS_DOING, STATUS_DONE, STATUS_TODO, WEEKDAYS_FULL, WEEKDAYS_SHORT, humanize_due,
)
from ..styles import PRIORITY_COLORS, STATUS_COLORS, T
from .widgets import (
    BarChart, ClickableFrame, DonutChart, MiniBar, StatCard, add_shadow, clear_layout, make_panel,
)


class DashboardPage(QWidget):
    request_edit = Signal(int)

    def __init__(self, db):
        super().__init__()
        self.db = db
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        outer.addWidget(scroll)
        body = QWidget()
        scroll.setWidget(body)
        v = QVBoxLayout(body)
        v.setContentsMargins(28, 8, 28, 28)
        v.setSpacing(18)

        # ---- hero
        hero = QFrame()
        hero.setObjectName("hero")
        hero.setStyleSheet(
            "QFrame#hero{background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #6366F1,stop:1 #A855F7);"
            "border-radius:20px;}")
        hh = QHBoxLayout(hero)
        hh.setContentsMargins(30, 24, 30, 24)
        hv = QVBoxLayout()
        hv.setSpacing(4)
        self.greet = QLabel()
        self.greet.setStyleSheet("color:white;font-size:24px;font-weight:800;")
        self.greet_sub = QLabel()
        self.greet_sub.setWordWrap(True)
        self.greet_sub.setStyleSheet("color:rgba(255,255,255,215);font-size:14px;")
        hv.addWidget(self.greet)
        hv.addWidget(self.greet_sub)
        hh.addLayout(hv, 1)
        rv = QVBoxLayout()
        rv.setSpacing(0)
        self.rate = QLabel("0%")
        self.rate.setAlignment(Qt.AlignRight)
        self.rate.setStyleSheet("color:white;font-size:40px;font-weight:800;")
        rl = QLabel("tỷ lệ hoàn thành")
        rl.setAlignment(Qt.AlignRight)
        rl.setStyleSheet("color:rgba(255,255,255,200);font-size:12px;")
        rv.addWidget(self.rate)
        rv.addWidget(rl)
        hh.addLayout(rv)
        add_shadow(hero, 30, 8, 50)
        v.addWidget(hero)

        # ---- thẻ số liệu
        row = QHBoxLayout()
        row.setSpacing(16)
        self.c_total = StatCard("🗂", "Tổng công việc", "#6366F1")
        self.c_done = StatCard("✅", "Đã hoàn thành", "#22C55E")
        self.c_doing = StatCard("⏳", "Đang thực hiện", "#3B82F6")
        self.c_over = StatCard("🚨", "Quá hạn", "#EF4444")
        for c in (self.c_total, self.c_done, self.c_doing, self.c_over):
            row.addWidget(c, 1)
        v.addLayout(row)

        # ---- biểu đồ
        mid = QHBoxLayout()
        mid.setSpacing(16)
        p1, l1 = make_panel("Trạng thái công việc")
        self.donut = DonutChart()
        l1.addWidget(self.donut, 1)
        self.legend = QVBoxLayout()
        self.legend.setSpacing(6)
        l1.addLayout(self.legend)
        p2, l2 = make_panel("Việc đang mở theo ưu tiên")
        self.bar_pr = BarChart()
        l2.addWidget(self.bar_pr, 1)
        p3, l3 = make_panel("Hoàn thành 7 ngày qua")
        self.bar_7 = BarChart()
        l3.addWidget(self.bar_7, 1)
        for p in (p1, p2, p3):
            mid.addWidget(p, 1)
        v.addLayout(mid)

        # ---- danh sách
        bot = QHBoxLayout()
        bot.setSpacing(16)
        p4, l4 = make_panel("⏰ Sắp đến hạn & quá hạn", "Nhấn vào công việc để chỉnh sửa")
        self.upcoming = QVBoxLayout()
        self.upcoming.setSpacing(2)
        l4.addLayout(self.upcoming)
        l4.addStretch()
        p5, l5 = make_panel("📊 Tiến độ theo phân loại")
        self.cats = QVBoxLayout()
        self.cats.setSpacing(14)
        l5.addLayout(self.cats)
        l5.addStretch()
        bot.addWidget(p4, 3)
        bot.addWidget(p5, 2)
        v.addLayout(bot)
        v.addStretch()

    # ------------------------------------------------------------------ refresh
    def refresh(self):
        s = self.db.stats()
        total, bs = s["total"], s["by_status"]
        done = bs[STATUS_DONE]
        rate = round(done * 100 / total) if total else 0

        h = datetime.now().hour
        hello = "Chào buổi sáng" if h < 12 else "Chào buổi chiều" if h < 18 else "Chào buổi tối"
        today = date.today()
        self.greet.setText(f"{hello}! 👋")
        parts = []
        if s["due_today"]:
            parts.append(f"{s['due_today']} việc đến hạn hôm nay")
        if s["overdue"]:
            parts.append(f"{s['overdue']} việc đã quá hạn")
        tail = " · ".join(parts) if parts else "Không có việc gấp — bạn đang làm rất tốt!"
        self.greet_sub.setText(f"{WEEKDAYS_FULL[today.weekday()]}, {today:%d/%m/%Y}  —  {tail}")
        self.rate.setText(f"{rate}%")

        self.c_total.set_value(total, f"{bs[STATUS_TODO]} chưa bắt đầu")
        self.c_done.set_value(done, f"{rate}% tổng số")
        self.c_doing.set_value(bs[STATUS_DOING], "đang xử lý")
        self.c_over.set_value(s["overdue"], "cần xử lý ngay" if s["overdue"] else "không có")

        self.donut.set_data(
            [(k, bs[k], STATUS_COLORS[k]) for k in (STATUS_DONE, STATUS_DOING, STATUS_TODO)],
            f"{rate}%", "hoàn thành")
        clear_layout(self.legend)
        for k in (STATUS_DONE, STATUS_DOING, STATUS_TODO):
            r = QHBoxLayout()
            dot = QLabel()
            dot.setFixedSize(10, 10)
            dot.setStyleSheet(f"background:{STATUS_COLORS[k]};border-radius:5px;")
            r.addWidget(dot)
            r.addWidget(QLabel(k), 1)
            n = QLabel(str(bs[k]))
            n.setStyleSheet("font-weight:700;")
            r.addWidget(n)
            self.legend.addLayout(r)

        self.bar_pr.set_data([(PRIORITIES[i], s["by_priority"][i], PRIORITY_COLORS[i]) for i in PRIORITIES])
        self.bar_7.set_data([(f"{WEEKDAYS_SHORT[d.weekday()]} {d.day}", n, T["primary"]) for d, n in s["last7"]])

        # ---- sắp đến hạn
        clear_layout(self.upcoming)
        items = self.db.upcoming(hours=24 * 7, limit=7)
        if not items:
            e = QLabel("🎉  Không có việc nào sắp đến hạn trong 7 ngày tới.")
            e.setObjectName("muted")
            e.setContentsMargins(0, 18, 0, 18)
            self.upcoming.addWidget(e)
        for t in items:
            self.upcoming.addWidget(self._row(t))

        # ---- theo phân loại
        clear_layout(self.cats)
        if not s["categories"]:
            e = QLabel("Chưa có dữ liệu.")
            e.setObjectName("muted")
            self.cats.addWidget(e)
        for c in s["categories"][:6]:
            box = QVBoxLayout()
            box.setSpacing(5)
            top = QHBoxLayout()
            top.addWidget(QLabel(c["category"]), 1)
            cnt = QLabel(f"{c['done']}/{c['total']} · {round(c['avg'])}%")
            cnt.setObjectName("muted")
            top.addWidget(cnt)
            box.addLayout(top)
            box.addWidget(MiniBar(c["avg"], T["success"] if c["avg"] >= 100 else T["primary"]))
            self.cats.addLayout(box)

    def _row(self, t) -> QFrame:
        f = ClickableFrame()
        f.setObjectName("rowitem")
        h = QHBoxLayout(f)
        h.setContentsMargins(10, 8, 10, 8)
        h.setSpacing(12)
        dot = QLabel()
        dot.setFixedSize(10, 10)
        dot.setStyleSheet(f"background:{PRIORITY_COLORS[t.priority]};border-radius:5px;")
        h.addWidget(dot)
        col = QVBoxLayout()
        col.setSpacing(0)
        title = QLabel(t.title)
        title.setStyleSheet("font-weight:700;")
        sub = QLabel(f"{t.category} · {PRIORITIES[t.priority]}")
        sub.setObjectName("muted")
        sub.setStyleSheet("font-size:11px;")
        col.addWidget(title)
        col.addWidget(sub)
        h.addLayout(col, 1)
        due = QLabel(humanize_due(t))
        due.setStyleSheet(f"font-weight:600;color:{T['danger'] if t.is_overdue() else T['muted']};")
        h.addWidget(due)
        f.clicked.connect(lambda tid=t.id: self.request_edit.emit(tid))
        return f
