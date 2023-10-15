
import networkx as nx
import numpy as np

from PySide6.QtCore import (Qt, Signal, Slot, QPoint, QPointF, QLine, QLineF,
        QRect, QRectF, QSize) 
from PySide6.QtWidgets import (QApplication, QWidget, QLabel, QHBoxLayout, QPushButton, QSizePolicy,
        QVBoxLayout, QGraphicsView, QGraphicsScene, QGraphicsPolygonItem, QGraphicsRectItem,
        QGraphicsEllipseItem, QGraphicsItem, QGraphicsTextItem, QGraphicsPathItem, QGraphicsLineItem, QGroupBox,
        QScrollArea, QFrame, QTabWidget, QSplitter)
from PySide6.QtGui import QPainterPath, QPainter, QTransform, QBrush, QPen, QColor, QPolygonF, QFont, QIcon, QPixmap

class VisualGraph(QGraphicsItem):
    def __init__(self, graph=None, vertical=False, show_text=True, circle_nodes=True, parent=None):
        super().__init__(parent=parent)
        # State
        self.show_text = show_text
        self.circle_nodes = circle_nodes
        self.horizontal = not vertical

        # Drawing Config
        self.node_size = 75
        self.y_spacing = 1.25*self.node_size
        self.x_spacing = 1.25*self.node_size

        self.brush = QBrush(Qt.darkGreen)
        self.pen = QPen(Qt.black, 2)

        # State 
        self._graph = graph
        self._node_to_vnode_map = {}
        self._edge_to_vedge_map = {}

        self._generation_map = {}

        if graph:
            self.setGraph(graph)
        self._bounding_rect = self.childrenBoundingRect()

    def getNodeCenterOfMass(self):
        x_tot, y_tot = 0, 0 
        num_nodes = len(self._node_to_vnode_map.values())
        for vnode in self._node_to_vnode_map.values():
            p0 = vnode.center()
            x_tot = p0.x()
            y_tot = p0.y()

        return QPointF(x_tot / num_nodes, y_tot / num_nodes)

    def getProperties(self):
        defaults = {'number of nodes': self._graph.number_of_nodes(), 'number of edges': self._graph.number_of_edges()}
        return self._graph.graph.get('properties', defaults) 

    def setNodeText(self, visible=True):
        for node in self._node_to_vnode_map.values():
            node.text.setVisible(visible)

    def calculate_positions(self):
        x, y = 0, 0
        positions = {}
        self._generation_map = {}
        for i, generation in enumerate(nx.topological_generations(self._graph)):
            N, S = len(generation), self.x_spacing
            xs = np.arange(N)*S - (N-1)/2*S 
            for node,x in zip(generation,xs):
                self._generation_map[node] = i
                positions[node] = [x,y]
            y += self.y_spacing

        for generation in list(nx.topological_generations(self._graph)):
            ideal_x = []
            for node in generation:
                out_node_x = [positions[out_node][0] for out_node in self._graph.predecessors(node)]
                if out_node_x:
                    ideal_x.append(np.average(out_node_x))
                else:
                    ideal_x.append(positions[node][0])

            for i in range(len(ideal_x[:-1])):
                xdelta = ideal_x[i+1] - ideal_x[i]
                if xdelta < self.x_spacing:
                    for j in range(len(ideal_x)):
                        if j <= i:
                            ideal_x[j] -= (self.x_spacing - xdelta)
                        else:
                            ideal_x[j] += (self.x_spacing - xdelta)

            for i,node in enumerate(generation):
                positions[node][0] = ideal_x[i]

        return positions

    def create_visual_nodes(self, positions):
        for node,pos in positions.items():
            if self.horizontal:
                l,t = pos[1]-self.node_size/2, pos[0]-self.node_size/2
            else:
                l,t = pos[0]-self.node_size/2, pos[1]-self.node_size/2

            visual_scheme = self._graph.nodes[node].get('visual_scheme', {})
            self._node_to_vnode_map[node] = VisualNode(node, QPointF(l,t),
                    visual_scheme, self.circle_nodes, parent=self)

    def create_visual_edges(self):
        self._edge_to_vedge_map.clear()
        for u,v,key,data in self._graph.edges(keys=True, data=True):
            self._edge_to_vedge_map[(u,v,key)] = VisualEdge((u,v,key,data), parent=self)

    def paint(self, painter, option, widget=None):
        #painter.setBrush(self.brush)
        #painter.drawRoundedRect(self.boundingRect(), 5, 5)

        if not self._graph:
            return

        for x,y,_ in self._graph.edges:
            pass
            #self.paintEdge(x, y, painter) 

    def paintEdge(self, from_node, to_node, painter):
        n0, n1 = self._node_to_vnode_map[from_node], self._node_to_vnode_map[to_node]
        n0_center = n0.pos() + n0.boundingRect().center()
        n1_center = n1.pos() + n1.boundingRect().center()
        t, b = n0_center.y(), n1_center.y()
        l, r = n0_center.x(), n1_center.x()

        generational_gap = self._generation_map[to_node] - self._generation_map[from_node]
        if  generational_gap > 1 and abs(l - r) < self.x_spacing/4:
            w = self.x_spacing * generational_gap/4 
            rect = QRectF(l-w/2, t, w, b-t)
            start, span = 90*16, np.sign(l-r+0.001)*180*16
            painter.drawArc(rect, start, span)

        else:

            line = QLineF(n1_center, n0_center)
            painter.drawLine(line)

            c = line.center()
            u = line.unitVector().p1() - line.unitVector().p2()

            # Arrow head
            arrow_left = QLineF(c+3*u, c-3*u)
            arrow_left.setAngle(line.angle()+30)

            arrow_right = QLineF(c+3*u, c-3*u)
            arrow_right.setAngle(line.angle()-30)

            painter.setPen(Qt.white)
            painter.drawLine(arrow_left)
            painter.drawLine(arrow_right)

    def boundingRect(self):
        #br = self.childrenBoundingRect()
        #size = QPointF(br.width(), br.height())
        #return QRectF(br.center()-size*2, br.center()+size*2)#self._bounding_rect
        return self.childrenBoundingRect()

    def childrenMoved(self, child):
        self._bounding_rect = self.childrenBoundingRect()
        self.update_adjacent_edges(child.node)
        #self.update()

    def update_adjacent_edges(self, node):
        for u,v,idx in self._graph.in_edges(node, keys=True):
            self._edge_to_vedge_map[(u,v,idx)].updatePath()

        for u,v,idx in self._graph.out_edges(node, keys=True):
            self._edge_to_vedge_map[(u,v,idx)].updatePath()

    def setGraph(self, graph):
        self._graph = nx.MultiDiGraph(graph)
        positions = self.calculate_positions()
        self.create_visual_nodes(positions)
        self.create_visual_edges()
        self._bounding_rect = self.childrenBoundingRect()

