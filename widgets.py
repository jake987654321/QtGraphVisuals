
import sys, pathlib, importlib
import networkx as nx
import numpy as np
from PySide6.QtCore import (Qt, Signal, Slot, QPoint, QPointF, QLine, QLineF,
        QRect, QRectF, QSize) 
from PySide6.QtWidgets import (QApplication, QWidget, QLabel, QHBoxLayout, QPushButton, QSizePolicy,
        QVBoxLayout, QGraphicsView, QGraphicsScene, QGraphicsPolygonItem, QGraphicsRectItem,
        QGraphicsEllipseItem, QGraphicsItem, QGraphicsTextItem, QGraphicsPathItem, QGraphicsLineItem, QGroupBox,
        QScrollArea, QFrame, QTabWidget, QSplitter)
from PySide6.QtGui import QPainterPath, QPainter, QTransform, QBrush, QPen, QColor, QPolygonF, QFont, QIcon, QPixmap

# Local files
#from importlib import resources as importlib_resources
from importlib import resources as impresources
from . import icons

class IconLoader:
    icon_folder = impresources.files(icons)

    def __init__(self, filename_list):
        self.icons = [self._load_icon(f) for f in filename_list]

    def _load_icon(self, filename):
        file_path = self.icon_folder / filename

        #QColor selected_color('#4388FC');
        color = QColor(67,136,252);
        
        # load gray-scale image (an alpha map)
        pixmap = QPixmap(str(file_path))
        
        # initialize painter to draw on a pixmap and set composition mode
        painter = QPainter(pixmap);
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn);
        
        painter.setBrush(color);
        painter.setPen(color);
        
        painter.drawRect(pixmap.rect());

        del painter
        
        # Here is our new colored icon!
        return QIcon(pixmap)

    @staticmethod
    def load(filename_list):
        loader = IconLoader(filename_list)
        return loader.icons

def onnxToMultiDiGraph(model):
    import onnx
    class HashableOnnxNode:
        def __init__(self, proto, type_):
            self.name = proto.name
            self.proto = proto
            self.type_ = type_ # Node / Input / Output
            if type_ in ['Input', 'Output']:
                self.op_type = type_
            else:
                self.op_type = proto.op_type
            self.init_dict = {}

    def setVisualScheme(graph):
        # Set Visual Schemes
        for node in graph.nodes():
            vs = {'boundarySize': 2, 'size': 50}

            vs['label'] = node.op_type.lower()
            if 'conv' in node.op_type.lower():
                vs['fillColor'] = 'darkBlue'
            elif 'pool' in node.op_type.lower():
                vs['fillColor'] = 'darkGreen'
            elif 'elu' in node.op_type.lower():
                vs['fillColor'] = 'darkRed'
                vs['size'] = [50,25]
            graph.nodes[node]['visual_scheme'] = vs

            graph.nodes[node]['properties'] = {}
            graph.nodes[node]['properties']['name'] = node.name
            graph.nodes[node]['properties']['inbound'] = list(graph.predecessors(node))
            graph.nodes[node]['properties']['outbound'] = list(graph.successors(node))
            if node.type_ == 'Node':
                graph.nodes[node]['properties'].update({attr.name: onnx.helper.get_attribute_value(attr) for attr in list(node.proto.attribute)})

        for u,v,key,data in graph.edges(keys=True, data=True):
            try:
                txt = onnx.helper.printable_value_info(data.get('value', 0))
            except:
                txt = ''
            graph.edges[u,v,key]['properties'] = {'info': txt}

    G = nx.MultiDiGraph(name=model.graph.name)

    # Add nodes to the graph
    for node_proto in model.graph.node:
        hnode = HashableOnnxNode(node_proto, type_='Node')
        G.add_node(hnode)

    # Add initializer data to the nodes
    for init_proto in model.graph.initializer:
        for node in G.nodes:
            if init_proto.name in node.proto.input:
                node.init_dict[init_proto.name] = init_proto

    # Add edges to the graph
    name_to_value_map = {v.name:v for v in model.graph.value_info}
    for u in G.nodes:
        for v in G.nodes:
            if v is u:
                continue

            # Use v.input because this considers the Multi part in MultiDiGraph
            for v_index, value_name in enumerate(v.proto.input):
                if not value_name in u.proto.output:
                    continue
                u_index = list(u.proto.output).index(value_name)
                value = name_to_value_map.get(value_name, None)
                G.add_edge(u, v, u_index=u_index,
                    v_index=v_index, value=value)

    # Add input/output nodes
    for input_proto in list(model.graph.input):
        G.add_node(HashableOnnxNode(proto=input_proto, type_='Input'))
    for output_proto in list(model.graph.output):
        G.add_node(HashableOnnxNode(proto=output_proto, type_='Output'))
    node_list = [n for n in G.nodes if n.type_=='Node']

    # Add input/output edges
    for u in [n for n in G.nodes if n.type_=='Input']:
        for v in node_list:
            for v_index, value_name in enumerate(v.proto.input):
                if value_name ==  u.name:
                    G.add_edge(u, v, u_index=0, v_index=v_index,
                            value=u.proto)

    for v in [n for n in G.nodes if n.type_=='Output']:
        for u in node_list:
            for u_index, value_name in enumerate(u.proto.output):
                if value_name == v.name:
                    G.add_edge(u, v, u_index=u_index, v_index=0,
                            value=v.proto)
    setVisualScheme(G)
    return G

