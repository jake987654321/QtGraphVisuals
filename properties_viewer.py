
from PySide6.QtCore import (Qt, Signal, Slot, QPoint, QPointF, QLine, QLineF,
        QRect, QRectF, QSize) 
from PySide6.QtWidgets import (QApplication, QWidget, QLabel, QHBoxLayout, QPushButton, QSizePolicy,
        QVBoxLayout, QGraphicsView, QGraphicsScene, QGraphicsPolygonItem, QGraphicsRectItem,
        QGraphicsEllipseItem, QGraphicsItem, QGraphicsTextItem, QGraphicsPathItem, QGraphicsLineItem, QGroupBox,
        QScrollArea, QFrame, QTabWidget, QSplitter)
from PySide6.QtGui import QPainterPath, QPainter, QTransform, QBrush, QPen, QColor, QPolygonF, QFont, QIcon, QPixmap

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
