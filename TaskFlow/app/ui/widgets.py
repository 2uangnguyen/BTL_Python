"""Các widget dùng chung: thẻ thống kê, biểu đồ vẽ tay, thông báo nổi..."""
from __future__ import annotations

from PySide6.QtCore import QLineF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget,
)

from ..styles import T


# ----------------------------------------------------------------- helpers
def rgba(hex_color: str, alpha: int = 40) -> str:
    c = QColor(hex_color)
    return f"rgba({c.red()},{c.green()},{c.blue()},{alpha})"


def clear_layout(layout):
    while layout.count():
        item = layout.takeAt(0)
        w = item.widget()
        if w is not None:
            w.setParent(None)
            w.deleteLater()
        elif item.layout() is not None:
            clear_layout(item.layout())
            item.layout().deleteLater()


def add_shadow(w: QWidget, blur: int = 26, dy: int = 4, alpha: int = 26):
    e = QGraphicsDropShadowEffect(w)
    e.setBlurRadius(blur)
    e.setOffset(0, dy)
    e.setColor(QColor(15, 23, 42, alpha))
    w.setGraphicsEffect(e)


def chip(text: str, color: str) -> QLabel:
    lb = QLabel(text)
    lb.setAlignment(Qt.AlignCenter)
    lb.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
    lb.setStyleSheet(
        f"background:{rgba(color, 36)};color:{color};border-radius:10px;"
        "padding:3px 10px;font-size:11px;font-weight:700;")
    return lb


def dot_icon(color: str) -> QIcon:
    pm = QPixmap(14, 14)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setBrush(QColor(color))
    p.setPen(Qt.NoPen)
    p.drawEllipse(1, 1, 12, 12)
    p.end()
    return QIcon(pm)


def make_panel(title: str, subtitle: str = ""):
    f = QFrame()
    f.setObjectName("card")
    v = QVBoxLayout(f)
    v.setContentsMargins(20, 18, 20, 18)
    v.setSpacing(10)
    t = QLabel(title)
    t.setObjectName("panelTitle")
    v.addWidget(t)
    if subtitle:
        s = QLabel(subtitle)
        s.setObjectName("muted")
        v.addWidget(s)
    add_shadow(f)
    return f, v


# ----------------------------------------------------------- clickable bits
class ClickableFrame(QFrame):
    clicked = Signal()

    def __init__(self, *a):
        super().__init__(*a)
        self.setCursor(Qt.PointingHandCursor)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self.rect().contains(e.position().toPoint()):
            self.clicked.emit()
        super().mouseReleaseEvent(e)


class ClickableLabel(QLabel):
    clicked = Signal()

    def __init__(self, *a):
        super().__init__(*a)
        self.setCursor(Qt.PointingHandCursor)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self.rect().contains(e.position().toPoint()):
            self.clicked.emit()
        super().mouseReleaseEvent(e)


# ---------------------------------------------------------------- stat card
class StatCard(QFrame):
    def __init__(self, icon: str, title: str, color: str):
        super().__init__()
        self.setObjectName("card")
        h = QHBoxLayout(self)
        h.setContentsMargins(18, 16, 18, 16)
        h.setSpacing(14)
        ic = QLabel(icon)
        ic.setFixedSize(50, 50)
        ic.setAlignment(Qt.AlignCenter)
        ic.setStyleSheet(f"background:{rgba(color, 36)};border-radius:15px;font-size:22px;")
        h.addWidget(ic)
        v = QVBoxLayout()
        v.setSpacing(0)
        self.value = QLabel("0")
        self.value.setObjectName("statValue")
        self.title = QLabel(title)
        self.title.setObjectName("muted")
        self.hint = QLabel("")
        self.hint.setObjectName("muted")
        self.hint.setStyleSheet("font-size:11px;")
        v.addWidget(self.value)
        v.addWidget(self.title)
        v.addWidget(self.hint)
        h.addLayout(v, 1)
        add_shadow(self)

    def set_value(self, value, hint: str = ""):
        self.value.setText(str(value))
        self.hint.setText(hint)
        self.hint.setVisible(bool(hint))


