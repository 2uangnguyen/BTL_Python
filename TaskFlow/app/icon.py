"""Biểu tượng ứng dụng được vẽ bằng code (không cần file ảnh)."""
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap


def make_app_icon() -> QIcon:
    size = 256
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    g = QLinearGradient(0, 0, size, size)
    g.setColorAt(0, QColor("#6366F1"))
    g.setColorAt(1, QColor("#8B5CF6"))
    p.setBrush(g)
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(QRectF(12, 12, size - 24, size - 24), 58, 58)
    path = QPainterPath()
    path.moveTo(QPointF(76, 134))
    path.lineTo(QPointF(112, 170))
    path.lineTo(QPointF(182, 92))
    pen = QPen(QColor("white"), 26, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    p.drawPath(path)
    p.end()
    return QIcon(pm)
