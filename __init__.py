from QtGraphVisuals.widgets import GraphViewerWindow as QGraphViewerWindow
from QtGraphVisuals.widgets import GraphViewer as QGraphViewer

def quick_view(graph_dict):
    import sys
    from PySide6.QtWidgets import QApplication
    from qt_material import apply_stylesheet

    if not QApplication.instance():
        app = QApplication(sys.argv)
        extra={ "secondaryDarkColor":"#232629", "font_size": '15px',}
        apply_stylesheet(app, theme='dark_blue.xml', extra=extra)
        app.setApplicationName("QtGraphVisuals QuickView")
    else:
        app = QApplication.instance()

    gv= QGraphViewer(graph_dict)
    gv.resize(800,600)
    gv.show()
    app.exec()

