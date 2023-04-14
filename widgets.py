
import sys, json, pathlib
import networkx as nx
import numpy as np
from PySide6.QtCore import (Qt, Signal, Slot, QPoint, QPointF, QLine, QLineF,
        QRect, QRectF)
from PySide6.QtWidgets import (QApplication, QWidget, QLabel, QHBoxLayout,
        QVBoxLayout, QGraphicsView, QGraphicsScene, QGraphicsRectItem,
        QGraphicsEllipseItem, QGraphicsItem, QGraphicsTextItem, QGraphicsLineItem, QGroupBox,
        QScrollArea, QFrame, QTabWidget, QSplitter)
from PySide6.QtGui import QPainter, QTransform, QBrush, QPen, QColor

# Load default visual schemes 
default_visual_schemes = {}
path = pathlib.Path(__file__).parent
with open(path / 'default_visual_schemes.json', 'r') as f:
    default_visual_schemes = json.loads(f.read())

## Application
class GraphViewer(QWidget):
    def __init__(self, views, parent=None):
        super().__init__(parent)

        # Children
        self._tabs = QTabWidget(parent=self)
        self._properties_viewer = PropertiesViewer(parent=self)

        # Create views
        self._views = {}
        [self.addView(name, graph) for name,graph in views.items()]

        # Layout
        self.setLayout(QVBoxLayout())
        self._splitter = QSplitter(Qt.Horizontal)
        self._splitter.addWidget(self._tabs)
        self._splitter.addWidget(self._properties_viewer)
        self.layout().addWidget(self._splitter)

        # Connect
        self._tabs.currentChanged.connect(self.tabChanged)

    @Slot(int)
    def tabChanged(self, idx):
        if self._tabs.currentWidget():
            self._tabs.currentWidget().centerScene()

    def clearViews(self):
        for name, view in self._views.items():
            self._tabs.removeTab(self._tabs.indexOf(view))
            view.deleteLater()
        self._views.clear()

    def removeView(self, view_name):
        if view_name not in self._views:
            raise ValueError(f"{view_name} is not a view")
        gv = self._views.pop(view_name)
        self._tabs.removeTab(self._tabs.indexOf(gv))
        gv.deleteLater()

    def addView(self, view_name, graph, visual_scheme=None):
        if view_name in self._views:
            raise ValueError(f"{view_name} already exsists")
        gv = GraphViewerWindow(graph, visual_scheme, parent=self)
        self._views[view_name] = gv
        gv.clicked.connect(self._properties_viewer.setConfig)
        self._tabs.addTab(gv, view_name)

    def setView(self, view_name, graph):
        self._views[view_name].setGraph(graph)

    def showEvent(self, e):
        super().showEvent(e)
        self._tabs.currentWidget().centerScene()

