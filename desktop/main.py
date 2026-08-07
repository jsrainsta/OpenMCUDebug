"""MCU Debug Assistant 入口。

运行方式（在项目根目录）::

    python -m desktop.main
"""

import sys

from PyQt6.QtWidgets import QApplication

from desktop.ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
