"""Lập lịch kế hoạch theo Ngày / Tuần / Tháng."""
from __future__ import annotations

import calendar
from datetime import date, timedelta

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QButtonGroup, QCheckBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QSizePolicy, QVBoxLayout, QWidget,
)

from ..models import PRIORITIES, WEEKDAYS_FULL, WEEKDAYS_SHORT, humanize_due
from ..styles import PRIORITY_COLORS, STATUS_COLORS, T
from .widgets import (
    ClickableFrame, ClickableLabel, MiniBar, add_shadow, chip, clear_layout, rgba,
)

MAX_CHIPS = 3


class PlannerPage(QWidget):
    changed = Signal()
    request_edit = Signal(int)
    request_new = Signal(object)

    def __init__(self, db):
        super().__init__()
        self.db = db
        self.mode = "week"
        self.current = date.today()

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 8, 28, 24)
        root.setSpacing(14)

        # ---- thanh điều hướng
        bar = QHBoxLayout()
        bar.setSpacing(10)
        seg = QFrame()
        seg.setObjectName("card")
        sh = QHBoxLayout(seg)
        sh.setContentsMargins(4, 4, 4, 4)
        sh.setSpacing(2)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.seg_buttons = {}
        for key, label in (("day", "Ngày"), ("week", "Tuần"), ("month", "Tháng")):
            b = QPushButton(label)
            b.setObjectName("seg")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            self.group.addButton(b)
            self.seg_buttons[key] = b
            sh.addWidget(b)
            b.clicked.connect(lambda _=False, k=key: self.set_mode(k))
        self.seg_buttons[self.mode].setChecked(True)
        bar.addWidget(seg)

        prev_b, next_b = QPushButton("‹"), QPushButton("›")
        today_b = QPushButton("Hôm nay")
        for b in (prev_b, next_b):
            b.setObjectName("iconbtn")
        prev_b.clicked.connect(lambda: self.shift(-1))
        next_b.clicked.connect(lambda: self.shift(1))
        today_b.clicked.connect(self.go_today)
        bar.addWidget(prev_b)
        bar.addWidget(next_b)
        bar.addWidget(today_b)
        self.title = QLabel("")
        self.title.setObjectName("h2")
        self.title.setContentsMargins(10, 0, 0, 0)
        bar.addWidget(self.title, 1)
        add_b = QPushButton("＋  Thêm vào lịch")
        add_b.setObjectName("primary")
        add_b.clicked.connect(lambda: self.request_new.emit(self.current))
        bar.addWidget(add_b)
        root.addLayout(bar)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        root.addWidget(self.scroll, 1)

    # ------------------------------------------------------------ điều hướng
    def set_mode(self, mode: str):
        self.mode = mode
        self.seg_buttons[mode].setChecked(True)
        self.refresh()

    def go_today(self):
        self.current = date.today()
        self.refresh()

    def goto_day(self, d: date):
        self.current = d
        self.set_mode("day")

    def shift(self, n: int):
        if self.mode == "day":
            self.current += timedelta(days=n)
        elif self.mode == "week":
            self.current += timedelta(days=7 * n)
        else:
            m = self.current.month - 1 + n
            y, m = self.current.year + m // 12, m % 12 + 1
            self.current = date(y, m, min(self.current.day, calendar.monthrange(y, m)[1]))
        self.refresh()

    def _title_text(self) -> str:
        d = self.current
        if self.mode == "day":
            return f"{WEEKDAYS_FULL[d.weekday()]}, {d:%d/%m/%Y}"
        if self.mode == "week":
            s = d - timedelta(days=d.weekday())
            return f"Tuần {d.isocalendar()[1]}  ·  {s:%d/%m} – {s + timedelta(days=6):%d/%m/%Y}"
        return f"Tháng {d.month}/{d.year}"

    # --------------------------------------------------------------- dữ liệu
    def refresh(self):
        self.title.setText(self._title_text())
        build = {"day": self._build_day, "week": self._build_week, "month": self._build_month}[self.mode]
        w = build()
        old = self.scroll.takeWidget()
        if old is not None:
            old.deleteLater()
        self.scroll.setWidget(w)

    def _bucket(self, d1: date, d2: date) -> dict:
        out = {}
        for t in self.db.tasks_in_range(d1, d2):
            s, e = t.span()
            cur, last = max(s, d1), min(e, d2)
            while cur <= last:
                out.setdefault(cur, []).append(t)
                cur += timedelta(days=1)
        for lst in out.values():
            lst.sort(key=lambda t: (t.is_done, t.due or "9999", -t.priority))
        return out

    def _toggle(self, tid: int):
        self.db.toggle_done(tid)
        self.changed.emit()

    def _edit(self, tid: int):
        self.request_edit.emit(tid)

    @staticmethod
    def _strike(label: QLabel, bold: bool = True, px: int = 0, done: bool = False):
        f = QFont(label.font())
        f.setBold(bold)
        if px:
            f.setPixelSize(px)
        f.setStrikeOut(done)
        label.setFont(f)

    # ------------------------------------------------------------- DAY VIEW
    def _section(self, text: str, color: str | None = None) -> QLabel:
        lb = QLabel(text)
        lb.setStyleSheet(f"font-size:14px;font-weight:700;color:{color or T['text']};padding-top:6px;")
        return lb

    def _task_card(self, t) -> ClickableFrame:
        col = PRIORITY_COLORS[t.priority]
        c = ClickableFrame()
        c.setObjectName("taskcard")
        c.setMinimumHeight(66)
        h = QHBoxLayout(c)
        h.setContentsMargins(0, 0, 16, 0)
        h.setSpacing(12)
        bar = QFrame()
        bar.setFixedWidth(5)
        bar.setStyleSheet(f"background:{col};border:none;border-top-left-radius:12px;"
                          "border-bottom-left-radius:12px;")
        h.addWidget(bar)
        cb = QCheckBox()
        cb.setChecked(t.is_done)
        cb.setToolTip("Đánh dấu hoàn thành")
        cb.toggled.connect(lambda _=False, tid=t.id: self._toggle(tid))
        h.addWidget(cb)
        v = QVBoxLayout()
        v.setSpacing(1)
        title = QLabel(t.title)
        self._strike(title, True, 14, t.is_done)
        if t.is_done:
            title.setStyleSheet(f"color:{T['muted']};")
        meta = QLabel(f"{t.category}  ·  {humanize_due(t)}")
        meta.setStyleSheet(f"font-size:12px;color:{T['danger'] if t.is_overdue() else T['muted']};")
        v.addStretch()
        v.addWidget(title)
        v.addWidget(meta)
        v.addStretch()
        h.addLayout(v, 1)
        h.addWidget(chip(PRIORITIES[t.priority], col))
        h.addWidget(chip(f"☑ {t.sub_done}/{t.sub_total}" if t.sub_total else t.status,
                         STATUS_COLORS[t.status]))
        c.clicked.connect(lambda tid=t.id: self._edit(tid))
        return c

    def _build_day(self) -> QWidget:
        d, today = self.current, date.today()
        tasks = self._bucket(d, d).get(d, [])
        over = []
        if d == today:
            ids = {t.id for t in tasks}
            over = [t for t in self.db.overdue_tasks() if t.id not in ids]
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(10)

        done = sum(t.is_done for t in tasks)
        pct = round(done * 100 / len(tasks)) if tasks else 0
        card = QFrame()
        card.setObjectName("card")
        ch = QHBoxLayout(card)
        ch.setContentsMargins(22, 16, 22, 16)
        ch.setSpacing(20)
        left = QVBoxLayout()
        left.setSpacing(2)
        big = QLabel("Hôm nay" if d == today else WEEKDAYS_FULL[d.weekday()])
        big.setObjectName("h2")
        sm = QLabel(f"{len(tasks)} công việc trong ngày · {done} đã hoàn thành")
        sm.setObjectName("muted")
        left.addWidget(big)
        left.addWidget(sm)
        ch.addLayout(left)
        ch.addStretch()
        right = QVBoxLayout()
        right.setSpacing(4)
        rl = QLabel(f"Tiến độ ngày: {pct}%")
        rl.setStyleSheet("font-weight:700;")
        right.addWidget(rl)
        mb = MiniBar(pct, T["success"] if pct == 100 else T["primary"])
        mb.setFixedWidth(220)
        right.addWidget(mb)
        ch.addLayout(right)
        add_shadow(card)
        v.addWidget(card)

        if over:
            v.addWidget(self._section(f"⚠  Quá hạn chưa hoàn thành ({len(over)})", T["danger"]))
            for t in over:
                v.addWidget(self._task_card(t))

        v.addWidget(self._section("📌  Công việc trong ngày"))
        if tasks:
            for t in tasks:
                v.addWidget(self._task_card(t))
        else:
            e = QFrame()
            e.setObjectName("card")
            eh = QVBoxLayout(e)
            eh.setContentsMargins(20, 36, 20, 36)
            lb = QLabel("🌤  Chưa có công việc nào cho ngày này.\nNhấn “＋ Thêm vào lịch” để lập kế hoạch.")
            lb.setObjectName("muted")
            lb.setAlignment(Qt.AlignCenter)
            eh.addWidget(lb)
            v.addWidget(e)
        v.addStretch()
        return w

    # ------------------------------------------------------------ WEEK VIEW
    def _mini_card(self, t, d: date) -> ClickableFrame:
        col = PRIORITY_COLORS[t.priority]
        c = ClickableFrame()
        c.setObjectName("minicard")
        c.setStyleSheet(
            f"QFrame#minicard{{background:{rgba(col, 30)};border:none;"
            f"border-left:4px solid {col};border-radius:8px;}}")
        v = QVBoxLayout(c)
        v.setContentsMargins(9, 7, 8, 7)
        v.setSpacing(2)
        title = QLabel(t.title)
        title.setWordWrap(True)
        self._strike(title, True, 12, t.is_done)
        if t.is_done:
            title.setStyleSheet(f"color:{T['muted']};")
        if t.due and t.due_dt.date() == d:
            sub = f"Hạn {t.due_dt:%H:%M} · {t.progress_summary}"
        else:
            sub = f"{t.progress_summary} · {t.category}"
        s = QLabel(sub)
        s.setStyleSheet(f"font-size:11px;color:{T['muted']};")
        v.addWidget(title)
        v.addWidget(s)
        c.clicked.connect(lambda tid=t.id: self._edit(tid))
        return c

    def _build_week(self) -> QWidget:
        start = self.current - timedelta(days=self.current.weekday())
        buckets = self._bucket(start, start + timedelta(days=6))
        today = date.today()
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(10)
        for i in range(7):
            d = start + timedelta(days=i)
            col = QFrame()
            col.setObjectName("daycol")
            col.setProperty("today", d == today)
            col.setMinimumWidth(138)
            col.setMinimumHeight(440)
            v = QVBoxLayout(col)
            v.setContentsMargins(8, 8, 8, 10)
            v.setSpacing(6)
            head = ClickableFrame()
            head.setObjectName("colhead")
            hv = QVBoxLayout(head)
            hv.setContentsMargins(6, 4, 6, 4)
            hv.setSpacing(0)
            dn = QLabel(WEEKDAYS_FULL[d.weekday()])
            dn.setAlignment(Qt.AlignCenter)
            dn.setStyleSheet(f"font-size:12px;font-weight:600;color:{T['primary'] if d == today else T['muted']};")
            num = QLabel(str(d.day))
            num.setAlignment(Qt.AlignCenter)
            num.setStyleSheet(f"font-size:22px;font-weight:800;color:{T['primary'] if d == today else T['text']};")
            hv.addWidget(dn)
            hv.addWidget(num)
            head.clicked.connect(lambda dd=d: self.goto_day(dd))
            v.addWidget(head)
            tasks = buckets.get(d, [])
            for t in tasks:
                v.addWidget(self._mini_card(t, d))
            if not tasks:
                e = QLabel("—")
                e.setAlignment(Qt.AlignCenter)
                e.setObjectName("muted")
                v.addWidget(e)
            v.addStretch()
            h.addWidget(col, 1)
        return w

    # ----------------------------------------------------------- MONTH VIEW
    def _build_month(self) -> QWidget:
        y, m = self.current.year, self.current.month
        first = date(y, m, 1)
        last = date(y, m, calendar.monthrange(y, m)[1])
        start = first - timedelta(days=first.weekday())
        end = last + timedelta(days=6 - last.weekday())
        rows = ((end - start).days + 1) // 7
        buckets = self._bucket(start, end)
        today = date.today()

        w = QWidget()
        g = QGridLayout(w)
        g.setContentsMargins(0, 0, 0, 0)
        g.setSpacing(8)
        for c in range(7):
            lb = QLabel(WEEKDAYS_SHORT[c])
            lb.setAlignment(Qt.AlignCenter)
            lb.setObjectName("muted")
            lb.setStyleSheet("font-weight:700;")
            g.addWidget(lb, 0, c)
            g.setColumnStretch(c, 1)
        for r in range(rows):
            for c in range(7):
                d = start + timedelta(days=r * 7 + c)
                g.addWidget(self._month_cell(d, buckets.get(d, []), d.month == m, d == today), r + 1, c)
        return w

    def _month_cell(self, d: date, tasks, in_month: bool, is_today: bool) -> ClickableFrame:
        cell = ClickableFrame()
        cell.setObjectName("daycell")
        cell.setProperty("dim", not in_month)
        cell.setProperty("today", is_today)
        cell.setMinimumHeight(112)
        cell.setMinimumWidth(80)
        cell.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        v = QVBoxLayout(cell)
        v.setContentsMargins(8, 6, 8, 6)
        v.setSpacing(3)
        top = QHBoxLayout()
        num = QLabel(str(d.day))
        if is_today:
            num.setAlignment(Qt.AlignCenter)
            num.setStyleSheet(f"background:{T['primary']};color:white;border-radius:11px;font-weight:800;"
                              "min-width:22px;max-width:22px;min-height:22px;max-height:22px;")
        else:
            num.setStyleSheet(f"font-weight:700;color:{T['text'] if in_month else T['muted']};")
        top.addWidget(num)
        top.addStretch()
        if tasks:
            cnt = QLabel(str(len(tasks)))
            cnt.setStyleSheet(f"font-size:11px;font-weight:700;color:{T['muted']};")
            top.addWidget(cnt)
        v.addLayout(top)
        for t in tasks[:MAX_CHIPS]:
            col = PRIORITY_COLORS[t.priority]
            lb = ClickableLabel(("✓ " if t.is_done else "") + t.title)
            lb.setToolTip(f"{t.title}\n{humanize_due(t)}")
            lb.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
            lb.setStyleSheet(
                f"background:{rgba(col, 34)};color:{T['muted'] if t.is_done else col};"
                "border-radius:5px;padding:2px 6px;font-size:11px;font-weight:600;")
            self._strike(lb, True, 11, t.is_done)
            lb.clicked.connect(lambda tid=t.id: self._edit(tid))
            v.addWidget(lb)
        if len(tasks) > MAX_CHIPS:
            more = ClickableLabel(f"+{len(tasks) - MAX_CHIPS} việc khác")
            more.setStyleSheet(f"font-size:11px;color:{T['primary']};font-weight:600;padding-left:4px;")
            more.clicked.connect(lambda dd=d: self.goto_day(dd))
            v.addWidget(more)
        v.addStretch()
        cell.clicked.connect(lambda dd=d: self.goto_day(dd))
        return cell
