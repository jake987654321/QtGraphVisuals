
import sys
from PySide6.QtWidgets import QApplication
from QtGraphVisuals import QGraphViewer

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("QtGraphVisuals Demo")

    viewer = QGraphViewer()
    viewer.show()

    sys.exit(app.exec())
