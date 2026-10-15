"""Dịch vụ nhắc nhở: định kỳ kiểm tra hạn hoàn thành và phát tín hiệu thông báo."""
from datetime import datetime, timedelta

from PySide6.QtCore import QObject, QTimer, Signal

from .models import humanize_due


class ReminderService(QObject):
    # tiêu đề, nội dung, loại ("danger" | "warning")
    notified = Signal(str, str, str)
    checked = Signal()

    def __init__(self, db, interval_ms: int = 30_000, parent=None):
        super().__init__(parent)
        self.db = db
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check)
        self.timer.start(interval_ms)

    def check(self):
        now = datetime.now()
        overdue, upcoming = [], []
        for t in self.db.reminder_candidates():
            due = t.due_dt
            if now >= due:
                self.db.mark_reminded(t.id, 2)
                overdue.append(t)
            elif t.remind_before >= 0 and t.reminded < 1 and now >= due - timedelta(minutes=t.remind_before):
                self.db.mark_reminded(t.id, 1)
                upcoming.append(t)

        if overdue or upcoming:
            lines = [f"⚠ {t.title} — đã quá hạn" for t in overdue[:3]]
            lines += [f"⏰ {t.title} — {humanize_due(t, now).split('· ')[-1]}" for t in upcoming[:3]]
            extra = len(overdue) + len(upcoming) - len(lines)
            if extra > 0:
                lines.append(f"… và {extra} việc khác")
            title = "🔔 Nhắc nhở công việc"
            self.notified.emit(title, "\n".join(lines), "danger" if overdue else "warning")
        self.checked.emit()