class PropertiesViewer(QGroupBox):
    def __init__(self, config={}, parent=None): 
        super().__init__(parent)

        # Configure
        self.setLayout(QVBoxLayout())
        #self.setMinimumHeight(300)
        #self.setMinimumWidth(300)
        #self.setMaximumWidth(300)
        self.setTitle('Properties')

        self.scroll = QScrollArea(parent=self)
        self.scroll.setWidgetResizable(True)

        self.group = QWidget(parent=self.scroll)
        self.group.setLayout(QVBoxLayout())

        self.property_text_boxes = [PropertyViewerTextBox(parent=self.group) for i in range(100)]
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
            if i > 99:
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
        self._value.setStyleSheet("QLabel {background: rgb(49, 54, 59); border-radius: 3px;}")
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

    def __init__(self, graph=None, visual_scheme=None, parent=None):
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
        self.setGraph(self._graph, visual_scheme)

        # Set scene bounding rect
        self.setSceneRect()

        # State
        self._dragging = False
        self._selected = None
        self._hovering = None

        # Center the Scene
        self.centerScene()

    def setSceneRect(self):
        br = self.scene().itemsBoundingRect()
        size = QPointF(br.height(), br.width())*10
        tl, br = br.center()-size, br.center()+size
        self.scene().setSceneRect(QRectF(tl, br))

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            item = self.itemAt(e.position().toPoint())

            if isinstance(item, VisualNode):# and not isinstance(item, VisualGraph):
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

    def _checkHovering(self, e):
        item = self.itemAt(e.position().toPoint())
        if not item and not self._hovering:
            pass
        elif item and not self._hovering:
            if hasattr(item, 'setHovering'):
                item.setHovering(True)
            self._hovering = item
        elif not item and self._hovering:
            if hasattr(self._hovering, 'setHovering'):
                self._hovering.setHovering(False)
            self._hovering = None 
        else: # item and self._hovering
            if not item is self._hovering:
                if hasattr(self._hovering, 'setHovering'):
                    self._hovering.setHovering(False)
                if hasattr(item, 'setHovering'):
                    item.setHovering(True)
                self._hovering = item

    def mouseMoveEvent(self, e):
        self._checkHovering(e)

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

    def setGraph(self, graph, visual_scheme=None):
        self.scene().clear()
        
        # Convert graph (if not already a DiGraph) and set visual scheme (if not specified)
        if isinstance(graph, nx.MultiDiGraph):
            self._graph = graph
            if visual_scheme is None:
                visual_scheme = default_visual_schemes['default']
        elif 'keras' in graph.__module__:
            self._graph = self.kerasToMultiDiGraph(graph)
            if visual_scheme is None:
                visual_scheme = default_visual_schemes['keras']

        self._vgraph = VisualGraph(self._graph, visual_scheme=visual_scheme)
        self.scene().addItem(self._vgraph)
        self.setSceneRect()

        # reset-state
        self._dragging = False
        self._selected = None

    def kerasToMultiDiGraph(self, model):
        from tensorflow import keras
        graph = nx.MultiDiGraph()

        # Add all 'Layers' (aka nodes) to the graph
        graph.add_nodes_from(model.layers)

        # Get a set of all 'Nodes' (aka edges) in the keras graph
        keras_nodes = []
        for layer in model.layers:
            for node in layer.outbound_nodes:
                keras_nodes.append(node)
        keras_nodes = set(keras_nodes)

        # Add the edges to the graph
        for kn in keras_nodes:
            input_layers = kn.inbound_layers
            if not isinstance(input_layers, list): 
                input_layers = [input_layers]
            output_layer = kn.outbound_layer

            for index, input_layer in enumerate(input_layers):
                shape = input_layer.output_shape
                graph.add_edge(input_layer, output_layer,
                            in_index=0, out_index=index, shape=shape)
        return graph

