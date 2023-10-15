
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

from QtGraphVisuals.graphic_items import VisualGraph, VisualNode, VisualEdge 
from QtGraphVisuals.properties_viewer import PropertiesViewer
from QtGraphVisuals.converters import onnxToMultiDiGraph, kerasToMultiDiGraph

## Application
class GraphViewer(QWidget):
    def __init__(self, views, parent=None):
        super().__init__(parent)

        # Children
        self._tabs = QTabWidget(parent=self)

        # Create views
        self._views = {}
        [self.addView(name, graph) for name,graph in views.items()]

        # Layout
        self.setLayout(QHBoxLayout())
        self.layout().addWidget(self._tabs)

        # Connect
        self._tabs.currentChanged.connect(self.tabChanged)

    @Slot(int)
    def tabChanged(self, idx):
        pass

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
        gvwp = GraphViewerWindowAndProperties(graph, parent=self)
        self._views[view_name] = gvwp
        self._tabs.addTab(gvwp, view_name)

    def setView(self, view_name, graph):
        self._views[view_name]._gvw.setGraph(graph)

    def showEvent(self, e):
        super().showEvent(e)
        self._tabs.currentWidget()._gvw.centerScene()

# Graph Viewer
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

    class ResetViewButton(QWidget):
        def __init__(self, graph_viewer_window, parent=None):
            super().__init__(parent)
            # Keep a reference to the graphviewerwindow around
            self.gvw = graph_viewer_window

            # Load Icons
            self.icons = IconLoader.load([
                'restart_alt_FILL0_wght300_GRAD0_opsz24.svg'
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
            self.gvw.setGraph(self.gvw._graph)
            self.gvw.centerScene()
            self.gvw.setDefaultZoom()

    class ZoomFullButton(QWidget):
        def __init__(self, graph_viewer_window, parent=None):
            super().__init__(parent)
            # Keep a reference to the graphviewerwindow around
            self.gvw = graph_viewer_window

            # Load Icons
            self.icons = IconLoader.load([
                'zoom_out_map_FILL0_wght300_GRAD0_opsz24.svg'
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
            self.gvw.centerAndFitNodes()
            self.gvw.centerAndFitNodes()

    def __init__(self, parent=None):
        super().__init__(parent)

        #self.frame = QFrame(self)
        #self.frame.setLayout(QVBoxLayout())

        self.setLayout(QHBoxLayout())
        self.layout().setAlignment(Qt.AlignLeft)

        self.reset_button = ControlRibbon.ResetViewButton(graph_viewer_window=parent, parent=self)
        self.zoom_full_button = ControlRibbon.ZoomFullButton(graph_viewer_window=parent, parent=self)
        self.orientation_button = ControlRibbon.OrienationButton(graph_viewer_window=parent, parent=self)
        self.shape_button = ControlRibbon.ShapeButton(graph_viewer_window=parent, parent=self)
        self.text_button = ControlRibbon.TextButton(graph_viewer_window=parent, parent=self)

        self.layout().addWidget(self.reset_button)
        self.layout().addWidget(self.zoom_full_button)
        self.layout().addWidget(self.orientation_button)
        self.layout().addWidget(self.shape_button)
        self.layout().addWidget(self.text_button)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Maximum)

class GraphViewerWindowAndProperties(QWidget):
    def __init__(self, graph=None, parent=None):
        super().__init__(parent)

        self.setLayout(QHBoxLayout())
        self._splitter = QSplitter(Qt.Horizontal)
        self._gvw = GraphViewerWindow(graph, parent=self)
        self._properties_viewer = PropertiesViewer(parent=self)
        self._splitter.addWidget(self._gvw)
        self._splitter.addWidget(self._properties_viewer)
        self.layout().addWidget(self._splitter)
        
        # Connect properties viewer and gvw, initalize w/ graph properties
        self._gvw.clicked.connect(self._properties_viewer.setConfig)
        self._properties_viewer.setConfig(self._gvw._vgraph.getProperties())

        # Resize stuff
        total_width = self._splitter.width() - self._splitter.handleWidth()
        self._splitter.setSizes([2 * total_width // 3, total_width // 3])

        # Recenter gvw
        self._gvw.centerScene()

class GraphViewerWindow(QGraphicsView):
    clicked = Signal(tuple)

    def __init__(self, graph=None, parent=None):
        super().__init__(parent)
        self._graph = graph

        # Drawing states
        self._draw_vertical = True
        self._draw_text = True
        self._draw_circles = True

        # Configure QGraphicsView
        self.setTransformationAnchor(QGraphicsView.NoAnchor)
        self.setResizeAnchor(QGraphicsView.NoAnchor)
        self.setHorizontalScrollBarPolicy( Qt.ScrollBarAlwaysOff )
        self.setVerticalScrollBarPolicy( Qt.ScrollBarAlwaysOff )
        self.setRenderHints(QPainter.Antialiasing)

        # Create/Configure the Scene
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setSceneRect()

        self._vgraph = None
        self.setGraph(self._graph)

        # State
        self._dragging = False
        self._selected = None
        self._selection_box = None
        self._hovering = []

        self.control_ribbon = ControlRibbon(parent=self)
        self.control_ribbon.setGeometry(10, 10, 300, 50)  # Set geometry to position the button

    # Button Control helpers
    def toggleGraphOrientation(self):
        self._draw_vertical = not self._draw_vertical
        self.setGraph(self._graph)
        self.centerScene()

    def toggleGraphNodeShape(self):
        self._draw_circles = not self._draw_circles
        self.setGraph(self._graph)

    def setSceneRect(self):
        br = self.scene().itemsBoundingRect()
        size = QPointF(br.height(), br.width())*10
        tl, br = br.center()-size, br.center()+size
        #print(tl, br)
        #self.scene().setSceneRect(QRectF(tl, br))
        self.scene().setSceneRect(-float('inf'), -float('inf'), float('inf'), float('inf'))

    def mousePressEvent(self, e):
        x,y = e.position().x(), e.position().y()
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
            else:
                self.clicked.emit(self._vgraph.getProperties())

        super().mouseReleaseEvent(e)

    def _checkHovering(self, e):
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

        # Save the old mouse position
        old_pos = self.mapToScene(e.position().toPoint())

        # Scale the scene
        self.scale(zf,zf)

        # Reposition the scene so the 'mouse' stayed in the same spot
        new_pos = self.mapToScene(e.position().toPoint())
        delta = new_pos - old_pos
        self.translate(delta.x(), delta.y())

    def setDefaultZoom(self):
        current_zf = self.transform().m11()

        #self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.scale(1 / current_zf, 1 / current_zf)
        #self.setTransformationAnchor(QGraphicsView.NoAnchor)

    def centerScene(self):
        p0 = self.mapToScene(*self.centerOfView()) 
        self.setTransform(QTransform().translate(p0.x(), p0.y()), combine=True)

    def centerAndFitNodes(self):
        """
        Center the scene on the middle of all VisualNodes in VisualGraph and adjust the zoom level such that all vnodes are visible.
        Must be called twice to work properly LOL... 
        """
        # Calculate the combined bounding rectangle of all items
        bounding_rect = QRectF()
        for vnode in self._vgraph._node_to_vnode_map.values():
            bounding_rect = bounding_rect.united(vnode.sceneBoundingRect())
                        
        # Adjust the zoom level to fit the items in view
        #self.fitInView(bounding_rect, aspectRadioMode=Qt.AspectRatioMode.KeepAspectRatio)

        ## Center the view on the point
        #self.centerOn(bounding_rect.center())

        # Calculate current visible rectangle
        visible_rect = self.mapToScene(self.viewport().rect()).boundingRect()
        # Calculate the scale factors
        x_scale = visible_rect.width() / bounding_rect.width()
        y_scale = visible_rect.height() / bounding_rect.height()
        scale_factor = min(x_scale, y_scale)
        # Apply the scale transformation
        self.scale(scale_factor, scale_factor)
        # Calculate the translation required to center on the desired point
        delta = bounding_rect.center() - visible_rect.center()
        #translation_point = self.mapFromScene(delta)
        # Apply the translation
        self.translate(-delta.x(), -delta.y())


    def centerOfView(self):
        return (self.size().width()-1)/2, (self.size().height()-1)/2

    def setGraph(self, graph):
        self.scene().clear()
        
        # Convert graph (if not already a MultiDiGraph)
        if isinstance(graph, nx.MultiDiGraph):
            self._graph = graph
        elif 'keras' in graph.__module__:
            self._graph = kerasToMultiDiGraph(graph)
        elif 'onnx' in graph.__module__:
            self._graph = onnxToMultiDiGraph(graph)

        self._vgraph = VisualGraph(self._graph, self._draw_vertical, self._draw_text, self._draw_circles)
        self.scene().addItem(self._vgraph)
        #self.setSceneRect()
        self.centerScene()

        # reset-state
        self._dragging = False
        self._selected = None
