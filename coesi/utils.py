import os
import shutil
import yaml
import zmq
from collections import deque
import h5py
from collections import defaultdict, OrderedDict
import networkx as nx
import random
import json
from matplotlib import pyplot as plt
from pathlib import Path
import sys
import socket
import queue
import threading

import sys
from pathlib import Path

PROJECT_ROOT = str(Path(__file__).resolve().parents[2]).replace('\\', '/')
sys.path.append(PROJECT_ROOT)
from coesi.definitions import *


# class UDP(object):
#
#     def __init__(self, ip=None, port=None, local=None, msg_rcv=villas_pb2.Message()):
#         self.protocol = 'UDP'
#         self.ip = ip
#         self.port = port
#         self.counter_opal = 0
#         self.buffer_size = 1024
#
#         self.socket = (self.ip, self.port)
#         self.opal = None
#         self.q_opal = queue.Queue()
#         self.msg_rcv = msg_rcv
#
#         self.vars_values_rcv = {}
#
#         self.server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#         print('Starting up UDP Server on IP %s Port %s' % self.socket)
#         #local = ('130.192.177.102', 12004)
#         self.local = local
#         self.server.bind(self.local)
#         if self.ip:
#             self.server.connect(self.socket)
#
#
#     def start(self):
#         self.receiveThread = threading.Thread(target=self.receive_from_opal)
#         self.receiveThread.start()
#         # super(self.__class__, self).start(ip, port)
#
#     def stop(self):
#         #super(self.__class__, self).stop()
#         if (hasattr(self, "receiveThread")):
#             if self.receiveThread.is_alive():
#                 try:
#                     self.receiveThread._Thread__stop()
#                 except Exception:
#                     print(sys.stderr)
#         self.server.close()
#
#     def receive_from_opal(self):
#
#         while self.receiveThread.is_alive():
#             data = self.server.recv(self.buffer_size)
#             self.msg_rcv.ParseFromString(data)
#             for i in range(len(self.msg_rcv.samples[0].values[:])):
#                 self.vars_values_rcv[i] = self.msg_rcv.samples[0].values[i].f
#             print(self.vars_values_rcv[0])
#
#             # try:
#             #     data = self.server.recv(BUFFER_SIZE)
#             #     self.msg_rcv.ParseFromString(data)
#             #     for i in range(len(self.msg_rcv.samples[0].values[:])):
#             #         self.vars_values_rcv[i]= self.msg_rcv.samples[0].values[i].f
#             #     print(self.vars_values_rcv)
#             # except Exception:
#             #     print('YES')
#             #     print(Exception)
#

def read_scenario_from_db(db_filename, root):
    src_db = os.path.join(root, db_filename).replace('\\', '/')
    db = h5py.File(src_db,'r')
    scen_str = db['Sim_set'].attrs['Scenario']
    scen = json.loads(scen_str)
    return scen

def scn_config_load(scn_filename, root):
    src_scn = os.path.join(root, scn_filename).replace('\\','/')
    if root == SCENARIO_ROOT:
        src_scn = os.path.join(root, scn_filename)
        if os.path.isfile(src_scn):
            with open(src_scn, 'r') as stream:
                try:
                    dict_object = yaml.safe_load(stream)
                except yaml.YAMLError as exc:
                    raise Exception(exc)
        else:
            raise FileExistsError(f'File YAML with name "{src_scn.split()[0]}" does not exist in the input data '
                                  f'directory!')
        Path(TEMP_ROOT).mkdir(parents=True, exist_ok=True)
        shutil.copy(src_scn, TEMP_ROOT, follow_symlinks=True)
        src_scn_dest_old = os.path.join(TEMP_ROOT, scn_filename)
        src_scn_dest_new = os.path.join(TEMP_ROOT, f'temp_scn.yaml') # temp scenario
        if os.path.exists(src_scn_dest_new):
            os.remove(src_scn_dest_new)
        os.rename(src_scn_dest_old, src_scn_dest_new)
        return dict_object
    else: # for other roots like SOURCE_ROOT and parent folders
        if os.path.isfile(src_scn):
            with open(src_scn, 'r') as stream:
                try:
                    dict_object = yaml.safe_load(stream)
                except yaml.YAMLError as exc:
                    raise Exception(exc)
        else:
            raise FileExistsError(
                    f'File YAML with name "{src_scn.split()[0]}" does not exist in the input data '
                    f'directory!')
        return dict_object