# ------------------------------------------------------------------ charts
class DonutChart(QWidget):
    def __init__(self):
        super().__init__()
        self.data, self.center, self.sub = [], "", ""
        self.setMinimumSize(170, 170)

    def set_data(self, data, center: str, sub: str):
        self.data, self.center, self.sub = data, center, sub
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        side = min(self.width(), self.height()) - 16
        thick = side * 0.15
        rect = QRectF((self.width() - side) / 2, (self.height() - side) / 2, side, side)
        r = rect.adjusted(thick / 2, thick / 2, -thick / 2, -thick / 2)
        p.setPen(QPen(QColor(T["border"]), thick))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(r)
        total = sum(v for _, v, _ in self.data)
        if total > 0:
            angle = 90 * 16
            for _, val, color in self.data:
                if val <= 0:
                    continue
                span = -round(360 * 16 * val / total)
                pen = QPen(QColor(color), thick)
                pen.setCapStyle(Qt.FlatCap)
                p.setPen(pen)
                p.drawArc(r, angle, span)
                angle += span
        f = QFont(self.font())
        f.setPixelSize(int(side * 0.2))
        f.setBold(True)
        p.setFont(f)
        p.setPen(QColor(T["text"]))
        p.drawText(QRectF(rect.x(), rect.y() + side * 0.28, side, side * 0.25), Qt.AlignCenter, self.center)
        f.setPixelSize(12)
        f.setBold(False)
        p.setFont(f)
        p.setPen(QColor(T["muted"]))
        p.drawText(QRectF(rect.x(), rect.y() + side * 0.52, side, 20), Qt.AlignCenter, self.sub)


class BarChart(QWidget):
    def __init__(self):
        super().__init__()
        self.data = []
        self.setMinimumHeight(190)

    def set_data(self, data):
        self.data = data
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        area = QRectF(6, 24, w - 12, h - 24 - 26)
        mx = max([v for _, v, _ in self.data] + [1])
        pen = QPen(QColor(T["border"]), 1, Qt.DashLine)
        for i in range(4):
            y = area.bottom() - area.height() * i / 3
            p.setPen(pen)
            p.drawLine(QLineF(area.left(), y, area.right(), y))
        n = len(self.data)
        if not n:
            return
        f = QFont(self.font())
        f.setPixelSize(11)
        p.setFont(f)
        slot = area.width() / n
        bw = min(42.0, slot * 0.55)
        for i, (label, val, color) in enumerate(self.data):
            x = area.left() + slot * i + (slot - bw) / 2
            bh = area.height() * val / mx
            p.setPen(Qt.NoPen)
            if val > 0:
                p.setBrush(QColor(color))
                p.drawRoundedRect(QRectF(x, area.bottom() - bh, bw, bh), 6, 6)
                p.setPen(QColor(T["text"]))
                p.drawText(QRectF(x - 10, area.bottom() - bh - 20, bw + 20, 18), Qt.AlignCenter, str(val))
            else:
                p.setBrush(QColor(T["border"]))
                p.drawRoundedRect(QRectF(x, area.bottom() - 4, bw, 4), 2, 2)
            p.setPen(QColor(T["muted"]))
            p.drawText(QRectF(area.left() + slot * i, area.bottom() + 6, slot, 18), Qt.AlignCenter, label)


class MiniBar(QWidget):
    def __init__(self, value: float = 0, color: str = "#6366F1"):
        super().__init__()
        self.value, self.color = value, color
        self.setFixedHeight(8)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        r = QRectF(0, 0, self.width(), self.height())
        p.setBrush(QColor(T["border"]))
        p.drawRoundedRect(r, 4, 4)
        if self.value > 0:
            p.setBrush(QColor(self.color))
            p.drawRoundedRect(QRectF(0, 0, max(8.0, r.width() * self.value / 100), r.height()), 4, 4)


# -------------------------------------------------------------------- toast
class Toast(QFrame):
    """Thông báo nổi ở góc dưới bên phải cửa sổ."""

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setObjectName("toast")
        self.setFixedWidth(350)
        v = QVBoxLayout(self)
        v.setContentsMargins(18, 14, 18, 16)
        v.setSpacing(4)
        self.title = QLabel()
        self.title.setObjectName("toastTitle")
        self.msg = QLabel()
        self.msg.setObjectName("muted")
        self.msg.setWordWrap(True)
        v.addWidget(self.title)
        v.addWidget(self.msg)
        add_shadow(self, 30, 6, 60)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.hide)
        self.setCursor(Qt.PointingHandCursor)
        self.hide()

    def show_message(self, title: str, msg: str, kind: str = "info"):
        color = {"danger": T["danger"], "warning": T["warning"],
                 "success": T["success"]}.get(kind, T["primary"])
        self.setStyleSheet(
            f"QFrame#toast{{background:{T['surface']};border:1px solid {T['border']};"
            f"border-left:5px solid {color};border-radius:12px;}}")
        self.title.setText(title)
        self.msg.setText(msg)
        self.setFixedHeight(self.layout().totalHeightForWidth(self.width()))
        self.reposition()
        self.show()
        self.raise_()
        self.timer.start(9000)

    def reposition(self):
        p = self.parentWidget()
        if p:
            self.move(p.width() - self.width() - 24, p.height() - self.height() - 24)

    def mousePressEvent(self, _):
        self.hide()
