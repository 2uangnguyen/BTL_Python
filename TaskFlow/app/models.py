"""Mô hình dữ liệu và các hàm tiện ích dùng chung."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional, Tuple

DT_FMT = "%Y-%m-%d %H:%M"
D_FMT = "%Y-%m-%d"

PRIORITIES = {0: "Thấp", 1: "Trung bình", 2: "Cao", 3: "Khẩn cấp"}

STATUS_TODO = "Chưa bắt đầu"
STATUS_DOING = "Đang thực hiện"
STATUS_DONE = "Hoàn thành"
STATUSES = [STATUS_TODO, STATUS_DOING, STATUS_DONE]

DEFAULT_CATEGORIES = ["Công việc", "Học tập", "Cá nhân", "Sức khỏe", "Tài chính", "Gia đình"]

# (nhãn, số phút nhắc trước hạn) - -1 = không nhắc
REMIND_OPTIONS = [
    ("Không nhắc", -1),
    ("Khi đến hạn", 0),
    ("Trước 15 phút", 15),
    ("Trước 30 phút", 30),
    ("Trước 1 giờ", 60),
    ("Trước 3 giờ", 180),
    ("Trước 1 ngày", 1440),
    ("Trước 2 ngày", 2880),
]

WEEKDAYS_FULL = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"]
WEEKDAYS_SHORT = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]


def parse_dt(s: Optional[str]) -> Optional[datetime]:
    return datetime.strptime(s, DT_FMT) if s else None


def parse_d(s: Optional[str]) -> Optional[date]:
    return datetime.strptime(s, D_FMT).date() if s else None


@dataclass
class Task:
    id: int
    title: str
    description: str
    category: str
    priority: int
    status: str
    progress: int
    start_date: Optional[str]
    due: Optional[str]
    remind_before: int
    reminded: int
    created_at: str
    completed_at: Optional[str]
    sub_total: int = 0   # số công việc con
    sub_done: int = 0    # số công việc con đã xong

    @classmethod
    def from_row(cls, row) -> "Task":
        return cls(**{k: row[k] for k in row.keys()})

    @property
    def progress_label(self) -> str:
        if self.sub_total:
            return f"{self.sub_done}/{self.sub_total}"
        return "✓" if self.is_done else "—"

    @property
    def progress_summary(self) -> str:
        return f"{self.sub_done}/{self.sub_total} việc con" if self.sub_total else self.status

    @property
    def is_done(self) -> bool:
        return self.status == STATUS_DONE

    @property
    def due_dt(self) -> Optional[datetime]:
        return parse_dt(self.due)

    def is_overdue(self, now: Optional[datetime] = None) -> bool:
        if self.is_done or not self.due:
            return False
        return self.due_dt < (now or datetime.now())

    def span(self) -> Tuple[Optional[date], Optional[date]]:
        """Khoảng ngày công việc xuất hiện trong lịch (bắt đầu → hạn)."""
        s = parse_d(self.start_date)
        e = self.due_dt.date() if self.due else None
        if s is None:
            s = e
        if e is None:
            e = s
        if s and e and e < s:
            s, e = e, s
        return s, e


def _dur(secs: float) -> str:
    m = int(secs // 60)
    if m < 60:
        return f"{max(m, 1)} phút"
    h = m // 60
    if h < 24:
        return f"{h} giờ"
    return f"{h // 24} ngày"


def humanize_due(t: Task, now: Optional[datetime] = None) -> str:
    if not t.due:
        return "Không đặt hạn"
    now = now or datetime.now()
    d = t.due_dt
    base = d.strftime("%d/%m %H:%M" if d.year == now.year else "%d/%m/%Y %H:%M")
    if t.is_done:
        return base
    secs = (d - now).total_seconds()
    return f"{base} · quá {_dur(-secs)}" if secs < 0 else f"{base} · còn {_dur(secs)}"