def scn_config_write(scn_filename,scn_dict,root):

    src_scn = os.path.join(root, scn_filename).replace('\\','/')
    data = yaml.safe_dump(scn_dict)
    f = open(src_scn, "w")
    f.write(data)
    f.close()

def scn_config_read(scn_filename, root):
    src_scn = os.path.join(root, scn_filename).replace('\\', '/')
    if os.path.isfile(src_scn):
        with open(src_scn, 'r') as stream:
            try:
                dict_object = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                raise Exception(exc)
    else:
        raise FileExistsError(f'File YAML with name "{src_scn.split()[0]}" does not exist in the input data '
                              f'directory!')
    return dict_object

# Read scenario for app
def read_scenario_runtime():

    src_scenario = os.path.join(TEMP_ROOT, 'temp_scn.yaml')
    if os.path.isfile(src_scenario):
        with open(src_scenario, 'r') as stream:
            dict_scenario = yaml.safe_load(stream)
    else:
        raise Exception('File YAML not found in temp directory')

    try:
        if 'ZMQ' in dict_scenario['SCEN_OUTPUTS']:
            attrs_live = dict_scenario['SCEN_OUTPUTS']['ZMQ']['attrs']
        else:
            attrs_live = []
    except TypeError:
        attrs_live = []
    # TODO: richiamare l'attributo da sim-.model_ completo!n anche per db
    scenario_name = dict_scenario['SCEN_CONFIG']['SCENARIO_NAME']
    start_date = dict_scenario['SCEN_CONFIG']['START_DATE']
    live_cache = set_live_cache(attrs_live)
    attrs_input = None
    if 'zmq_rcv' in dict_scenario['SIM_CONFIG']:
        attrs_input = dict_scenario['SIM_CONFIG']['zmq_rcv']['MODELS']['zmq_rcv']['PARAMS']['start_vrs']
    return [scenario_name, start_date, attrs_live,live_cache, attrs_input]

def set_live_cache(attrs_live, max_length=1000):
    live_cache = {}
    for attr in attrs_live:
        live_cache[attr] = deque(maxlen=max_length)
    live_cache['t'] = deque(maxlen=max_length)
    return live_cache


# ZMQ command sender
def create_command_sender(port = "5560"):
    context = zmq.Context()
    socket = context.socket(zmq.PUB)
    socket.bind("tcp://127.0.0.1:%s" % port)
    return  socket

# ZMQ Receiver for WebApp
def create_zmq_socket(zmq_port="5558"):
    """ Create a ZMQ SUBSCRIBE socket """
    context = zmq.Context()
    zmq_socket = context.socket(zmq.SUB)
    zmq_socket.connect("tcp://127.0.0.1:%s" % zmq_port)
    zmq_socket.setsockopt_string(zmq.SUBSCRIBE, '')

    return zmq_socket


def zmq_receiver():
    """ Receive data over ZMQ PubSub socket
    Returns json data
    """
    # Note - context managing socket as it can't be shared between threads
    # This makes sure the socket is opened and closed by whatever thread Dash gives it
    with create_zmq_socket() as socket:
        if socket.poll(1000,zmq.POLLIN): # TODO: dipende dalla velocità del simulatore
            msg = socket.recv_json()
        else:
            msg = json.loads('{}')
        # message structure from simulation [29700, {'power_dc': {'pv-0.PV_0': 365.2684652613373}, 'ghi': {'pv-0.PV_0': 72.5001, 'csv_meteo-0.meteo_0': 72.5001}, 'T_ext': {'pv-0.PV_0': -1.84, 'csv_meteo-0.meteo_0': -1.84}}]
        return msg


def retrive_outputs_db():
    out_db_list = {}
    Path(OUTPUTS_ROOT).mkdir(parents=True, exist_ok=True)
    for db in os.listdir(OUTPUTS_ROOT):
        out_db_list[db] = db
    return out_db_list


