
import sys
from PySide6.QtWidgets import QApplication
from QtGraphVisuals import QGraphViewer
from qt_material import apply_stylesheet
import networkx as nx

# Temporary graph generation function
def graph1():
    return nx.MultiDiGraph([(1,2), (1,3), (2,4), (3,4), (4,5), (2,5)])

def graph2():
    return nx.MultiDiGraph([(1,2), (1,3), (1,4)])

if __name__ == "__main__":

    app = QApplication(sys.argv)
    app.setApplicationName("QtGraphVisuals Demo")

    extra={ "secondaryDarkColor":"#232629", "font_size": '15px',}
    apply_stylesheet(app, theme='dark_blue.xml', extra=extra)

    viewer = QGraphViewer({'graph1': graph1(), 'graph2':graph2()})
    viewer.resize(800,600)
    viewer.show()

    sys.exit(app.exec())