class VisualEdge(QGraphicsItem):
    class ArrowHead(QGraphicsItem):
        def __init__(self, parent=None):
            super().__init__(parent=parent)
            line = QLineF(QPointF(-3,0), QPointF(3,0))
            line.setAngle(30)
            self.arrow_up = QGraphicsLineItem (line, parent=self)
            self.arrow_up.setPen(QPen(Qt.white))

            line = QLineF(QPointF(-3,0), QPointF(3,0))
            line.setAngle(-30)
            self.arrow_down = QGraphicsLineItem (line, parent=self)
            self.arrow_down.setPen(QPen(Qt.white))

            self.arrow_up.setFlag(QGraphicsItem.ItemStacksBehindParent, enabled=True)
            self.arrow_down.setFlag(QGraphicsItem.ItemStacksBehindParent, enabled=True)

        def setHovering(self, state):
            if state:
                self.parentItem().path.setPen(QPen(Qt.red))
                self.parentItem().text.setVisible(True)
                self.setPen(QPen(Qt.red))
            else:
                self.parentItem().path.setPen(QPen(Qt.white))
                self.parentItem().text.setVisible(False)
                self.setPen(QPen(Qt.white))
            self.parentItem().update()

        def setPen(self, pen):
            self.arrow_up.setPen(pen)
            self.arrow_down.setPen(pen)

        def paint(self, painter, option, widget=None):
            pass

        def boundingRect(self):
            return self.childrenBoundingRect()

    class Arc(QGraphicsItem):
        def __init__(self, parent=None):
            super().__init__(parent=parent)
            self.rect = QRectF()
            self.pen = QPen()
            self.orientation = True

        def setOrientation(self, ori):
            self.orientation = ori

        def setRect(self, rect):
            self.rect = rect

        def setPen(self, pen):
            self.pen = pen 

        def paint(self, painter, option, widget=None):
            painter.setPen(self.pen)
            if self.orientation:
                start, span = 0, 180*16
            else:
                start, span = 0, -180*16
            painter.drawArc(self.rect, start, span)

        def boundingRect(self):
            return self.rect

    def __init__(self, edge, parent=None):
        super().__init__(parent=parent)

        # Unpack the edge
        self.graph = self.parentItem()._graph
        self.edge = edge
        self.in_node, self.out_node, self.key, self.data = edge
        self.in_vnode = self.parentItem()._node_to_vnode_map[self.in_node]
        self.out_vnode = self.parentItem()._node_to_vnode_map[self.out_node]

        # Create the graphics items
        self.path = VisualEdge.Arc(parent=self)
        self.arrow = VisualEdge.ArrowHead(parent=self)
        self.text = QGraphicsTextItem(str(self.data), parent=self)#str(self.data))
        self.setEdgeText()

        self.path.setFlag(QGraphicsItem.ItemStacksBehindParent, enabled=True)
        #self.arrow.setFlag(QGraphicsItem.ItemStacksBehindParent, enabled=True)
        self.text.setFlag(QGraphicsItem.ItemStacksBehindParent, enabled=True)
        self.text.setVisible(False)

        # Colorize
        self.path.setPen(QPen(Qt.white))
        self.arrow.setPen(QPen(Qt.white))
        self.text.setDefaultTextColor(Qt.lightGray)

        # Calculate graphic items positions
        self.setZValue(-2)
        self.calculatePath()
        self.calculateText()

    def setEdgeText(self):
        properties = self.data.get('properties', {})
        if properties:
            txt = "\n".join([f"{k}: {v}" for k,v in properties.items()])
        else:
            txt = ""
        self.text.setPlainText(txt)

    def lineIntersects(self, line):
        def orientation(p1,p2,p3): 
            val = (float(p2.y() - p1.y()) * (p3.x() - p2.x())) - (float(p2.x() - p1.x()) * (p3.y() - p2.y()))
            return val > 0

        path = QPainterPath(line.p1())
        path.lineTo(line.p2())
        for vnode in self.parentItem()._node_to_vnode_map.values():
            if vnode is self.in_vnode or vnode is self.out_vnode:
                continue
            shape = vnode.mapToScene(vnode.shape())
            if shape.intersects(path):
                return True, orientation(self.in_vnode.center(), self.out_vnode.center(), vnode.center())
        return False, False

    def calculatePath(self):
        # If a straight path intersects other nodes, make the line arc instead
        line = QLineF(self.out_vnode.center(), self.in_vnode.center())
        intersected, orientation = self.lineIntersects(line)
        if intersected: 
            h = 80 if orientation else -80
        else:
            h = 0

        rect = QRectF(QPointF(0,h/2), QPointF(line.length(), -h/2))
        self.path.setOrientation(orientation)
        self.path.setRect(rect)
        self.path.setRotation(-line.angle())

        pos = line.p1()

        # For multi-edge nodes draw an offset on the edge so its more visible
        delta = 0
        if isinstance(self.key, int):
            if self.key != 0:
                delta = 8 if self.key % 2 else -8
        if delta:
            offset = (line.normalVector().unitVector().p2() - line.p1()) * delta
            pos = offset + line.p1()
        else:
            offset = QPointF(0,0)
        self.path.setPos(pos)

        curve_offset = (line.normalVector().unitVector().p2() - line.p1()) * h/2
        self.arrow.setRotation(-line.angle())
        self.arrow.setPos(line.center() + curve_offset + offset)

    def getLine(self):
        return QLineF(self.out_vnode.center(), self.in_vnode.center())

    def calculateText(self):
        self.text.setPos(self.getLine().center())

    def updatePath(self):
        self.prepareGeometryChange()
        self.calculatePath()
        self.calculateText()
        self.update()

    #def setHovering(self, state):
    #    if state:
    #        self.path.setPen(QPen(Qt.red))
    #        self.arrow.setPen(QPen(Qt.red))
    #        self.text.setVisible(True)
    #    else:
    #        self.path.setPen(QPen(Qt.white))
    #        self.arrow.setPen(QPen(Qt.white))
    #        self.text.setVisible(False)
    #    self.update()

    def paint(self, painter, option, widget=None):
        pass
        #painter.drawRect(self.boundingRect())

    def boundingRect(self):
        return self.childrenBoundingRect()