def retrive_entity_timeseries_db(db=None, default=False):
    if default == True:
        src_demo = os.path.join(OUTPUTS_ROOT, 'output_sim_demo.hdf5')
        if os.path.isfile(src_demo):
            d = h5py.File(src_demo, 'r')
        else:
            raise Exception('No outputs produced from demo simulation. Run demo first.')
    else:
        if db == None:
            raise Exception('No database selected!')
        src_db = os.path.join(OUTPUTS_ROOT, db)
        if os.path.isfile(src_db):
            d = h5py.File(src_db, 'r')
        else:
            raise Exception(f'No outputs produced from {db} scenario. Run {db} first.')
    entities_attrs_dict = defaultdict(lambda: defaultdict(list))
    entities = list(d['Series'].keys())
    for entity in entities:
        for attr in list(d['Series'][f'{entity}'].keys()):
            entities_attrs_dict[entity][attr] = list(d['Series'][f'{entity}'][attr][:])
    return default_to_regular(entities_attrs_dict)


def default_to_regular(d):
    if isinstance(d, defaultdict):
        d = {k: default_to_regular(v) for k, v in d.items()}
    return d


def load_graph_runtime():

    src_net_file = os.path.join(TEMP_ROOT, 'temp_gr_dataflow.graphml')

    graph = nx.read_graphml(src_net_file)
    try:
        graph.remove_node('zmq')
    except:
        pass
    try:
        graph.remove_node('db')
    except:
        pass

    # Nodes
    pos = nx.circular_layout(graph)   #fruchterman_reingold_layout(graph)
    Xn = [pos[k][0] for k in pos.keys()]
    Yn = [pos[k][1] for k in pos.keys()]
    trace_nodes = dict(type='scatter',
                       x=Xn,
                       y=Yn,
                       mode='markers+text',
                       marker=dict(size=28, color='#007FFF'),
                       text=list(pos.keys()),textposition='bottom center',
                       hoverinfo='text')
    # Middle node hidden
    middle_node_trace = dict(type='scatter',
                             x=[],
                             y=[],
                             text=[],
                             mode='markers+text',
                             hoverinfo='text', textposition='right',
                             marker=dict(size=28,opacity=0))

    # Edges
    Xe = []
    Ye = []
    for e1, e2, data in graph.edges(data=True):
        start = [pos[e1][0],pos[e1][1]]
        end = [pos[e2][0],pos[e2][1]]
        Xe, Ye = addEdge(start,end,Xe,Ye, lengthFrac=.9, arrowLength=0.06, dotSize=28, arrowPos='end')
        # Xe.extend([pos[e1][0], pos[e2][0], None])
        # Ye.extend([pos[e1][1], pos[e2][1], None])

        x=-random.random()*.2 + random.random()*.2
        middle_node_trace['x'].append((pos[e1][0] + pos[e2][0]) / 2 + pos[e1][0]*x)
        middle_node_trace['y'].append((pos[e1][1] + pos[e2][1]) / 2 - pos[e2][1]*x)
        middle_node_trace['text'].append(' - '.join(data.values()))

    trace_edges = dict(type='scatter',
                       mode='lines',
                       x=Xe,
                       y=Ye,
                       line=dict(width=4, color='#555555'),
                       hoverinfo='skip'
                       )
    axis = dict(showline=False,  # hide axis line, grid, ticklabels and  title
                zeroline=False,
                showgrid=False,
                showticklabels=False,
                title=''
                )
    layout = dict(title='Dataflow graph of the scenario',
                  font=dict(family='Balto',size=15),
                  #width=1500,
                  #height=1000,
                  #autosize=True,
                  showlegend=False,
                  xaxis=axis,
                  yaxis=dict(showline=False,  # hide axis line, grid, ticklabels and  title
                zeroline=False,
                showgrid=False,
                showticklabels=False,
                title='', scaleanchor = "x", scaleratio = 1
                ),
                  margin=dict(
                          l=50,
                          r=1,
                          b=1,
                          t=45,
                          pad=0,),
                  hovermode='closest',
                  plot_bgcolor='#ffffff',  # set background color
                  )

    return trace_nodes, trace_edges, middle_node_trace, layout

