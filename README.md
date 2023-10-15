# QtGraphVisuals
View directed graphs with a qt-widget implemented using pyside6!

I highly recommend making a virtual environment for new packages!
```bash
$ python3 -m venv /path/to/my/env
$ source /path/to/my/env/bin/activate
$ pip install --upgrade pip
```

Install w/ pip and run!
```bash
$ pip install QtGraphVisuals
$ python3 -m QtGraphVisuals
```

Viola!

Main features are: 
- Directed Graph visualisation: This library visualizes nx.DiGraph/MultiDigraph and also supports Keras / Onnx models.
- Graph exploration: Zoom / Pan / Click / Move the graph and nodes!
- Properties Viewer: View properties of the graph and nodes interactively!
- Tabs: View many graphs, just one tab click away :)

# Examples

View nx.DiGraphs: 
```python3
from QtGraphVisuals import quick_view
import networkx as nx

G1 = nx.DiGraph([(1,2), (2,3), (3,4)])
G2 = nx.DiGraph([(1,2), (2,3), (3,4), (2,4)])

quick_view({'G1': G1, 'G2': G2})
```

View Keras or Onnx models. Note you will have to install Onnx and Tensorflow separately (`pip install onnx` and/or `pip install tensorflow`)!

```python3
import onnx
from tensorflow import keras

onnx_model = onnx.load('my_model.onnx')
keras_model = keras.applications.ResNet50()
quick_view({'onnx': onnx_model, 'keras': keras_model})
```

Integrate as widget into other Qt GUI projects
```python3
import sys
import networkx as nx
from PySide6.QtWidgets import QApplication
from QtGraphVisuals import QGraphViewer

if __name__ == "__main__":
    # Create the app
    app = QApplication(sys.argv)
    app.setApplicationName("QtGraphVisuals Demo")

    # Stylize (not necessary but it looks nice)
    extra={ "secondaryDarkColor":"#232629", "font_size": '15px',}
    apply_stylesheet(app, theme='dark_blue.xml', extra=extra)

    # Instantiate viewer
    viewer = QGraphViewer({'graph1': nx.path_graph([1,2,3], create_using=nx.DiGraph)})
    viewer.resize(800,600)
    viewer.show()

    sys.exit(app.exec())
```