class VisualNode(QGraphicsItem):
    class Background(QGraphicsItem):
        def __init__(self, brush, pen, parent=None):
            super().__init__(parent=parent)
            self._boundary = None
            self.brush = brush
            self.pen = pen

        def setBoundingRect(self, boundary):
            self._boundary = boundary

        def boundingRect(self):
            return self._boundary

        def paint(self, painter, option, widget=None):
            painter.setBrush(self.brush)
            painter.drawRoundedRect(self.boundingRect(), 5, 5)

    def __init__(self, node, pos, visual_scheme, circle, parent=None):
        super().__init__(parent)
        # Keep reference to node
        self.graph = self.parentItem()._graph
        self.node = node
        self.circle = circle

        # set node config
        self.node_label, self.pen = None, None
        self.brush, self.size = None, None
        self.setVisualScheme()

        if self.circle:
            self.shell = QGraphicsEllipseItem(0, 0, self.size[0], self.size[1], parent=self)
        else:
            self.shell = QGraphicsRectItem(0, 0, self.size[0], self.size[1], parent=self)

        self.shell.setPen(self.pen)
        self.shell.setBrush(self.brush)
        self.shell.setFlag(QGraphicsItem.ItemStacksBehindParent, enabled=True)
        self.shell.setEnabled(False)

        #self.background = VisualNode.Background(self.brush, self.pen, parent=self)
        #self.background.setFlag(QGraphicsItem.ItemStacksBehindParent, enabled=True)
        #self.background.setEnabled(False)

        # set text
        self.text = QGraphicsTextItem(self.label_text, parent=self)
        self.text.setPos(self.shell.boundingRect().center() - self.text.boundingRect().center())
        self.text.setDefaultTextColor(Qt.white)
        self.text.setFlag(QGraphicsItem.ItemStacksBehindParent, enabled=True)
        self.text.setEnabled(False)

        # set node shell
        #self.background.setBoundingRect(self.boundingRect())

        super().setPos(pos - self.boundingRect().center())

    def setVisualScheme(self):
        config = self.graph.nodes[self.node].get('visual_scheme', {})

        # Pen
        self.pen = QPen(Qt.black, int(config.get("boundarySize", 2)))
        
        # Brush
        color = config.get("fillColor", 'darkGray')
        self.brush = QBrush(getattr(Qt, color))

        # Size
        size = config.get('size', [50,50])
        if not isinstance(size, list):
            size = [size, size]
        self.size = [int(s) for s in size]

        # Node Label
        self.label_text = config.get('label', repr(self.node)) 

    def getProperties(self):
        defaults = {'type': type(self.node).__name__, 'name': self.node}
        return self.graph.nodes[self.node].get('properties', defaults) 

    def paint(self, painter, option, widget=None):
        pass
        #painter.setBrush(self.brush)
        #painter.drawRoundedRect(self.boundingRect(), 5, 5)
        #super().paint(painter, option, widget=None)
        #pass

    def boundingRect(self):
        return self.childrenBoundingRect() 

    def center(self):
        return self.pos() + self.childrenBoundingRect().center()

    def setPos(self, pos):
        super().setPos(pos)
        self.parentItem().childrenMoved(self)

    def mousePressEvent(self, e):
        super().mousePressEvent(e)

class GraphLayout:
    def __init__(self):
        pass

