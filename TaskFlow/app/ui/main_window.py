"""Cửa sổ chính: thanh bên, thanh tiêu đề, các trang và nhắc nhở."""
from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication, QButtonGroup, QFrame, QHBoxLayout, QLabel, QMainWindow, QMenu, QPushButton,
    QStackedWidget, QSystemTrayIcon, QVBoxLayout, QWidget,
)

from .. import styles
from ..icon import make_app_icon
from ..models import humanize_due
from ..reminder import ReminderService
from .dashboard_page import DashboardPage
from .planner_page import PlannerPage
from .task_dialog import TaskDialog
from .task_page import TaskPage
from .widgets import Toast

PAGES = [
    ("📊", "Tổng quan", "Tổng quan", "Thống kê và tiến độ công việc của bạn"),
    ("✅", "Công việc", "Công việc của tôi", "Thêm, tìm kiếm, phân loại và theo dõi tiến độ"),
    ("🗓", "Kế hoạch", "Lập kế hoạch", "Xem lịch theo ngày, tuần và tháng"),
]


class MainWindow(QMainWindow):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self._quitting = False
        self._tray_hinted = False
        self._last_day = date.today()
        self.setWindowTitle("TaskFlow — Quản lý công việc cá nhân")
        self.setWindowIcon(make_app_icon())
        self.resize(1380, 880)
        self.setMinimumSize(1120, 720)

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_sidebar())

        right = QWidget()
        right.setObjectName("content")
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.setSpacing(0)
        rv.addWidget(self._build_topbar())
        self.stack = QStackedWidget()
        rv.addWidget(self.stack, 1)
        root.addWidget(right, 1)

        self.dashboard = DashboardPage(db)
        self.tasks = TaskPage(db)
        self.planner = PlannerPage(db)
        for p in (self.dashboard, self.tasks, self.planner):
            self.stack.addWidget(p)

        self.dashboard.request_edit.connect(self.edit_task)
        for p in (self.tasks, self.planner):
            p.changed.connect(self.refresh_all)
            p.request_edit.connect(self.edit_task)
            p.request_new.connect(self.new_task)

        self.toast = Toast(central)

        # ---- nhắc nhở
        self.reminders = ReminderService(db, parent=self)
        self.reminders.notified.connect(self._on_notify)
        self.reminders.checked.connect(self._on_checked)
        self._setup_tray()

        # ---- phím tắt
        QShortcut(QKeySequence("Ctrl+N"), self, activated=lambda: self.new_task(None))
        QShortcut(QKeySequence("Ctrl+F"), self, activated=self._focus_search)
        for i in range(3):
            QShortcut(QKeySequence(f"Ctrl+{i + 1}"), self, activated=lambda i=i: self.switch(i))

        self.apply_theme(db.get_setting("theme", "light"))
        self.switch(0)
        QTimer.singleShot(1200, self.reminders.check)

    # ---------------------------------------------------------------- bố cục
    def _build_sidebar(self) -> QFrame:
        sb = QFrame()
        sb.setObjectName("sidebar")
        sb.setFixedWidth(236)
        v = QVBoxLayout(sb)
        v.setContentsMargins(16, 24, 16, 18)
        v.setSpacing(6)

        logo = QHBoxLayout()
        ic = QLabel("✓")
        ic.setFixedSize(40, 40)
        ic.setAlignment(Qt.AlignCenter)
        ic.setStyleSheet(
            "background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #6366F1,stop:1 #A855F7);"
            "color:white;border-radius:12px;font-size:22px;font-weight:800;")
        name = QLabel("TaskFlow")
        name.setObjectName("brand")
        logo.addWidget(ic)
        logo.addWidget(name, 1)
        v.addLayout(logo)
        v.addSpacing(22)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self.nav_buttons = []
        for i, (icon, label, *_rest) in enumerate(PAGES):
            b = QPushButton(f"  {icon}   {label}")
            b.setObjectName("nav")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, i=i: self.switch(i))
            self.nav_group.addButton(b)
            self.nav_buttons.append(b)
            v.addWidget(b)
        v.addStretch()

        hint = QLabel("Ctrl+N  thêm việc\nCtrl+F  tìm kiếm\nCtrl+1/2/3  chuyển trang")
        hint.setObjectName("muted")
        hint.setStyleSheet("font-size:11px;")
        v.addWidget(hint)
        v.addSpacing(8)
        self.theme_btn = QPushButton()
        self.theme_btn.clicked.connect(self.toggle_theme)
        v.addWidget(self.theme_btn)
        return sb

    def _build_topbar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("content")
        h = QHBoxLayout(bar)
        h.setContentsMargins(28, 22, 28, 14)
        h.setSpacing(10)
        v = QVBoxLayout()
        v.setSpacing(0)
        self.page_title = QLabel()
        self.page_title.setObjectName("h1")
        self.page_sub = QLabel()
        self.page_sub.setObjectName("muted")
        v.addWidget(self.page_title)
        v.addWidget(self.page_sub)
        h.addLayout(v, 1)
        self.bell = QPushButton("🔔")
        self.bell.setToolTip("Việc sắp đến hạn / quá hạn")
        self.bell.clicked.connect(self._show_bell)
        h.addWidget(self.bell)
        add = QPushButton("＋  Thêm công việc")
        add.setObjectName("primary")
        add.clicked.connect(lambda: self.new_task(None))
        h.addWidget(add)
        return bar

    # ------------------------------------------------------------- điều hướng
    def switch(self, i: int):
        self.stack.setCurrentIndex(i)
        self.nav_buttons[i].setChecked(True)
        self.page_title.setText(PAGES[i][2])
        self.page_sub.setText(PAGES[i][3])
        self.refresh_all()

    def _focus_search(self):
        self.switch(1)
        self.tasks.focus_search()

    def refresh_all(self):
        self._last_day = date.today()
        self.dashboard.refresh()
        self.tasks.refresh()
        self.planner.refresh()
        self.update_bell()

    # ------------------------------------------------------------ chủ đề
    def apply_theme(self, name: str):
        styles.set_theme(name)
        app = QApplication.instance()
        app.setPalette(styles.make_palette())
        app.setStyleSheet(styles.qss())
        self.theme_btn.setText("☀️  Chế độ sáng" if name == "dark" else "🌙  Chế độ tối")
        self.db.set_setting("theme", name)
        self.refresh_all()

    def toggle_theme(self):
        self.apply_theme("light" if styles.T["name"] == "dark" else "dark")

    # ------------------------------------------------------- thêm / sửa / xóa
    def new_task(self, default_date=None):
        dlg = TaskDialog(self.db, None, default_date, self)
        if dlg.exec():
            v = dlg.values()
            subs = v.pop("subtasks")
            tid = self.db.add_task(**v)
            self.db.set_subtasks(tid, subs)
            self.refresh_all()

    def edit_task(self, tid: int):
        t = self.db.get_task(tid)
        if not t:
            return
        dlg = TaskDialog(self.db, t, None, self)
        if dlg.exec():
            if dlg.deleted:
                self.db.delete_tasks([tid])
            else:
                v = dlg.values()
                subs = v.pop("subtasks")
                self.db.update_task(tid, **v)
                self.db.set_subtasks(tid, subs)
            self.refresh_all()

    # ------------------------------------------------------------ nhắc nhở
    def update_bell(self):
        n = len(self.db.upcoming(hours=24, limit=50))
        self.bell.setText(f"🔔  {n}" if n else "🔔")

    def _show_bell(self):
        items = self.db.upcoming(hours=24 * 3, limit=12)
        menu = QMenu(self)
        if not items:
            menu.addAction("🎉  Không có việc sắp đến hạn").setEnabled(False)
        for t in items:
            icon = "⚠" if t.is_overdue() else "⏰"
            act = menu.addAction(f"{icon}  {t.title}   —   {humanize_due(t)}")
            act.triggered.connect(lambda _=False, tid=t.id: self.edit_task(tid))
        menu.exec(self.bell.mapToGlobal(self.bell.rect().bottomLeft()))

    def _on_notify(self, title: str, msg: str, kind: str):
        self.toast.show_message(title, msg, kind)
        if self.tray:
            self.tray.showMessage(title, msg, QSystemTrayIcon.Information, 8000)

    def _on_checked(self):
        self.update_bell()
        if date.today() != self._last_day:  # qua ngày mới
            self.refresh_all()

    # ------------------------------------------------------------- khay hệ thống
    def _setup_tray(self):
        self.tray = None
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self.tray = QSystemTrayIcon(make_app_icon(), self)
        self._tray_menu = QMenu()
        self._tray_menu.addAction("Mở TaskFlow").triggered.connect(self._show_from_tray)
        self._tray_menu.addAction("Thoát").triggered.connect(self._quit)
        self.tray.setContextMenu(self._tray_menu)
        self.tray.activated.connect(
            lambda reason: self._show_from_tray() if reason == QSystemTrayIcon.Trigger else None)
        self.tray.setToolTip("TaskFlow — đang chạy nền để nhắc việc")
        self.tray.show()
        QApplication.instance().setQuitOnLastWindowClosed(False)

    def _show_from_tray(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _quit(self):
        self._quitting = True
        QApplication.instance().quit()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if hasattr(self, "toast") and self.toast.isVisible():
            self.toast.reposition()

    def closeEvent(self, e):
        if self.tray and self.tray.isVisible() and not self._quitting:
            e.ignore()
            self.hide()
            if not self._tray_hinted:
                self._tray_hinted = True
                self.tray.showMessage(
                    "TaskFlow vẫn đang chạy",
                    "Ứng dụng chạy nền để nhắc việc. Chuột phải biểu tượng khay hệ thống để thoát.",
                    QSystemTrayIcon.Information, 5000)
        else:
            e.accept()
            QApplication.instance().quit()
