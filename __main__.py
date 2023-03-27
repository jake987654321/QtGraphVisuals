
import sys
from PySide6.QtWidgets import QApplication
from QtGraphVisuals import QGraphViewer
from qt_material import apply_stylesheet
import networkx as nx

# Temporary graph generation function
def graph():
    edge_list = []
    edge_list.append( (1,2) )
    edge_list.append( (1,3) )
    edge_list.append( (2,4) )
    edge_list.append( (3,4) )
    edge_list.append( (4,5) )
    edge_list.append( (2,5) )

    return nx.DiGraph(edge_list)

if __name__ == "__main__":

    app = QApplication(sys.argv)
    app.setApplicationName("QtGraphVisuals Demo")

    extra={ "secondaryDarkColor":"#232629", "font_size": '15px',}
    apply_stylesheet(app, theme='dark_blue.xml', extra=extra)

    viewer = QGraphViewer(graph())
    viewer.show()

    sys.exit(app.exec())