def kerasToMultiDiGraph(model):
    def setVisualScheme(graph):
        # Set Visual Schemes
        for node in graph.nodes():
            ntype = type(node).__name__
            vs = {'boundaySize': 2, 'size': 50, 'label': ntype}

            if 'conv' in ntype.lower():
                vs['fillColor'] = 'darkBlue'
            elif 'pool' in ntype.lower():
                vs['fillColor'] = 'darkGreen'
            elif 'elu' in ntype.lower() or 'activation' in ntype.lower():
                vs['fillColor'] = 'darkRed'
                vs['size'] = [50,25]
            elif 'normalization' in ntype.lower():
                vs['fillColor'] = 'darkMagenta'
                vs['size'] = [50,25]
            elif graph.in_degree(node) > 1:
                vs['fillColor'] = 'black'
                vs['size'] = [50,25]

            graph.nodes[node]['visual_scheme'] = vs
            graph.nodes[node]['properties'] = {}
            graph.nodes[node]['properties']['name'] = node
            graph.nodes[node]['properties']['inbound'] = list([n.name for n in graph.predecessors(node)])
            graph.nodes[node]['properties']['outbound'] = list([n.name for n in graph.successors(node)])
            graph.nodes[node]['properties'].update(node.get_config())

        for u,v,key,data in graph.edges(keys=True, data=True):
            graph.edges[u,v,key]['properties'] = {'shape': v.output_shape}

    graph = nx.MultiDiGraph()

    # Add all 'Layers' (aka nodes) to the graph
    graph.add_nodes_from(model.layers)

    # Get a set of all 'Nodes' (aka edges) in the keras graph
    for u in model.layers:
        for v in model.layers:
            if u is v:
                continue
            for node in u.outbound_nodes:
                if node in v.inbound_nodes:
                    index = v.inbound_nodes.index(node)
                    shape = u.output_shape
                    graph.add_edge(u, v, in_index=0, out_index=index,
                        shape=shape)

    # Adds auxillary information to the graph for visualization purposes
    setVisualScheme(graph)
    return graph

## Application
class GraphViewer(QWidget):
    def __init__(self, views, parent=None):
        super().__init__(parent)

        # Children
        self._tabs = QTabWidget(parent=self)
        self._properties_viewer = PropertiesViewer(parent=self)
        #self._controls = ControlButtons(parent=self)

        # Create views
        self._views = {}
        [self.addView(name, graph) for name,graph in views.items()]

        # Layout
        self.setLayout(QHBoxLayout())
        self._splitter = QSplitter(Qt.Horizontal)
        self._splitter.addWidget(self._tabs)
        self._splitter.addWidget(self._properties_viewer)
        #self.layout().addWidget(self._controls)
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

    def addView(self, view_name, graph):
        if view_name in self._views:
            raise ValueError(f"{view_name} already exsists")
        gv = GraphViewerWindow(graph, parent=self)
        self._views[view_name] = gv
        gv.clicked.connect(self._properties_viewer.setConfig)
        self._tabs.addTab(gv, view_name)

    def setView(self, view_name, graph):
        self._views[view_name].setGraph(graph)

    # getCurrentGraphViewerWindow()
    # getCurrentGraphViewerWindow()._vgraph.resetHorizontal

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

