"""Hộp thoại thêm / sửa công việc (có danh sách công việc con)."""
from __future__ import annotations

from datetime import date

from PySide6.QtCore import QDate, QDateTime, QTime, Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDateEdit, QDateTimeEdit, QDialog, QFrame, QGridLayout, QHBoxLayout,
    QLabel, QLineEdit, QMessageBox, QPlainTextEdit, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from ..models import (
    DEFAULT_CATEGORIES, PRIORITIES, REMIND_OPTIONS, STATUS_DOING, STATUS_DONE, STATUS_TODO,
    STATUSES,
)
from ..styles import PRIORITY_COLORS, T
from .widgets import MiniBar, dot_icon


def _field(label: str, widget: QWidget) -> QWidget:
    w = QWidget()
    v = QVBoxLayout(w)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(5)
    lb = QLabel(label)
    lb.setObjectName("muted")
    lb.setStyleSheet("font-weight:600;")
    v.addWidget(lb)
    v.addWidget(widget)
    return w


class SubtaskEditor(QWidget):
    """Danh sách công việc con: tích hoàn thành, sửa tên, xóa, thêm mới."""
    changed = Signal()

    def __init__(self):
        super().__init__()
        self.rows = []  # (widget, checkbox, lineedit)
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)

        head = QHBoxLayout()
        lb = QLabel("Công việc con (tiến độ tự tính theo số việc đã xong)")
        lb.setObjectName("muted")
        lb.setStyleSheet("font-weight:600;")
        self.summary = QLabel("")
        self.summary.setStyleSheet("font-weight:700;")
        head.addWidget(lb)
        head.addStretch()
        head.addWidget(self.summary)
        v.addLayout(head)
        self.bar = MiniBar(0)
        v.addWidget(self.bar)

        box = QFrame()
        box.setObjectName("card")
        bl = QVBoxLayout(box)
        bl.setContentsMargins(4, 4, 4, 4)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setMinimumHeight(96)
        self.scroll.setMaximumHeight(176)
        holder = QWidget()
        self.rows_layout = QVBoxLayout(holder)
        self.rows_layout.setContentsMargins(6, 4, 6, 4)
        self.rows_layout.setSpacing(2)
        self.rows_layout.addStretch()
        self.scroll.setWidget(holder)
        bl.addWidget(self.scroll)
        v.addWidget(box)

        add = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("＋ Nhập công việc con rồi nhấn Enter…")
        self.input.returnPressed.connect(self._add_from_input)
        btn = QPushButton("Thêm")
        btn.setAutoDefault(False)
        btn.clicked.connect(self._add_from_input)
        add.addWidget(self.input, 1)
        add.addWidget(btn)
        v.addLayout(add)
        self._update_summary()

    # --------------------------------------------------------------- hàng
    def add_row(self, title: str = "", done: bool = False, emit: bool = True):
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)
        cb = QCheckBox()
        cb.setChecked(done)
        le = QLineEdit(title)
        le.setPlaceholderText("Tên công việc con")
        x = QPushButton("✕")
        x.setFixedSize(28, 28)
        x.setCursor(Qt.PointingHandCursor)
        x.setAutoDefault(False)
        x.setToolTip("Xóa công việc con")
        x.setStyleSheet(
            f"QPushButton{{border:none;background:transparent;color:{T['muted']};padding:0;min-height:0;}}"
            f"QPushButton:hover{{color:{T['danger']};background:transparent;}}")
        h.addWidget(cb)
        h.addWidget(le, 1)
        h.addWidget(x)
        entry = (row, cb, le)
        self.rows.append(entry)
        self.rows_layout.insertWidget(self.rows_layout.count() - 1, row)
        cb.toggled.connect(lambda _=False, e=entry: self._on_toggle(e))
        x.clicked.connect(lambda _=False, e=entry: self._remove(e))
        self._style(entry)
        if emit:
            self._emit()

    @staticmethod
    def _style(entry):
        _, cb, le = entry
        done = cb.isChecked()
        f = le.font()
        f.setStrikeOut(done)
        le.setFont(f)
        le.setStyleSheet(
            f"border:none;background:transparent;padding:5px 2px;color:{T['muted'] if done else T['text']};")

    def _on_toggle(self, entry):
        self._style(entry)
        self._emit()

    def _remove(self, entry):
        self.rows.remove(entry)
        entry[0].setParent(None)
        entry[0].deleteLater()
        self._emit()

    def _add_from_input(self):
        text = self.input.text().strip()
        if not text:
            return
        self.add_row(text, False)
        self.input.clear()
        QTimer.singleShot(0, lambda: self.scroll.verticalScrollBar().setValue(
            self.scroll.verticalScrollBar().maximum()))

    # ------------------------------------------------------------- API
    def items(self):
        return [(le.text().strip(), cb.isChecked()) for _, cb, le in self.rows if le.text().strip()]

    def counts(self):
        it = self.items()
        return sum(1 for _, d in it if d), len(it)

    def set_items(self, items):
        for entry in list(self.rows):
            entry[0].setParent(None)
            entry[0].deleteLater()
        self.rows.clear()
        for title, done in items:
            self.add_row(title, done, emit=False)
        self._update_summary()

    def set_all(self, done: bool):
        for entry in self.rows:
            entry[1].blockSignals(True)
            entry[1].setChecked(done)
            entry[1].blockSignals(False)
            self._style(entry)
        self._emit()

    def uncheck_last(self):
        for entry in reversed(self.rows):
            if entry[1].isChecked() and entry[2].text().strip():
                entry[1].setChecked(False)
                return

    def _update_summary(self):
        d, t = self.counts()
        if t:
            pct = d * 100 // t
            self.summary.setText(f"{d}/{t} hoàn thành · {pct}%")
            self.bar.value = pct
            self.bar.color = T["success"] if pct == 100 else T["primary"]
        else:
            self.summary.setText("Chưa có công việc con")
            self.bar.value = 0
        self.bar.update()

    def _emit(self):
        self._update_summary()
        self.changed.emit()