def plot_directed_graph():

    src_net_file = os.path.join(TEMP_ROOT, 'temp_gr_dataflow.graphml')

    g = nx.read_graphml(src_net_file)
    pos = nx.spring_layout(g)
    try:
        g.remove_node('zmq')
    except:
        pass
    try:
        g.remove_node('db')
    except:
        pass

    nx.draw(g, with_labels=True, pos=pos)

    edge_labels = {}
    for e1, e2, data in g.edges(data=True):
        edge_labels[(e1,e2)] = " ".join(data.values())

    nx.draw_networkx_edge_labels(g, pos,edge_labels=edge_labels)
    return

"""
Created on Fri May 15 11:45:07 2020
@author: aransil
"""

import math


# Start and end are lists defining start and end points
# Edge x and y are lists used to construct the graph
# arrowAngle and arrowLength define properties of the arrowhead
# arrowPos is None, 'middle' or 'end' based on where on the edge you want the arrow to appear
# arrowLength is the length of the arrowhead
# arrowAngle is the angle in degrees that the arrowhead makes with the edge
# dotSize is the plotly scatter dot size you are using (used to even out line spacing when you have a mix of edge
# lengths)
def addEdge(start, end, edge_x, edge_y, lengthFrac=1, arrowPos=None, arrowLength=0.025, arrowAngle=30, dotSize=20):
    # Get start and end cartesian coordinates
    x0, y0 = start
    x1, y1 = end

    # Incorporate the fraction of this segment covered by a dot into total reduction
    length = math.sqrt((x1 - x0) ** 2 + (y1 - y0) ** 2)
    dotSizeConversion = .0565 / 20  # length units per dot size
    convertedDotDiameter = dotSize * dotSizeConversion
    lengthFracReduction = convertedDotDiameter / length
    lengthFrac = lengthFrac - lengthFracReduction

    # If the line segment should not cover the entire distance, get actual start and end coords
    skipX = (x1 - x0) * (1 - lengthFrac)
    skipY = (y1 - y0) * (1 - lengthFrac)
    x0 = x0 + skipX / 2
    x1 = x1 - skipX / 2
    y0 = y0 + skipY / 2
    y1 = y1 - skipY / 2

    # Append line corresponding to the edge
    edge_x.append(x0)
    edge_x.append(x1)
    edge_x.append(None)  # Prevents a line being drawn from end of this edge to start of next edge
    edge_y.append(y0)
    edge_y.append(y1)
    edge_y.append(None)

    # Draw arrow
    if not arrowPos == None:

        # Find the point of the arrow; assume is at end unless told middle
        pointx = x1
        pointy = y1
        eta = math.degrees(math.atan((x1 - x0) / (y1 - y0)))

        if arrowPos == 'middle' or arrowPos == 'mid':
            pointx = x0 + (x1 - x0) / 2
            pointy = y0 + (y1 - y0) / 2

        # Find the directions the arrows are pointing
        signx = (x1 - x0) / abs(x1 - x0)
        signy = (y1 - y0) / abs(y1 - y0)

        # Append first arrowhead
        dx = arrowLength * math.sin(math.radians(eta + arrowAngle))
        dy = arrowLength * math.cos(math.radians(eta + arrowAngle))
        edge_x.append(pointx)
        edge_x.append(pointx - signx ** 2 * signy * dx)
        edge_x.append(None)
        edge_y.append(pointy)
        edge_y.append(pointy - signx ** 2 * signy * dy)
        edge_y.append(None)

        # And second arrowhead
        dx = arrowLength * math.sin(math.radians(eta - arrowAngle))
        dy = arrowLength * math.cos(math.radians(eta - arrowAngle))
        edge_x.append(pointx)
        edge_x.append(pointx - signx ** 2 * signy * dx)
        edge_x.append(None)
        edge_y.append(pointy)
        edge_y.append(pointy - signx ** 2 * signy * dy)
        edge_y.append(None)

    return edge_x, edge_y


