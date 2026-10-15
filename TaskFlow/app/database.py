"""Lớp truy cập dữ liệu SQLite."""
from __future__ import annotations

import sqlite3
import unicodedata
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from .models import (
    D_FMT, DT_FMT, PRIORITIES, STATUS_DOING, STATUS_DONE, STATUS_TODO, STATUSES, Task,
)

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "taskflow.db"

SELECT_TASK = (
    "SELECT t.*, "
    "(SELECT COUNT(*) FROM subtasks s WHERE s.task_id=t.id) AS sub_total, "
    "(SELECT COUNT(*) FROM subtasks s WHERE s.task_id=t.id AND s.done=1) AS sub_done "
    "FROM tasks t"
)

FIELDS = ["title", "description", "category", "priority", "status", "progress",
          "start_date", "due", "remind_before", "reminded", "completed_at"]


def fold(s) -> str:
    """Chuẩn hóa chuỗi để tìm kiếm không phân biệt hoa/thường và dấu tiếng Việt."""
    if s is None:
        return ""
    s = unicodedata.normalize("NFD", str(s).lower().replace("đ", "d"))
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


class Database:
    def __init__(self, path: Path = DB_PATH):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path))
        self.conn.row_factory = sqlite3.Row
        self.conn.create_function("fold", 1, fold)
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._init_schema()
        if self.get_setting("seeded") is None:
            if self.conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 0:
                self._seed()
            self.set_setting("seeded", "1")

    # ------------------------------------------------------------------ schema
    def _init_schema(self):
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                title         TEXT NOT NULL,
                description   TEXT DEFAULT '',
                category      TEXT DEFAULT 'Công việc',
                priority      INTEGER DEFAULT 1,
                status        TEXT DEFAULT 'Chưa bắt đầu',
                progress      INTEGER DEFAULT 0,
                start_date    TEXT,
                due           TEXT,
                remind_before INTEGER DEFAULT 60,
                reminded      INTEGER DEFAULT 0,
                created_at    TEXT NOT NULL,
                completed_at  TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_tasks_due ON tasks(due);
            CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
            CREATE TABLE IF NOT EXISTS subtasks (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id  INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                title    TEXT NOT NULL,
                done     INTEGER DEFAULT 0,
                position INTEGER DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS idx_sub_task ON subtasks(task_id);
            CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
            """
        )
        self.conn.commit()

    # --------------------------------------------------------------- settings
    def get_setting(self, key: str, default=None):
        r = self.conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return r["value"] if r else default

    def set_setting(self, key: str, value: str):
        self.conn.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (key, value))
        self.conn.commit()

    # -------------------------------------------------------------- normalize
    @staticmethod
    def _normalize(data: dict) -> dict:
        status = data.get("status") or STATUS_TODO
        progress = max(0, min(100, int(data.get("progress") or 0)))
        if status == STATUS_DONE:
            progress = 100
        elif progress >= 100:
            status, progress = STATUS_DONE, 100
        elif progress > 0 and status == STATUS_TODO:
            status = STATUS_DOING
        data["status"], data["progress"] = status, progress
        if status == STATUS_DONE:
            if not data.get("completed_at"):
                data["completed_at"] = datetime.now().strftime(DT_FMT)
        else:
            data["completed_at"] = None
        return data

    # ------------------------------------------------------------------- CRUD
    def add_task(self, **f) -> int:
        data = {
            "title": "", "description": "", "category": "Công việc", "priority": 1,
            "status": STATUS_TODO, "progress": 0, "start_date": None, "due": None,
            "remind_before": 60, "reminded": 0, "completed_at": None,
        }
        data.update(f)
        data = self._normalize(data)
        created = f.get("created_at") or datetime.now().strftime(DT_FMT)
        cur = self.conn.execute(
            f"INSERT INTO tasks({','.join(FIELDS)},created_at) VALUES({','.join('?' * len(FIELDS))},?)",
            [data[k] for k in FIELDS] + [created],
        )
        self.conn.commit()
        return cur.lastrowid

    def update_task(self, tid: int, **changes):
        old = self.get_task(tid)
        if not old:
            return
        data = {k: getattr(old, k) for k in FIELDS}
        data.update(changes)
        if data["due"] != old.due or data["remind_before"] != old.remind_before:
            data["reminded"] = 0
        data = self._normalize(data)
        self.conn.execute(
            f"UPDATE tasks SET {', '.join(k + '=?' for k in FIELDS)} WHERE id=?",
            [data[k] for k in FIELDS] + [tid],
        )
        self.conn.commit()

    def delete_tasks(self, ids: List[int]):
        self.conn.executemany("DELETE FROM subtasks WHERE task_id=?", [(i,) for i in ids])
        self.conn.executemany("DELETE FROM tasks WHERE id=?", [(i,) for i in ids])
        self.conn.commit()

    def get_task(self, tid: int) -> Optional[Task]:
        r = self.conn.execute(f"{SELECT_TASK} WHERE t.id=?", (tid,)).fetchone()
        return Task.from_row(r) if r else None

    # ------------------------------------------------------------- trạng thái
    def mark_done(self, tid: int):
        """Hoàn thành công việc = tích xong tất cả công việc con."""
        self.conn.execute("UPDATE subtasks SET done=1 WHERE task_id=?", (tid,))
        self.conn.commit()
        self.update_task(tid, status=STATUS_DONE, progress=100)

    def reopen(self, tid: int):
        t = self.get_task(tid)
        if not t:
            return
        pct = 0
        if t.sub_total and t.sub_done == t.sub_total:  # bỏ tích việc con cuối cùng
            self.conn.execute(
                "UPDATE subtasks SET done=0 WHERE id=(SELECT id FROM subtasks WHERE task_id=? "
                "AND done=1 ORDER BY position DESC, id DESC LIMIT 1)", (tid,))
            self.conn.commit()
        if t.sub_total:
            t = self.get_task(tid)
            pct = t.sub_done * 100 // t.sub_total
        self.update_task(tid, status=STATUS_DOING, progress=pct)

    def toggle_done(self, tid: int):
        t = self.get_task(tid)
        if t:
            self.reopen(tid) if t.is_done else self.mark_done(tid)

    def set_status(self, tid: int, status: str):
        t = self.get_task(tid)
        if not t:
            return
        if status == STATUS_DONE:
            self.mark_done(tid)
        elif status == STATUS_TODO:
            self.conn.execute("UPDATE subtasks SET done=0 WHERE task_id=?", (tid,))
            self.conn.commit()
            self.update_task(tid, status=STATUS_TODO, progress=0)
        elif t.is_done:
            self.reopen(tid)
        else:
            self.update_task(tid, status=STATUS_DOING)

    # ------------------------------------------------------------ công việc con
    def list_subtasks(self, tid: int) -> List[dict]:
        rows = self.conn.execute(
            "SELECT id, title, done FROM subtasks WHERE task_id=? ORDER BY position, id", (tid,))
        return [{"id": r["id"], "title": r["title"], "done": bool(r["done"])} for r in rows]

    def set_subtasks(self, tid: int, items):
        """Ghi lại toàn bộ danh sách công việc con: items = [(tiêu đề, đã xong)]."""
        self.conn.execute("DELETE FROM subtasks WHERE task_id=?", (tid,))
        self.conn.executemany(
            "INSERT INTO subtasks(task_id,title,done,position) VALUES(?,?,?,?)",
            [(tid, title, int(bool(done)), i) for i, (title, done) in enumerate(items)])
        self.conn.commit()
        self.sync_progress(tid)

    def toggle_subtask(self, sid: int):
        r = self.conn.execute("SELECT task_id FROM subtasks WHERE id=?", (sid,)).fetchone()
        if not r:
            return
        self.conn.execute("UPDATE subtasks SET done=1-done WHERE id=?", (sid,))
        self.conn.commit()
        self.sync_progress(r["task_id"])

    def sync_progress(self, tid: int):
        """Tiến độ = % công việc con đã xong; trạng thái đi theo."""
        t = self.get_task(tid)
        if not t:
            return
        if t.sub_total == 0:
            self.update_task(tid, progress=100 if t.is_done else 0)
            return
        pct = t.sub_done * 100 // t.sub_total
        if t.sub_done == t.sub_total:
            status = STATUS_DONE
        elif t.sub_done > 0:
            status = STATUS_DOING
        else:
            status = STATUS_TODO if t.is_done else t.status
        self.update_task(tid, progress=pct, status=status)

    # ---------------------------------------------------------------- queries
    def list_tasks(self, search: str = "", priority: Optional[int] = None,
                   status: Optional[str] = None, category: Optional[str] = None,
                   sort: str = "due") -> List[Task]:
        sql, p = f"{SELECT_TASK} WHERE 1=1", []
        if search.strip():
            k = f"%{fold(search.strip())}%"
            sql += " AND (fold(title) LIKE ? OR fold(description) LIKE ? OR fold(category) LIKE ?)"
            p += [k, k, k]
        if priority is not None:
            sql += " AND priority=?"
            p.append(priority)
        if status:
            sql += " AND status=?"
            p.append(status)
        if category:
            sql += " AND category=?"
            p.append(category)
        done = f"(status='{STATUS_DONE}')"
        order = {
            "due": f" ORDER BY {done}, (due IS NULL), due ASC, priority DESC",
            "priority": f" ORDER BY {done}, priority DESC, (due IS NULL), due ASC",
            "created": " ORDER BY id DESC",
            "progress": " ORDER BY progress DESC, id DESC",
        }[sort]
        return [Task.from_row(r) for r in self.conn.execute(sql + order, p)]

    def tasks_in_range(self, d1: date, d2: date) -> List[Task]:
        """Các công việc có khoảng [bắt đầu, hạn] giao với [d1, d2]."""
        rows = self.conn.execute(
            f"{SELECT_TASK} WHERE COALESCE(start_date, substr(due,1,10)) <= ? "
            "AND COALESCE(substr(due,1,10), start_date) >= ?",
            (d2.strftime(D_FMT), d1.strftime(D_FMT)),
        )
        return [Task.from_row(r) for r in rows]

    def overdue_tasks(self) -> List[Task]:
        now = datetime.now().strftime(DT_FMT)
        rows = self.conn.execute(
            f"{SELECT_TASK} WHERE status!=? AND due IS NOT NULL AND due<? ORDER BY due",
            (STATUS_DONE, now))
        return [Task.from_row(r) for r in rows]

    def upcoming(self, hours: int = 24 * 7, limit: int = 8) -> List[Task]:
        """Việc chưa xong, đã quá hạn hoặc sắp đến hạn trong `hours` giờ tới."""
        cutoff = (datetime.now() + timedelta(hours=hours)).strftime(DT_FMT)
        rows = self.conn.execute(
            f"{SELECT_TASK} WHERE status!=? AND due IS NOT NULL AND due<=? "
            "ORDER BY due ASC LIMIT ?", (STATUS_DONE, cutoff, limit))
        return [Task.from_row(r) for r in rows]

    def categories(self) -> List[str]:
        return [r[0] for r in self.conn.execute(
            "SELECT DISTINCT category FROM tasks WHERE category!='' ORDER BY category")]

    # --------------------------------------------------------------- reminder
    def reminder_candidates(self) -> List[Task]:
        rows = self.conn.execute(
            f"{SELECT_TASK} WHERE status!=? AND due IS NOT NULL AND reminded<2", (STATUS_DONE,))
        return [Task.from_row(r) for r in rows]

    def mark_reminded(self, tid: int, level: int):
        self.conn.execute("UPDATE tasks SET reminded=? WHERE id=?", (level, tid))
        self.conn.commit()

    # ------------------------------------------------------------------ stats
    def stats(self) -> Dict:
        c, now, today = self.conn, datetime.now(), date.today()
        by_status = {s: 0 for s in STATUSES}
        for r in c.execute("SELECT status, COUNT(*) n FROM tasks GROUP BY status"):
            by_status[r["status"]] = r["n"]
        total = sum(by_status.values())
        overdue = c.execute(
            "SELECT COUNT(*) FROM tasks WHERE status!=? AND due IS NOT NULL AND due<?",
            (STATUS_DONE, now.strftime(DT_FMT))).fetchone()[0]
        due_today = c.execute(
            "SELECT COUNT(*) FROM tasks WHERE status!=? AND substr(due,1,10)=?",
            (STATUS_DONE, today.strftime(D_FMT))).fetchone()[0]
        by_priority = {i: 0 for i in PRIORITIES}
        for r in c.execute("SELECT priority, COUNT(*) n FROM tasks WHERE status!=? GROUP BY priority",
                           (STATUS_DONE,)):
            by_priority[r["priority"]] = r["n"]
        days = [today - timedelta(days=i) for i in range(6, -1, -1)]
        counts = {d.strftime(D_FMT): 0 for d in days}
        for r in c.execute(
                "SELECT substr(completed_at,1,10) d, COUNT(*) n FROM tasks "
                "WHERE completed_at IS NOT NULL AND substr(completed_at,1,10)>=? GROUP BY d",
                (days[0].strftime(D_FMT),)):
            if r["d"] in counts:
                counts[r["d"]] = r["n"]
        cats = [
            {"category": r["category"], "total": r["total"], "done": r["done"] or 0,
             "avg": r["avg"] or 0}
            for r in c.execute(
                "SELECT category, COUNT(*) total, SUM(status=?) done, AVG(progress) avg "
                "FROM tasks GROUP BY category ORDER BY total DESC", (STATUS_DONE,))
        ]
        return {
            "total": total, "by_status": by_status, "overdue": overdue, "due_today": due_today,
            "by_priority": by_priority, "last7": [(d, counts[d.strftime(D_FMT)]) for d in days],
            "categories": cats,
        }

    # ------------------------------------------------------------------- seed
    def _seed(self):
        """Dữ liệu mẫu cho lần chạy đầu tiên (xóa tuỳ ý)."""
        today = date.today()

        def dt(days, h, m=0):
            return (datetime.combine(today, time(h, m)) + timedelta(days=days)).strftime(DT_FMT)

        def d(days):
            return (today + timedelta(days=days)).strftime(D_FMT)

        T, G, D = STATUS_TODO, STATUS_DOING, STATUS_DONE
        samples = [
            ("Hoàn thiện báo cáo tuần", "Tổng hợp số liệu và gửi quản lý", "Công việc", 3, G,
             [("Thu thập số liệu", 1), ("Viết phần nội dung", 1), ("Làm biểu đồ", 1),
              ("Rà soát lỗi", 0), ("Gửi cho quản lý", 0)], d(-1), dt(0, 23, 0), 60, None),
            ("Họp nhóm dự án", "Chuẩn bị slide báo cáo tiến độ", "Công việc", 2, T,
             [("Soạn slide", 0), ("Gửi agenda cho nhóm", 0), ("Đặt phòng họp", 0)],
             d(0), dt(1, 9, 30), 30, None),
            ("Học tiếng Anh 30 phút", "Ôn từ vựng và luyện nghe", "Học tập", 1, G,
             [("Ôn 20 từ vựng", 1), ("Nghe podcast", 1), ("Viết nhật ký", 0), ("Luyện nói", 0), ("Làm quiz", 0)],
             d(-3), dt(3, 21), 60, None),
            ("Khám sức khỏe định kỳ", "Đặt lịch và chuẩn bị giấy tờ", "Sức khỏe", 2, T,
             [("Đặt lịch khám", 0), ("Chuẩn bị giấy tờ", 0)], d(2), dt(4, 8), 1440, None),
            ("Thanh toán hóa đơn điện nước", "Chuyển khoản qua ngân hàng", "Tài chính", 3, T,
             [], d(-2), dt(-1, 12), 60, None),
            ("Chuẩn bị quà sinh nhật bạn", "Chọn quà và gói quà", "Gia đình", 2, T,
             [("Chọn quà", 0), ("Mua quà", 0), ("Gói quà", 0)], d(5), dt(7, 18), 1440, None),
            ("Lập kế hoạch chi tiêu tháng", "Phân bổ ngân sách theo nhóm", "Tài chính", 1, D,
             [("Liệt kê thu nhập", 1), ("Phân bổ ngân sách", 1)], d(-4), dt(-2, 18), 60, dt(-2, 16)),
            ("Đọc xong chương 3 sách Python", "Làm bài tập cuối chương", "Học tập", 1, D,
             [], d(-3), dt(-1, 20), 60, dt(-1, 19)),
            ("Dọn dẹp bàn làm việc", "", "Cá nhân", 0, D, [], d(0), dt(0, 9), -1, dt(0, 8)),
            ("Chạy bộ buổi sáng", "5 km quanh hồ", "Sức khỏe", 1, D, [], d(-3), dt(-3, 7), -1, dt(-3, 7)),
            ("Gửi email báo giá khách hàng", "", "Công việc", 2, D, [], d(-5), dt(-4, 15), 60, dt(-4, 14)),
        ]
        for title, desc, cat, pr, st, subs, start, due, rem, comp in samples:
            tid = self.add_task(title=title, description=desc, category=cat, priority=pr, status=st,
                                progress=100 if st == D else 0, start_date=start, due=due,
                                remind_before=rem, completed_at=comp)
            if subs:
                self.set_subtasks(tid, [(t, bool(x)) for t, x in subs])
