
import sys
import networkx as nx
from PySide6.QtCore import (Qt, Signal, Slot, QPoint, QPointF, QLine, QLineF,
        QRect, QRectF)
from PySide6.QtWidgets import (QApplication, QWidget, QLabel, QHBoxLayout,
        QVBoxLayout, QGraphicsView, QGraphicsScene, QGraphicsRectItem,
        QGraphicsEllipseItem, QGraphicsItem, QGraphicsTextItem, QGroupBox,
        QScrollArea, QFrame)
from PySide6.QtGui import QPainter, QTransform, QBrush, QPen, QColor

## Application
class GraphViewer(QWidget):
    def __init__(self, graph, parent=None):
        super().__init__(parent)

        # Children
        self._graph_viewer = GraphViewerWindow(graph, parent=self)
        self._properties_viewer = PropertiesViewer(parent=self)

        # Connections
        self._graph_viewer.clicked.connect(self._properties_viewer.setConfig)

        # Layout
        layout = QHBoxLayout()
        layout.addWidget(self._graph_viewer)
        layout.addWidget(self._properties_viewer)
        self.setLayout(layout)

    def setGraph(self, graph):
        self._graph_viewer.setGraph(graph)

class PropertiesViewer(QGroupBox):
    def __init__(self, config={}, parent=None): 
        super().__init__(parent)

        # Configure
        self.setLayout(QVBoxLayout())
        self.setMinimumHeight(300)
        self.setMaximumWidth(300)
        self.setTitle('Properties')

        self.scroll = QScrollArea(parent=self)
        self.scroll.setWidgetResizable(True)

        self.group = QWidget(parent=self.scroll)
        self.group.setLayout(QVBoxLayout())

        self.property_text_boxes = [PropertyViewerTextBox(parent=self.group) for i in range(30)]
        [p.setVisible(False) for p in self.property_text_boxes]

        [self.group.layout().addWidget(p) for p in self.property_text_boxes]
        self.group.layout().setAlignment(Qt.AlignTop)

        self.scroll.setWidget(self.group)
        self.layout().addWidget(self.scroll)

        self.setConfig(config)

    @Slot(dict)
    def setConfig(self, config):
        [p.setVisible(False) for p in self.property_text_boxes]

        if not config: 
            return 

        # Create 
        for i,(k,v) in enumerate(config.items()):
            if i > 30:
                break

            self.property_text_boxes[i].set(k,v)
            self.property_text_boxes[i].setVisible(True)
        self.show()

class PropertyViewerTextBox(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._name = QLabel()
        self._name.setMinimumWidth(100)
        self._name.setMaximumWidth(100)

        self._value = QLabel()
        self._value.setStyleSheet("QLabel {background: rgb(49, 54, 59); border-radius: 3px;} ")
        self._value.setFixedHeight(24)
        self._value.setIndent(3)
        self._value.setTextInteractionFlags(Qt.TextSelectableByMouse)

        layout = QHBoxLayout()
        layout.addWidget(self._name)
        layout.addWidget(self._value)
        layout.setContentsMargins(0,0,0,0)
        self.setLayout(layout)

    def set(self, name, value):
        self._name.setText(f"{name}")
        self._value.setText(f"{value}")

# Graph Viewer
class GraphViewerWindow(QGraphicsView):
    clicked = Signal(tuple)


    def __init__(self, graph=None, parent=None):
        super().__init__(parent)
        self._graph = graph

        # Configure QGraphicsView
        self.setTransformationAnchor(QGraphicsView.NoAnchor)
        self.setResizeAnchor(QGraphicsView.NoAnchor)
        self.setHorizontalScrollBarPolicy( Qt.ScrollBarAlwaysOff )
        self.setVerticalScrollBarPolicy( Qt.ScrollBarAlwaysOff )
        self.setRenderHints(QPainter.Antialiasing)

        # Create/Configure the Scene
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)

        self._vgraph = None
        self.setGraph(self._graph)

        # Set scene bounding rect
        self.scene().setSceneRect(self.scene().itemsBoundingRect())

        # State
        self._dragging = False
        self._selected = None

        # Center the Scene
        self.centerScene()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            item = self.itemAt(e.position().toPoint())
            if item and not isinstance(item, VisualGraph):
                self._selected = item
            else:
                self._selected = None

            self._dragging = True
            self._last_drag_pos = e.position()
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._dragging = False
            self.setCursor(Qt.ArrowCursor)
            if self._selected:
                self.clicked.emit(self._selected.get_properties())
                #self.scene().setSceneRect(self.scene().itemsBoundingRect())
        super().mouseReleaseEvent(e)

    def mouseMoveEvent(self, e):
        if self._dragging:
            if self._selected:
                pos = self.mapToScene(e.position().toPoint()) - self._selected.boundingRect().center()
                self._selected.setPos(pos)
                #self._vgraph.update()
            else:
                p0 = self.mapToScene(e.position().toPoint())
                p1 = self.mapToScene(self._last_drag_pos.toPoint())
                delta = p0 - p1 

                self.translate(delta.x(), delta.y())
                self._last_drag_pos = QPointF(e.position())

        super().mouseMoveEvent(e)

    def wheelEvent(self, e):
        zoom_in_factor = 1.15
        zoom_out_factor = 1 / zoom_in_factor
        if e.angleDelta().y() > 0:
            zf = zoom_in_factor
        else:
            zf = zoom_out_factor

        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.scale(zf,zf)
        self.setTransformationAnchor(QGraphicsView.NoAnchor)

    def centerScene(self):
        p0 = self.mapToScene(*self.centerOfView()) 
        self.setTransform(QTransform().translate(p0.x(), p0.y()), combine=True)

    def centerOfView(self):
        return (self.size().width()-1)/2, (self.size().height()-1)/2

    def setGraph(self, graph):
        self.scene().clear()

        self._graph = graph
        self._vgraph = VisualGraph(graph)
        self.scene().addItem(self._vgraph)
        self.scene().setSceneRect(self.scene().itemsBoundingRect())

        # reset-state
        self._dragging = False
        self._selected = None

        # Center the Scene
        self.centerScene()

