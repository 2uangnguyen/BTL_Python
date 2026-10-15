"""Trang quản lý công việc: tìm kiếm, lọc, sắp xếp, thêm/sửa/xóa, cập nhật tiến độ."""
from __future__ import annotations

from PySide6.QtCore import QRect, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics, QKeySequence, QPainter, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QFrame, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMenu,
    QMessageBox, QPushButton, QStyle, QStyledItemDelegate, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from ..models import PRIORITIES, STATUS_DONE, STATUSES, humanize_due
from ..styles import PRIORITY_COLORS, STATUS_COLORS, T
from .widgets import add_shadow

COLS = ["Công việc", "Phân loại", "Ưu tiên", "Trạng thái", "Việc con", "Hạn hoàn thành"]
ROLE_SUB, ROLE_DONE, ROLE_ID, ROLE_COLOR = (Qt.UserRole, Qt.UserRole + 1, Qt.UserRole + 2, Qt.UserRole + 3)


def _paint_selection(p: QPainter, opt):
    if opt.state & QStyle.State_Selected:
        p.fillRect(opt.rect, QColor(T["sel"]))


class TitleDelegate(QStyledItemDelegate):
    def paint(self, p, opt, idx):
        p.save()
        _paint_selection(p, opt)
        done = bool(idx.data(ROLE_DONE))
        r = opt.rect.adjusted(14, 7, -8, -7)
        f = QFont(opt.font)
        f.setBold(True)
        f.setPixelSize(14)
        f.setStrikeOut(done)
        p.setFont(f)
        p.setPen(QColor(T["muted"] if done else T["text"]))
        title = QFontMetrics(f).elidedText(idx.data(Qt.DisplayRole) or "", Qt.ElideRight, r.width())
        p.drawText(QRect(r.x(), r.y(), r.width(), 22), Qt.AlignVCenter | Qt.AlignLeft, title)
        f2 = QFont(opt.font)
        f2.setPixelSize(12)
        p.setFont(f2)
        p.setPen(QColor(T["muted"]))
        sub = QFontMetrics(f2).elidedText(idx.data(ROLE_SUB) or "", Qt.ElideRight, r.width())
        p.drawText(QRect(r.x(), r.y() + 22, r.width(), 18), Qt.AlignVCenter | Qt.AlignLeft, sub)
        p.restore()


class ChipDelegate(QStyledItemDelegate):
    def paint(self, p, opt, idx):
        p.save()
        p.setRenderHint(QPainter.Antialiasing)
        _paint_selection(p, opt)
        color = QColor(idx.data(ROLE_COLOR))
        text = idx.data(Qt.DisplayRole) or ""
        f = QFont(opt.font)
        f.setBold(True)
        f.setPixelSize(12)
        p.setFont(f)
        w = QFontMetrics(f).horizontalAdvance(text) + 24
        r = QRectF(opt.rect.x() + 8, opt.rect.center().y() - 13, w, 26)
        bg = QColor(color)
        bg.setAlpha(38)
        p.setPen(Qt.NoPen)
        p.setBrush(bg)
        p.drawRoundedRect(r, 13, 13)
        p.setBrush(color)
        p.drawEllipse(QRectF(r.x() + 9, r.center().y() - 3, 6, 6))
        p.setPen(color)
        p.drawText(QRectF(r.x() + 18, r.y(), r.width() - 18, r.height()), Qt.AlignCenter, text)
        p.restore()


class ProgressDelegate(QStyledItemDelegate):
    def paint(self, p, opt, idx):
        p.save()
        p.setRenderHint(QPainter.Antialiasing)
        _paint_selection(p, opt)
        val = int(idx.data(ROLE_COLOR) or 0)
        r = opt.rect.adjusted(10, 0, -10, 0)
        bar = QRectF(r.x(), r.center().y() - 4, max(10, r.width() - 58), 8)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(T["border"]))
        p.drawRoundedRect(bar, 4, 4)
        if val > 0:
            color = QColor(T["success"] if val >= 100 else T["primary"])
            p.setBrush(color)
            p.drawRoundedRect(QRectF(bar.x(), bar.y(), max(8.0, bar.width() * val / 100), 8), 4, 4)
        f = QFont(opt.font)
        f.setPixelSize(12)
        f.setBold(True)
        p.setFont(f)
        p.setPen(QColor(T["text"]))
        p.drawText(QRectF(bar.right() + 8, r.y(), 50, r.height()), Qt.AlignVCenter | Qt.AlignLeft,
                   idx.data(Qt.DisplayRole) or "")
        p.restore()