class TaskDialog(QDialog):
    def __init__(self, db, task=None, default_date: date | None = None, parent=None):
        super().__init__(parent)
        self.db, self.task = db, task
        self.deleted = False
        self._syncing = False
        self.setWindowTitle("Sửa công việc" if task else "Thêm công việc mới")
        self.setMinimumWidth(600)
        self.setModal(True)

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 22)
        root.setSpacing(14)
        head = QLabel("✏️  Sửa công việc" if task else "✨  Thêm công việc mới")
        head.setObjectName("h2")
        root.addWidget(head)

        # ---- các trường nhập
        self.title = QLineEdit()
        self.title.setPlaceholderText("Bạn cần làm gì?")
        self.desc = QPlainTextEdit()
        self.desc.setPlaceholderText("Mô tả chi tiết (không bắt buộc)")
        self.desc.setFixedHeight(66)

        self.category = QComboBox()
        self.category.setEditable(True)
        self.category.addItems(list(dict.fromkeys(DEFAULT_CATEGORIES + db.categories())))

        self.priority = QComboBox()
        for i, name in PRIORITIES.items():
            self.priority.addItem(dot_icon(PRIORITY_COLORS[i]), name)
        self.priority.setCurrentIndex(1)

        self.status = QComboBox()
        self.status.addItems(STATUSES)

        self.remind = QComboBox()
        for label, minutes in REMIND_OPTIONS:
            self.remind.addItem(label, minutes)
        self.remind.setCurrentIndex(4)

        self.start = QDateEdit()
        self.start.setCalendarPopup(True)
        self.start.setDisplayFormat("dd/MM/yyyy")
        self.start.setDate(QDate.currentDate())

        self.has_due = QCheckBox("Đặt hạn")
        self.due = QDateTimeEdit()
        self.due.setCalendarPopup(True)
        self.due.setDisplayFormat("dd/MM/yyyy  HH:mm")
        due_w = QWidget()
        dh = QHBoxLayout(due_w)
        dh.setContentsMargins(0, 0, 0, 0)
        dh.setSpacing(10)
        dh.addWidget(self.has_due)
        dh.addWidget(self.due, 1)

        self.subs = SubtaskEditor()

        # ---- bố cục lưới
        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(12)
        grid.addWidget(_field("Tiêu đề *", self.title), 0, 0, 1, 2)
        grid.addWidget(_field("Mô tả", self.desc), 1, 0, 1, 2)
        grid.addWidget(_field("Phân loại", self.category), 2, 0)
        grid.addWidget(_field("Mức độ ưu tiên", self.priority), 2, 1)
        grid.addWidget(_field("Trạng thái", self.status), 3, 0)
        grid.addWidget(_field("Nhắc nhở", self.remind), 3, 1)
        grid.addWidget(_field("Ngày bắt đầu", self.start), 4, 0)
        grid.addWidget(_field("Hạn hoàn thành", due_w), 4, 1)
        grid.addWidget(self.subs, 5, 0, 1, 2)
        root.addLayout(grid)

        self.error = QLabel("")
        self.error.setObjectName("error")
        self.error.hide()
        root.addWidget(self.error)

        # ---- nút
        btns = QHBoxLayout()
        if task:
            bd = QPushButton("🗑  Xóa")
            bd.setObjectName("danger")
            bd.setAutoDefault(False)
            bd.clicked.connect(self._delete)
            btns.addWidget(bd)
        btns.addStretch()
        bc = QPushButton("Hủy")
        bc.setAutoDefault(False)
        bc.clicked.connect(self.reject)
        self.save_btn = QPushButton("Lưu công việc")
        self.save_btn.setObjectName("primary")
        self.save_btn.setAutoDefault(False)
        self.save_btn.clicked.connect(self._save)
        btns.addWidget(bc)
        btns.addWidget(self.save_btn)
        root.addLayout(btns)

        # ---- nạp dữ liệu
        if task:
            self._load(task)
        else:
            base = default_date or date.today()
            self.start.setDate(QDate(base.year, base.month, base.day))
            if default_date:
                self.has_due.setChecked(True)
                self.due.setDateTime(QDateTime(QDate(base.year, base.month, base.day), QTime(17, 0)))
            else:
                self.due.setDateTime(QDateTime(QDate.currentDate().addDays(1), QTime(17, 0)))
        self._toggle_due()

        self.has_due.toggled.connect(self._toggle_due)
        self.status.currentIndexChanged.connect(self._on_status)
        self.subs.changed.connect(self._on_subs_changed)
        self.title.setFocus()

    # ------------------------------------------------------------ nạp dữ liệu
    def _load(self, t):
        self.title.setText(t.title)
        self.desc.setPlainText(t.description or "")
        self.category.setCurrentText(t.category)
        self.priority.setCurrentIndex(t.priority)
        self.status.setCurrentIndex(STATUSES.index(t.status))
        self.subs.set_items([(s["title"], s["done"]) for s in self.db.list_subtasks(t.id)])
        if t.start_date:
            self.start.setDate(QDate.fromString(t.start_date, "yyyy-MM-dd"))
        self.has_due.setChecked(bool(t.due))
        if t.due:
            self.due.setDateTime(QDateTime.fromString(t.due, "yyyy-MM-dd HH:mm"))
        else:
            self.due.setDateTime(QDateTime(QDate.currentDate().addDays(1), QTime(17, 0)))
        idx = self.remind.findData(t.remind_before)
        self.remind.setCurrentIndex(idx if idx >= 0 else 4)

    # --------------------------------------------------------- đồng bộ trường
    def _toggle_due(self):
        on = self.has_due.isChecked()
        self.due.setEnabled(on)
        self.remind.setEnabled(on)

    def _on_status(self, idx: int):
        """Đổi trạng thái → cập nhật các công việc con cho khớp."""
        if self._syncing:
            return
        self._syncing = True
        s = STATUSES[idx]
        done, total = self.subs.counts()
        if total:
            if s == STATUS_DONE:
                self.subs.set_all(True)
            elif s == STATUS_TODO:
                self.subs.set_all(False)
            elif done == total:
                self.subs.uncheck_last()
        self._syncing = False

    def _on_subs_changed(self):
        """Tích công việc con → trạng thái tự đổi theo."""
        if self._syncing:
            return
        done, total = self.subs.counts()
        if not total:
            return
        self._syncing = True
        cur = STATUSES[self.status.currentIndex()]
        if done == total:
            new = STATUS_DONE
        elif done > 0:
            new = STATUS_DOING
        else:
            new = STATUS_TODO if cur == STATUS_DONE else cur
        self.status.setCurrentIndex(STATUSES.index(new))
        self._syncing = False

    # --------------------------------------------------------------- hành động
    def _save(self):
        if not self.title.text().strip():
            return self._show_error("Vui lòng nhập tiêu đề công việc.")
        if self.has_due.isChecked():
            if self.due.dateTime() < QDateTime(self.start.date(), QTime(0, 0)):
                return self._show_error("Hạn hoàn thành không được trước ngày bắt đầu.")
        self.accept()

    def _show_error(self, msg: str):
        self.error.setText("⚠ " + msg)
        self.error.show()

    def _delete(self):
        r = QMessageBox.question(self, "Xóa công việc", f"Xóa công việc “{self.task.title}”?",
                                 QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if r == QMessageBox.Yes:
            self.deleted = True
            self.accept()

    def values(self) -> dict:
        subs = self.subs.items()
        status = STATUSES[self.status.currentIndex()]
        if subs:
            progress = sum(1 for _, d in subs if d) * 100 // len(subs)
        else:
            progress = 100 if status == STATUS_DONE else 0
        return dict(
            title=self.title.text().strip(),
            description=self.desc.toPlainText().strip(),
            category=self.category.currentText().strip() or "Công việc",
            priority=self.priority.currentIndex(),
            status=status,
            progress=progress,
            start_date=self.start.date().toString("yyyy-MM-dd"),
            due=self.due.dateTime().toString("yyyy-MM-dd HH:mm") if self.has_due.isChecked() else None,
            remind_before=self.remind.currentData(),
            subtasks=subs,
        )