class VisualGraph(QGraphicsItem):
    def __init__(self, graph=None, visual_scheme=None, parent=None):
        super().__init__(parent=parent)

        # Drawing Config
        self.visual_scheme = visual_scheme
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
            l,t = pos[0]-self.node_size/2, pos[1]-self.node_size/2
            self._node_to_vnode_map[node] = VisualNode(node, QPointF(l,t),
                    self.visual_scheme, parent=self)

    def create_visual_edges(self):
        self._edge_to_vedge_map.clear()
        for u,v,key,data in self._graph.edges(keys=True, data=True):
            self._edge_to_vedge_map[(u,v,key)] = VisualEdge((u,v,key,data), parent=self)

    def paint(self, painter, option, widget=None):
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
        br = self.childrenBoundingRect()
        size = QPointF(br.width(), br.height())
        return QRectF(br.center()-size*2, br.center()+size*2)#self._bounding_rect

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
    def __init__(self, edge, parent=None):
        super().__init__(parent=parent)

        # Unpack the edge
        self.edge = edge
        self.in_node, self.out_node, self.key, self.data = edge
        self.in_vnode = self.parentItem()._node_to_vnode_map[self.in_node]
        self.out_vnode = self.parentItem()._node_to_vnode_map[self.out_node]

        # Create the graphics items
        self.path = QGraphicsLineItem(parent=self)
        self.arrow_left = QGraphicsLineItem(parent=self)
        self.arrow_right = QGraphicsLineItem(parent=self)
        self.text = QGraphicsTextItem(str(self.data), parent=self)#str(self.data))

        self.path.setFlag(QGraphicsItem.ItemStacksBehindParent, enabled=True)
        self.arrow_left.setFlag(QGraphicsItem.ItemStacksBehindParent, enabled=True)
        self.arrow_right.setFlag(QGraphicsItem.ItemStacksBehindParent, enabled=True)
        self.text.setFlag(QGraphicsItem.ItemStacksBehindParent, enabled=True)
        self.text.setVisible(False)

        # Colorize
        self.path.setPen(QPen(Qt.white))
        self.arrow_left.setPen(QPen(Qt.white))
        self.arrow_right.setPen(QPen(Qt.white))
        self.text.setDefaultTextColor(Qt.lightGray)

        # Calculate graphic items positions
        self.setZValue(-1)
        self.calculatePath()
        self.calculateArrowHead()
        self.calculateText()

    def calculatePath(self):
        delta = 0
        if isinstance(self.key, int):
            if self.key != 0:
                delta = 8 if self.key % 2 else -8

        line = QLineF(self.out_vnode.center(), self.in_vnode.center())
        if delta:
            offset = (line.normalVector().unitVector().p2() - line.p1()) * delta
            line.translate(offset)
        self.path.setLine(line)

    def calculateArrowHead(self):
        c = self.path.line().center()
        u = self.path.line().unitVector().p1() - self.path.line().unitVector().p2()
        angle = self.path.line().angle()

        # Arrow head
        arrow_right = QLineF(c+3*u, c-3*u)
        arrow_right.setAngle(angle+30)

        arrow_left = QLineF(c+3*u, c-3*u)
        arrow_left.setAngle(angle-30)

        self.arrow_left.setLine(arrow_left)
        self.arrow_right.setLine(arrow_right)

    def calculateText(self):
        self.text.setPos(self.path.line().center())

    def updatePath(self):
        self.calculatePath()
        self.calculateArrowHead()
        self.calculateText()

    def setHovering(self, state):
        if state:
            self.path.setPen(QPen(Qt.red))
            self.arrow_left.setPen(QPen(Qt.red))
            self.arrow_right.setPen(QPen(Qt.red))
            self.text.setVisible(True)
        else:
            self.path.setPen(QPen(Qt.white))
            self.arrow_left.setPen(QPen(Qt.white))
            self.arrow_right.setPen(QPen(Qt.white))
            self.text.setVisible(False)
        self.update()

    def paint(self, painter, option, widget=None):
        pass

    def boundingRect(self):
        return QRectF(self.arrow_left.boundingRect()).united(self.arrow_right.boundingRect())

class VisualNode(QGraphicsItem):
    def __init__(self, node, pos, visual_scheme, parent=None):
        super().__init__(parent)
        # Keep reference to node
        self.visual_scheme = visual_scheme
        self.node = node

        # set node config
        self.node_label, self.pen, self.brush, self.size = None, None, None, None
        self.setNodeConfig()

        # set node shell
        self.shell = QGraphicsEllipseItem(0, 0, self.size[0], self.size[1], parent=self)
        self.shell.setBrush(self.brush)
        self.shell.setPen(self.pen)
        self.shell.setEnabled(False)
        self.shell.setFlag(QGraphicsItem.ItemStacksBehindParent, enabled=True)

        # set text
        self.text = QGraphicsTextItem(self.label_text, parent=self)
        self.text.setPos(self.shell.boundingRect().center() - self.text.boundingRect().center())
        self.text.setFlag(QGraphicsItem.ItemStacksBehindParent, enabled=True)
        self.text.setEnabled(False)
        self.text.setDefaultTextColor(Qt.white)

        super().setPos(pos - self.boundingRect().center())

    def setNodeConfig(self):
        ntype = type(self.node).__name__
        default_config = self.visual_scheme['nodes'].get('default', {})
        config = self.visual_scheme['nodes'].get(ntype, default_config)

        # Pen
        self.pen = QPen(Qt.black, int(config.get("boundarySize", 0)))
        
        # Brush
        color = config.get("fillColor", 'darkGray')
        self.brush = QBrush(getattr(Qt, color))

        # Size
        size = config.get('size', [20,20])
        if not isinstance(size, list):
            size = [size, size]
        self.size = [int(s) for s in size]

        # Node Label
        label_attr = config.get('label_attr', None) 
        if label_attr:
            attr = getattr(self.node, label_attr)
            if callable(attr):
                txt = attr()
            else:
                txt = attr
        else:
            txt = type(self.node).__name__
        self.label_text = txt

    def get_properties(self):
        if hasattr(self.node, 'get_config'):
            return self.node.get_config()
        elif hasattr(self.node, '__dict__'):
            return self.node.__dict__
        else:
            return {'type': type(self.node).__name__, 'name': self.node}

    def paint(self, painter, option, widget=None):
        pass

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