class TaskPage(QWidget):
    changed = Signal()
    request_edit = Signal(int)
    request_new = Signal(object)

    SORTS = [("Hạn gần nhất", "due"), ("Ưu tiên cao nhất", "priority"),
             ("Mới tạo nhất", "created"), ("Tiến độ cao nhất", "progress")]

    def __init__(self, db):
        super().__init__()
        self.db = db
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 8, 28, 24)
        lay.setSpacing(14)

        # ---- thanh công cụ
        bar = QFrame()
        bar.setObjectName("card")
        bh = QHBoxLayout(bar)
        bh.setContentsMargins(14, 12, 14, 12)
        bh.setSpacing(10)
        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍  Tìm theo tiêu đề, mô tả, phân loại…")
        self.search.setClearButtonEnabled(True)
        self.search.setMinimumWidth(280)
        self.f_priority = QComboBox()
        self.f_priority.addItems(["Tất cả ưu tiên"] + list(PRIORITIES.values()))
        self.f_status = QComboBox()
        self.f_status.addItems(["Tất cả trạng thái"] + STATUSES)
        self.f_category = QComboBox()
        self.f_category.addItem("Tất cả phân loại")
        self.f_sort = QComboBox()
        for label, _ in self.SORTS:
            self.f_sort.addItem("↕  " + label)
        bh.addWidget(self.search, 2)
        for c in (self.f_priority, self.f_status, self.f_category, self.f_sort):
            bh.addWidget(c, 1)
        add_shadow(bar)
        lay.addWidget(bar)

        # ---- hàng nút hành động
        ah = QHBoxLayout()
        self.count = QLabel("")
        self.count.setObjectName("muted")
        ah.addWidget(self.count)
        ah.addStretch()
        self.b_done = QPushButton("✓  Hoàn thành")
        self.b_edit = QPushButton("✏️  Sửa")
        self.b_del = QPushButton("🗑  Xóa")
        self.b_del.setObjectName("danger")
        self.b_add = QPushButton("＋  Thêm công việc")
        self.b_add.setObjectName("primary")
        for b in (self.b_done, self.b_edit, self.b_del, self.b_add):
            ah.addWidget(b)
        lay.addLayout(ah)

        # ---- bảng
        card = QFrame()
        card.setObjectName("card")
        cv = QVBoxLayout(card)
        cv.setContentsMargins(8, 8, 8, 8)
        self.table = QTableWidget(0, len(COLS))
        self.table.setHorizontalHeaderLabels(COLS)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(58)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        hh = self.table.horizontalHeader()
        hh.setHighlightSections(False)
        hh.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        hh.setSectionResizeMode(0, QHeaderView.Stretch)
        for i, w in zip(range(1, 6), (120, 150, 170, 190, 190)):
            hh.setSectionResizeMode(i, QHeaderView.Fixed)
            self.table.setColumnWidth(i, w)
        self.table.setItemDelegateForColumn(0, TitleDelegate(self.table))
        self.table.setItemDelegateForColumn(2, ChipDelegate(self.table))
        self.table.setItemDelegateForColumn(3, ChipDelegate(self.table))
        self.table.setItemDelegateForColumn(4, ProgressDelegate(self.table))
        cv.addWidget(self.table)
        self.empty = QLabel("🗂  Không tìm thấy công việc nào.\nHãy thêm công việc mới hoặc đổi bộ lọc.")
        self.empty.setObjectName("muted")
        self.empty.setAlignment(Qt.AlignCenter)
        self.empty.setMinimumHeight(220)
        cv.addWidget(self.empty)
        add_shadow(card)
        lay.addWidget(card, 1)

        # ---- kết nối
        self.search.textChanged.connect(self.refresh)
        for c in (self.f_priority, self.f_status, self.f_category, self.f_sort):
            c.currentIndexChanged.connect(self.refresh)
        self.b_add.clicked.connect(lambda: self.request_new.emit(None))
        self.b_edit.clicked.connect(self.edit_selected)
        self.b_del.clicked.connect(self.delete_selected)
        self.b_done.clicked.connect(self.complete_selected)
        self.table.cellDoubleClicked.connect(lambda r, c: self._edit_row(r))
        self.table.customContextMenuRequested.connect(self._context_menu)
        sc = QShortcut(QKeySequence(Qt.Key_Delete), self.table)
        sc.setContext(Qt.WidgetShortcut)
        sc.activated.connect(self.delete_selected)

    # ----------------------------------------------------------------- dữ liệu
    def focus_search(self):
        self.search.setFocus()
        self.search.selectAll()

    def selected_ids(self):
        rows = sorted({i.row() for i in self.table.selectedIndexes()})
        return [self.table.item(r, 0).data(ROLE_ID) for r in rows]

    def _reload_categories(self):
        cur = self.f_category.currentText()
        self.f_category.blockSignals(True)
        self.f_category.clear()
        self.f_category.addItem("Tất cả phân loại")
        self.f_category.addItems(self.db.categories())
        i = self.f_category.findText(cur)
        self.f_category.setCurrentIndex(i if i >= 0 else 0)
        self.f_category.blockSignals(False)

    def refresh(self, *_):
        keep = set(self.selected_ids())
        self._reload_categories()
        pi, si, ci = (self.f_priority.currentIndex(), self.f_status.currentIndex(),
                      self.f_category.currentIndex())
        tasks = self.db.list_tasks(
            search=self.search.text(),
            priority=None if pi == 0 else pi - 1,
            status=None if si == 0 else STATUSES[si - 1],
            category=None if ci == 0 else self.f_category.currentText(),
            sort=self.SORTS[self.f_sort.currentIndex()][1],
        )
        self.table.setRowCount(len(tasks))
        va = Qt.AlignVCenter | Qt.AlignLeft
        for r, t in enumerate(tasks):
            it0 = QTableWidgetItem(t.title)
            it0.setData(ROLE_SUB, (t.description or "Không có mô tả").replace("\n", " "))
            it0.setData(ROLE_DONE, t.is_done)
            it0.setData(ROLE_ID, t.id)
            it1 = QTableWidgetItem(t.category)
            it2 = QTableWidgetItem(PRIORITIES[t.priority])
            it2.setData(ROLE_COLOR, PRIORITY_COLORS[t.priority])
            it3 = QTableWidgetItem(t.status)
            it3.setData(ROLE_COLOR, STATUS_COLORS[t.status])
            it4 = QTableWidgetItem(t.progress_label)
            it4.setData(ROLE_COLOR, t.progress)
            it5 = QTableWidgetItem(humanize_due(t))
            if t.is_overdue():
                it5.setForeground(QColor(T["danger"]))
            elif t.is_done:
                it5.setForeground(QColor(T["muted"]))
            for c, it in enumerate((it0, it1, it2, it3, it4, it5)):
                it.setTextAlignment(va)
                self.table.setItem(r, c, it)
            if t.id in keep:
                self.table.selectRow(r)
        self.count.setText(f"{len(tasks)} công việc")
        self.table.setVisible(bool(tasks))
        self.empty.setVisible(not tasks)

    # --------------------------------------------------------------- hành động
    def _edit_row(self, row: int):
        self.request_edit.emit(self.table.item(row, 0).data(ROLE_ID))

    def edit_selected(self):
        ids = self.selected_ids()
        if ids:
            self.request_edit.emit(ids[0])

    def delete_selected(self):
        ids = self.selected_ids()
        if not ids:
            return
        msg = "Xóa công việc đã chọn?" if len(ids) == 1 else f"Xóa {len(ids)} công việc đã chọn?"
        if QMessageBox.question(self, "Xác nhận xóa", msg, QMessageBox.Yes | QMessageBox.No,
                                QMessageBox.No) == QMessageBox.Yes:
            self.db.delete_tasks(ids)
            self.refresh()
            self.changed.emit()

    def complete_selected(self):
        ids = self.selected_ids()
        if not ids:
            return
        tasks = [self.db.get_task(i) for i in ids]
        if all(t.is_done for t in tasks):
            for t in tasks:
                self.db.reopen(t.id)
        else:
            for t in tasks:
                if not t.is_done:
                    self.db.mark_done(t.id)
        self.refresh()
        self.changed.emit()

    def _context_menu(self, pos):
        row = self.table.rowAt(pos.y())
        if row < 0:
            return
        if not self.table.item(row, 0).isSelected():
            self.table.selectRow(row)
        ids = self.selected_ids()
        menu = QMenu(self)
        a_edit = menu.addAction("✏️  Sửa công việc")
        a_done = menu.addAction("✓  Đánh dấu hoàn thành / mở lại")
        sub = menu.addMenu("🔄  Chuyển trạng thái")
        for st in STATUSES:
            sub.addAction(st).setData(st)
        menu.addSeparator()
        a_del = menu.addAction("🗑  Xóa")
        res = menu.exec(self.table.viewport().mapToGlobal(pos))
        if res is None:
            return
        if res is a_edit:
            self.request_edit.emit(ids[0])
        elif res is a_done:
            self.complete_selected()
        elif res is a_del:
            self.delete_selected()
        elif res.data() is not None:
            for i in ids:
                self.db.set_status(i, res.data())
            self.refresh()
            self.changed.emit()
