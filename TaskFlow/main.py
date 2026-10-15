"""TaskFlow - Ứng dụng quản lý công việc cá nhân (PySide6 + SQLite)."""
import sys

from PySide6.QtWidgets import QApplication

from app.database import Database
from app.icon import make_app_icon
from app.ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("TaskFlow")
    app.setStyle("Fusion")
    app.setWindowIcon(make_app_icon())
    db = Database()
    window = MainWindow(db)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
