"""Giao diện: bảng màu sáng/tối và stylesheet (QSS)."""
from pathlib import Path
from string import Template

from PySide6.QtGui import QColor, QPalette

LIGHT = dict(
    name="light", bg="#F4F6FB", surface="#FFFFFF", surface2="#F6F8FC", text="#0F172A",
    muted="#64748B", border="#E4E9F2", accent_text="#4F46E5", accent_soft="#EEF0FF",
    sidebar="#FFFFFF", sel="#EEF0FF", primary="#6366F1", primary_hover="#4F46E5",
    danger="#EF4444", success="#22C55E", warning="#F59E0B",
)
DARK = dict(
    name="dark", bg="#0B1120", surface="#141C2F", surface2="#1A2338", text="#E5E9F2",
    muted="#8D9BB5", border="#26324A", accent_text="#A5B4FC", accent_soft="#222B55",
    sidebar="#0F1729", sel="#222B55", primary="#6366F1", primary_hover="#7C7FF5",
    danger="#F87171", success="#34D399", warning="#FBBF24",
)

CHECK_ICON = (Path(__file__).resolve().parent / "assets" / "check.png").as_posix()
LIGHT["check_icon"] = DARK["check_icon"] = CHECK_ICON

T = dict(LIGHT)  # theme hiện tại (được cập nhật tại chỗ)

PRIORITY_COLORS = {0: "#22C55E", 1: "#3B82F6", 2: "#F59E0B", 3: "#EF4444"}
STATUS_COLORS = {"Chưa bắt đầu": "#94A3B8", "Đang thực hiện": "#6366F1", "Hoàn thành": "#22C55E"}


def set_theme(name: str):
    T.clear()
    T.update(DARK if name == "dark" else LIGHT)


def make_palette() -> QPalette:
    p = QPalette()
    p.setColor(QPalette.Window, QColor(T["bg"]))
    p.setColor(QPalette.WindowText, QColor(T["text"]))
    p.setColor(QPalette.Base, QColor(T["surface"]))
    p.setColor(QPalette.AlternateBase, QColor(T["surface2"]))
    p.setColor(QPalette.Text, QColor(T["text"]))
    p.setColor(QPalette.Button, QColor(T["surface"]))
    p.setColor(QPalette.ButtonText, QColor(T["text"]))
    p.setColor(QPalette.ToolTipBase, QColor(T["surface"]))
    p.setColor(QPalette.ToolTipText, QColor(T["text"]))
    p.setColor(QPalette.Highlight, QColor(T["primary"]))
    p.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
    p.setColor(QPalette.PlaceholderText, QColor(T["muted"]))
    return p


