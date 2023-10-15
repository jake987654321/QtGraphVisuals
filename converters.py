
import networkx as nx
import numpy as np

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
            graph.nodes[node]['properties']['inbound'] = [node.name for node in graph.predecessors(node)]
            graph.nodes[node]['properties']['outbound'] = [node.name for node in graph.successors(node)]
            if node.type_ == 'Node':
                graph.nodes[node]['properties'].update({attr.name: onnx.helper.get_attribute_value(attr) for attr in list(node.proto.attribute)})

        for u,v,key,data in graph.edges(keys=True, data=True):
            try:
                #txt = onnx.helper.printable_value_info(data.get('value', 0))
                value_info_proto = data['value']
                txt = onnx.helper.printable_type(value_info_proto.type)
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