class VisualGraph(QGraphicsItem):
    def __init__(self, graph=None, parent=None):
        super().__init__(parent=parent)

        # Drawing Config
        self.node_size = 50
        self.y_spacing = 2*self.node_size
        self.x_spacing = 2*self.node_size

        self.brush = QBrush(Qt.darkGreen)
        self.pen = QPen(Qt.black, 2)

        # State 
        self._graph = graph
        self._node_to_vnode_map = {}

        if graph:
            self.setGraph(graph)
        self._bounding_rect = self.childrenBoundingRect()

    def calculate_positions(self):
        x, y = 0, 0
        positions = {}
        for generation in nx.topological_generations(self._graph):
            x = 0
            for node in generation:
                positions[node] = (x,y)
                x += self.x_spacing
            y += self.y_spacing
        return positions

    def create_visual_nodes(self, positions):
        for node,pos in positions.items():
            l,t = pos[0]-self.node_size/2, pos[1]-self.node_size/2
            self._node_to_vnode_map[node] = VisualNode(node, QPointF(l,t),
                    QPointF(self.node_size,self.node_size), self.pen,
                    self.brush, parent=self)

    def paint(self, painter, option, widget=None):
        if not self._graph:
            return

        for x,y in self._graph.edges:
            self.paintEdge(x, y, painter) 

    def paintEdge(self, from_node, to_node, painter):
        n0, n1 = self._node_to_vnode_map[from_node], self._node_to_vnode_map[to_node]
        n0_center = n0.pos() + n0.boundingRect().center()
        n1_center = n1.pos() + n1.boundingRect().center()
        line = QLineF(n1_center, n0_center)

        c = line.center()
        u = line.unitVector().p1() - line.unitVector().p2()

        arrow_left = QLineF(c+3*u, c-3*u)
        arrow_left.setAngle(line.angle()+30)

        arrow_right = QLineF(c+3*u, c-3*u)
        arrow_right.setAngle(line.angle()-30)

        painter.drawLine(line)
        painter.drawLine(arrow_left)
        painter.drawLine(arrow_right)

    def boundingRect(self):
        return self._bounding_rect

    def childrenMoved(self):
        self._bounding_rect = self.childrenBoundingRect()
        self.update()

    def setGraph(self, graph):
        if not isinstance(graph, nx.DiGraph):
            raise ValueError()
        self._graph = graph
        positions = self.calculate_positions()
        self.create_visual_nodes(positions)
        self._bounding_rect = self.childrenBoundingRect()

class VisualNode(QGraphicsItem):
    def __init__(self, node, pos, size, pen, brush, parent=None):
        super().__init__(parent)
        # Keep reference to node
        self.node = node

        # set node outline
        self.shell = QGraphicsEllipseItem(0, 0, size.x(), size.y(), parent=self)
        self.shell.setPen(pen)
        self.shell.setBrush(brush)
        self.shell.setFlag(QGraphicsItem.ItemStacksBehindParent, enabled=True)

        # set text
        self.text = QGraphicsTextItem(str(node), parent=self)
        self.text.setPos(self.shell.boundingRect().center() - self.text.boundingRect().center())
        self.text.setFlag(QGraphicsItem.ItemStacksBehindParent, enabled=True)
        self.text.setDefaultTextColor(Qt.white)

        self.setPos(pos - self.boundingRect().center())

    def get_properties(self):
        if hasattr(self.node, 'get_config'):
            return self.node.get_config()
        else:
            return {'type': type(self.node).__name__, 'name': self.node}

    def paint(self, painter, option, widget=None):
        pass

    def boundingRect(self):
        return self.childrenBoundingRect() 

    def setPos(self, pos):
        super().setPos(pos)
        self.parentItem().childrenMoved()

    def mousePressEvent(self, e):
        super().mousePressEvent(e)

class GraphLayout:
    def __init__(self):
        pass