class ControlRibbon(QWidget):
    style_sheet = """
        QPushButton {padding: 0px; border-width: 0px; background: transparent}
        QPushButton:hover {background: rgba(127,127,127,127)}
        QPushButton:pressed {background: rgba(127,127,127,255)}
    """

    class OrienationButton(QWidget):
        def __init__(self, graph_viewer_window, parent=None):
            super().__init__(parent)
            # Keep a reference to the graphviewerwindow around
            self.gvw = graph_viewer_window

            # Load Icons
            self.icons = IconLoader.load([
                'arrow_circle_right_FILL0_wght300_GRAD0_opsz24.svg',
                'arrow_circle_down_FILL0_wght300_GRAD0_opsz24.svg'
            ])
            self.vertical = True

            self.button = QPushButton(parent=self) 
            self.button.setIcon(self.icons[self.vertical])
            self.button.setFixedWidth(self.button.height())
            self.button.setIconSize(QSize(self.button.width(), self.button.height()))
            self.button.setStyleSheet(ControlRibbon.style_sheet)

            self.button.clicked.connect(self.click)

            self.setLayout(QVBoxLayout())
            self.layout().addWidget(self.button)
            self.layout().setContentsMargins(0,0,0,0)

        @Slot()
        def click(self, e):
            self.vertical = not self.vertical
            self.button.setIcon(self.icons[self.vertical])
            self.gvw.toggleGraphOrientation()

    class ShapeButton(QWidget):
        def __init__(self, graph_viewer_window, parent=None):
            super().__init__(parent)
            # Keep a reference to the graphviewerwindow around
            self.gvw = graph_viewer_window

            # Load Icons
            self.icons = IconLoader.load([
                'shape_line_FILL0_wght300_GRAD0_opsz24.svg'
            ])

            self.button = QPushButton(parent=self) 
            self.button.setIcon(self.icons[0])
            self.button.setFixedWidth(self.button.height())
            self.button.setIconSize(QSize(self.button.width(), self.button.height()))
            self.button.setStyleSheet(ControlRibbon.style_sheet)
            self.button.clicked.connect(self.click)

            self.setLayout(QVBoxLayout())
            self.layout().addWidget(self.button)
            self.layout().setContentsMargins(0,0,0,0)

        @Slot()
        def click(self, e):
            self.gvw.toggleGraphNodeShape()

    class TextButton(QWidget):
        def __init__(self, graph_viewer_window, parent=None):
            super().__init__(parent)
            # Keep a reference to the graphviewerwindow around
            self.gvw = graph_viewer_window

            # Load Icons
            self.icons = IconLoader.load([
                'subtitles_FILL0_wght300_GRAD0_opsz24.svg',
                'subtitles_off_FILL0_wght300_GRAD0_opsz24.svg'
            ])
            self.state = True

            self.button = QPushButton(parent=self) 
            self.button.setIcon(self.icons[self.state])
            self.button.setFixedWidth(self.button.height())
            self.button.setIconSize(QSize(self.button.width(), self.button.height()))
            self.button.setStyleSheet(ControlRibbon.style_sheet)
            self.button.clicked.connect(self.click)

            self.setLayout(QVBoxLayout())
            self.layout().addWidget(self.button)
            self.layout().setContentsMargins(0,0,0,0)

        @Slot()
        def click(self, e):
            self.state = not self.state
            self.button.setIcon(self.icons[self.state])
            self.gvw._vgraph.setNodeText(self.state)

    def __init__(self, parent=None):
        super().__init__(parent)

        #self.frame = QFrame(self)
        #self.frame.setLayout(QVBoxLayout())

        self.setLayout(QHBoxLayout())
        self.layout().setAlignment(Qt.AlignLeft)

        self.orientation_button = ControlRibbon.OrienationButton(graph_viewer_window=parent, parent=self)
        self.shape_button = ControlRibbon.ShapeButton(graph_viewer_window=parent, parent=self)
        self.text_button = ControlRibbon.TextButton(graph_viewer_window=parent, parent=self)

        self.layout().addWidget(self.orientation_button)
        self.layout().addWidget(self.shape_button)
        self.layout().addWidget(self.text_button)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Maximum)

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
        self.setSceneRect()

        # State
        self._dragging = False
        self._selected = None
        self._selection_box = None
        self._hovering = []

        self._draw_vertical = True
        self._draw_text = True
        self._draw_circles = True

        # Center the Scene
        self.centerScene()

        self.control_ribbon = ControlRibbon(parent=self)
        self.control_ribbon.setGeometry(10, 10, 300, 50)  # Set geometry to position the button

    # Button Control helpers
    def toggleGraphOrientation(self):
        self._draw_vertical = not self._draw_vertical
        self.setGraph(self._graph, self._draw_vertical, self._draw_text, self._draw_circles)
        self.centerScene()

    def toggleGraphNodeShape(self):
        self._draw_circles = not self._draw_circles
        self.setGraph(self._graph, self._draw_vertical, self._draw_text, self._draw_circles)

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
                self.clicked.emit(self._selected.getProperties())
                #self.scene().setSceneRect(self.scene().itemsBoundingRect())
        super().mouseReleaseEvent(e)

    def _checkHovering(self, e):
        #item = self.itemAt(e.position().toPoint())
        items = self.items(e.position().toPoint()) 

        #i first unset all items no longer being hovered
        to_be_removed = []
        for hover in self._hovering:
            if hasattr(hover, 'setHovering') and hover not in items:
                hover.setHovering(False)
                to_be_removed.append(hover)
        [self._hovering.remove(r) for r in to_be_removed]

        # second set hovering for all items 
        for item in items:
            if hasattr(item, 'setHovering') and item not in self._hovering:
                item.setHovering(True)
                self._hovering.append(item)

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

    def setGraph(self, graph, vertical=True, show_text=True, circle_nodes=True):
        self.scene().clear()
        
        # Convert graph (if not already a MultiDiGraph)
        if isinstance(graph, nx.MultiDiGraph):
            self._graph = graph
        elif 'keras' in graph.__module__:
            self._graph = kerasToMultiDiGraph(graph)
        elif 'onnx' in graph.__module__:
            self._graph = onnxToMultiDiGraph(graph)

        self._vgraph = VisualGraph(self._graph, vertical, show_text, circle_nodes)
        self.scene().addItem(self._vgraph)
        self.setSceneRect()

        # reset-state
        self._dragging = False
        self._selected = None

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