_QSS = Template(r"""
* { font-family: "Segoe UI", "Inter", "Noto Sans", "Helvetica Neue", Arial, sans-serif; font-size: 13px; }
QMainWindow, QDialog { background: $bg; }
QWidget#content { background: $bg; }
QLabel { background: transparent; color: $text; }
QLabel#muted { color: $muted; }
QLabel#h1 { font-size: 26px; font-weight: 800; }
QLabel#h2 { font-size: 20px; font-weight: 700; }
QLabel#panelTitle { font-size: 15px; font-weight: 700; }
QLabel#statValue { font-size: 28px; font-weight: 800; }
QLabel#brand { font-size: 19px; font-weight: 800; }
QLabel#toastTitle { font-size: 14px; font-weight: 700; }
QLabel#error { color: $danger; font-weight: 600; }

QScrollArea { background: transparent; border: none; }
QScrollArea > QWidget > QWidget { background: transparent; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: $border; border-radius: 4px; min-height: 32px; }
QScrollBar::handle:vertical:hover { background: $muted; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px; }
QScrollBar::handle:horizontal { background: $border; border-radius: 4px; min-width: 32px; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }

QFrame#sidebar { background: $sidebar; border: none; border-right: 1px solid $border; }
QFrame#card { background: $surface; border: 1px solid $border; border-radius: 16px; }
QFrame#taskcard { background: $surface; border: 1px solid $border; border-radius: 12px; }
QFrame#taskcard:hover { border: 1px solid $primary; }
QFrame#rowitem { background: transparent; border: none; border-radius: 10px; }
QFrame#rowitem:hover { background: $surface2; }
QFrame#daycol { background: $surface; border: 1px solid $border; border-radius: 14px; }
QFrame#daycol[today="true"] { border: 2px solid $primary; }
QFrame#colhead { background: transparent; border: none; border-radius: 10px; }
QFrame#colhead:hover { background: $surface2; }
QFrame#daycell { background: $surface; border: 1px solid $border; border-radius: 10px; }
QFrame#daycell:hover { border: 1px solid $primary; }
QFrame#daycell[dim="true"] { background: $surface2; }
QFrame#daycell[today="true"] { border: 2px solid $primary; background: $accent_soft; }

QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QDateEdit, QDateTimeEdit, QSpinBox {
    background: $surface; border: 1px solid $border; border-radius: 9px; padding: 7px 10px;
    color: $text; selection-background-color: $primary; selection-color: white; }
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus,
QDateEdit:focus, QDateTimeEdit:focus, QSpinBox:focus { border: 1px solid $primary; }
QLineEdit:disabled, QDateTimeEdit:disabled, QComboBox:disabled { background: $surface2; color: $muted; }
QComboBox QLineEdit { border: none; padding: 0; background: transparent; }
QComboBox QAbstractItemView { background: $surface; border: 1px solid $border; outline: 0;
    selection-background-color: $accent_soft; selection-color: $accent_text; padding: 4px; }

QPushButton { background: $surface; color: $text; border: 1px solid $border; border-radius: 9px;
    padding: 8px 16px; min-height: 18px; font-weight: 600; }
QPushButton:hover { background: $surface2; border-color: $muted; }
QPushButton:pressed { background: $border; }
QPushButton#primary { background: $primary; color: white; border: 1px solid $primary; }
QPushButton#primary:hover { background: $primary_hover; border-color: $primary_hover; }
QPushButton#danger { color: $danger; border: 1px solid $danger; background: transparent; }
QPushButton#danger:hover { background: $danger; color: white; }
QPushButton#iconbtn { padding: 6px 12px; font-size: 15px; }
QPushButton#nav { text-align: left; padding: 12px 16px; border: none; border-radius: 11px;
    background: transparent; color: $muted; font-size: 14px; }
QPushButton#nav:hover { background: $surface2; color: $text; }
QPushButton#nav:checked { background: $accent_soft; color: $accent_text; }
QPushButton#seg { border: none; background: transparent; color: $muted; padding: 7px 20px; border-radius: 8px; }
QPushButton#seg:hover { color: $text; background: transparent; }
QPushButton#seg:checked { background: $primary; color: white; }

QCheckBox { spacing: 8px; background: transparent; color: $text; }
QCheckBox::indicator { width: 18px; height: 18px; border-radius: 6px; border: 2px solid $border; background: $surface; }
QCheckBox::indicator:hover { border-color: $primary; }
QCheckBox::indicator:checked { background: $success; border: 2px solid $success; image: url("$check_icon"); }

QSlider::groove:horizontal { height: 6px; background: $border; border-radius: 3px; }
QSlider::sub-page:horizontal { background: $primary; border-radius: 3px; }
QSlider::handle:horizontal { background: white; border: 2px solid $primary; width: 14px; height: 14px;
    margin: -6px 0; border-radius: 9px; }

QTableWidget { background: transparent; border: none; gridline-color: transparent;
    alternate-background-color: $surface2; outline: 0; selection-background-color: $sel; selection-color: $text; }
QTableWidget::item { padding: 0 10px; border: none; }
QTableWidget::item:selected { background: $sel; color: $text; }
QHeaderView { background: transparent; }
QHeaderView::section { background: transparent; color: $muted; border: none;
    border-bottom: 1px solid $border; padding: 10px 10px; font-weight: 700; font-size: 12px; }
QTableCornerButton::section { background: transparent; border: none; }

QMenu { background: $surface; border: 1px solid $border; border-radius: 10px; padding: 6px; }
QMenu::item { padding: 8px 24px 8px 16px; border-radius: 6px; color: $text; }
QMenu::item:selected { background: $accent_soft; color: $accent_text; }
QMenu::separator { height: 1px; background: $border; margin: 6px 10px; }
QToolTip { background: $surface; color: $text; border: 1px solid $border; padding: 5px 8px; }
QMessageBox { background: $surface; }
QCalendarWidget QWidget { background: $surface; color: $text; }
QCalendarWidget QAbstractItemView:enabled { selection-background-color: $primary; selection-color: white; }
""")


def qss() -> str:
    return _QSS.substitute(T)
