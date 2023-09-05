#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Flask application for the CoSim WepApp.

Research group of Politecnico di Torino Energy Center Lab.

- author: Daniele Salvatore Schiera
- copyright: Copyright 2020. Energy Center Lab - Politecnico di Torino"
- credits: Daniele Salvatore Schiera
- maintainer: Daniele Salvatore Schiera
- email: daniele.scheira@polito.it
- status: Development
"""
import datetime
import json
import os
import sys
from pathlib import Path

import dash
import plotly.graph_objs as go
from dash import dcc
from dash import html
from dash.dependencies import Input, Output, State


from coesi.utils import read_scenario_runtime, zmq_receiver, retrive_outputs_db, retrive_entity_timeseries_db, \
    load_graph_runtime

# Load stylesheets
external_css = ["https://maxcdn.bootstrapcdn.com/bootstrap/4.0.0/css/bootstrap.min.css"]  # ['https://codepen.io
# /chriddyp/pen/bWLwgP.css']  # [
# "https://cdnjs.cloudflare.com/ajax/libs/materialize
# /1.0.0/css/materialize.min.css"] #[
# "https://codepen.io/chriddyp/pen/bWLwgP.css"]

# Load scripts
external_js = []  # ["https://cdnjs.cloudflare.com/ajax/libs/materialize/1.0.0/js/materialize.min.js"]

# Run app Dash, suppress_callback_exceptions=True permits to avoid warnings if some html components are not directly
# loaded in layout but added in callbacks
app = dash.Dash(__name__, external_stylesheets=external_css, external_scripts=external_js,
                suppress_callback_exceptions=False, title='CoSim Dashboard', update_title=None,
                assets_folder=os.getcwd() + '/resources/assets/')

# init settings for runtime scenario loading # TODO: integrare tutto in callback  tab stream senza inizializzare prima
global live_cache  # TODO: avoid!
scenario_name, start_date, attrs_live, live_cache, attrs_input = read_scenario_runtime()

global attr_sender
# if attrs_input:
#     attr_sender = create_command_sender() # TODO: due zmq non vanno insieme
# start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d %H:%M:%S')
# live_cache = set_live_cache(attrs_live, max_length=500)

# Init database list in directory outputs.
# default_db = 'output_sim_demo.hdf5'
# TODO: ATT se si si sta runnando la demo, ouput sim demo dovrebbe essere non utilizzabile! perche nel frattempo sta
#  scrivendo il file sopra, e non potrei aprirlo!
outputs_db_list = retrive_outputs_db()
# entities_attrs_dict = retrive_entity_timeseries_db(default=True)


# Layout of the WebApp
app.layout = html.Div(className='container-fluid', children=
[html.Div(className='row align-items-center', children=
[html.Div([html.H1(f'CoSim Web Dashboard \n (prototype)', style={'text-align': 'center'})],
          className='col-10'),
 html.Div(className='col', children=
 [html.Div(className='float-right', children=html.Img(src='/assets/logoEC-Lab.png', style={"height": 100}))
  ]),

 ]),
 html.Div(children=[
     dcc.Tabs(id='tabs', children=[
         dcc.Tab(value='net', label='Entity-Dataflow View', children=[
             html.Div(id='network-content', children=[html.Div(id='network-graph',
                                                               className='col')],
                      className='row'
                      )]),
         dcc.Tab(value='live-stream', label='Scenario Data Stream', children=[
             html.Div(id='inter-live_cache', children=json.dumps({}), style={'display': 'none'}),
             html.Div(children=[
                 html.P(children=f'Data streamed from run-time simulation of the scenario. \n Select the attributes to '
                                 f'show the live timeseries:'),
                 # html.Button('ON/OFF streaming data', id='button'),
                 html.Div(id='attr-selection', children=[
                     dcc.Dropdown(id='attr-name',
                                  multi=True
                                  )]),
                 html.Div(id='attr-tuning', className='row'),  # TODO: tuning parameters
                 html.Div(id='graph-content', children=html.Div(id='graphs')),
                 dcc.Interval(
                     id='graph-update',
                     interval=1 * 500,  # in milliseconds # TODO: dipende dalla velocità di simulazione
                     n_intervals=0
                 )
             ])]),
         dcc.Tab(value='data', label='Datasets timeseries', children=[
             html.Div([
                 html.P('Select the database (from Outputs folder):'),
                 dcc.Dropdown(
                     id='select-db',
                     # options=[{'label': s, 'value': s} for s in outputs_db_list.keys()],
                     # value=default_db if default_db in outputs_db_list.keys() else
                     # list(outputs_db_list.keys())[0],
                     multi=False
                 ),
                 html.P('Select the Entity:'),
                 dcc.Dropdown(id='select-entity',
                              multi=True
                              ),
                 html.Div(id='inter-value', children=json.dumps({}), style={'display': 'none'}),
                 html.P('Select the attributes to plot the timeseries:'),
                 dcc.Dropdown(id='select-attr',
                              multi=True
                              ),
                 html.Div(id='graph-content-db', children=html.Div(id='graphs-db'))

             ])])
     ])
 ])
 ])


## Callbacks

## Scenario view
@app.callback(Output('network-graph', 'children'),
              [Input('tabs', 'value')])
def load_network(t):
    if t == 'net':
        # init graph plot of the runtime scenario
        trace_nodes, trace_edges, hidden_nodes, layout = load_graph_runtime()
        # fig = go.Figure(data=[trace_edges, trace_nodes], layout=layout)
        graph = dcc.Graph(
            id='Network',
            figure={'data': [trace_edges, trace_nodes, hidden_nodes], 'layout': layout}, style={'height': '1000px'})
        return graph
    else:
        return []


# # #Update attr-list
@app.callback(Output('attr-name', 'options'),
              [Input('tabs', 'value')])
def update_live_attr(tab):
    if tab == 'live-stream':
        scenario_name, start_date, attrs_live, live_cache, attrs_input = read_scenario_runtime()
        # live_json = json.dumps(live_cache)
        # start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d %H:%M:%S')
        # if not attrs_input:
        #     children = []
        # else:
        #     children = [
        #                html.Div([dcc.Dropdown(id='attr-input', multi=False,options=[{'label': s, 'value': s} for s in
        #                          attrs_input.keys()])], className='col-4'),
        #                html.Div([dcc.Input(id='input-value', value=None, type='number')], className='col'),
        #                html.Div([html.Button('Submit', id='submit', n_clicks=0)],
        #                         className='col'),
        #                html.P(id='placeholder')
        #            ],

        return [{'label': s, 'value': s} for s in attrs_live]
    else:
        return []


# TODO: tuning of parameters
# @app.callback(Output('placeholder', 'children'),
#               [Input('submit', 'n_clicks')],
#               [State('attr-input', 'value'),
#                State('input-value', 'value')])
# def send_value_attr(c, attr, value):
#     data = {}
#     data[attr] = value
#     if c > 0:
#         if attr != 'empty':
#             attr_sender.send_json(data)
#             return []
#         else:
#             return ['No tuning of parameters']


# Live Stream plot update
@app.callback(Output('graphs', 'children'),
              [Input('attr-name', 'value'),
               Input('graph-update', 'n_intervals')],
              [State('attr-name', 'options')])
def update(data_names, n, attrs_options):
    graphs = []
    # attrs_options = [HeatPump_HP.Power,HeatPump_HP.MV]
    if data_names:
        d = zmq_receiver()
        # [17400,
        #  {'Power': {'fmu_pyfmi_sim-0.HeatPump_HP': 1814.8638286090002},
        #   'MV': {'fmu_pyfmi_sim-0.HeatPump_HP': 0.027826809799222123},
        #   'TRooMea': {'fmu_pyfmi_sim2-0.Building_Home': 15.98094108517095}}]
        if bool(d):
            for attr in [x['label'] for x in attrs_options]:  # HeatPump_HP.Power
                attr_name = attr.split('.')[1]  # Power
                entity = attr.split('.')[0]  # HeatPump_HP
                for sim_entity in d[1][attr_name].keys():  # fmu_pyfmi_sim-0.HeatPump_HP
                    if sim_entity.split('.')[1] == entity:  # HeatPump_HP== HeatPump_HP
                        try:
                            live_cache[attr].append(d[1][attr_name][sim_entity])
                        except KeyError:
                            continue
            live_cache['t'].append(d[0])  # start_date + datetime.timedelta(seconds=d[0]))
            for data_name in data_names:
                data = go.Scatter(line={'shape': 'hv'},
                                  x=list(live_cache['t']),
                                  y=list(live_cache[data_name]),
                                  name='Scatter',
                                  mode='lines+markers',
                                  # fill='tozeroy',
                                  # fillcolor='#6897bb',
                                  marker=dict(size=3))

                graphs.append(html.Div(dcc.Graph(
                    id=data_name,
                    animate=False,
                    figure={'data': [data], 'layout': go.Layout(xaxis=dict(range=[min(live_cache['t']),
                                                                                  max(live_cache['t'])]),
                                                                yaxis=dict(range=[min(live_cache[data_name]),
                                                                                  max(live_cache[data_name])]),
                                                                title='{}'.format(data_name))}
                )))  # , className=class_choiche))  # in layout -> margin={'l': 50, 'r': 1, 't': 45, 'b': 1},
            return graphs
        else:
            data = []
            return html.Div('No simulation in run-time detected. Waiting..', className='col')
    else:
        data = []
        return html.Div('No attributes selected', className='col')


## DB plotting
# Dropdown scenarios update
@app.callback(Output('select-db', 'options'),
              [Input('tabs', 'value')])
def update_list_scenario(tab):
    if tab == 'data':
        outputs_db_list = retrive_outputs_db()
        return [{'label': s, 'value': s} for s in sorted(list(outputs_db_list.keys()), reverse=True)]
    else:
        return []


# selection db
@app.callback([Output('select-entity', 'options'),
               Output('inter-value', 'children')],
              [Input('select-db', 'value')])
def selection_db(db):
    if db is not None:
        entities_attrs_dict = retrive_entity_timeseries_db(db)
        ent_json = json.dumps(entities_attrs_dict)
        return [[{'label': s, 'value': s} for s in entities_attrs_dict.keys()], ent_json]
    else:
        return [[], []]


# selection entity
@app.callback(Output('select-attr', 'options'),
              [Input('select-entity', 'value')],
              [State('inter-value', 'children')])
def selection_entity(entities, value):
    attr_list = []
    if entities is not None:
        entities_attrs_dict = json.loads(value)
        for entity in entities:
            attr_list.extend(list(entities_attrs_dict[entity].keys()))
        return [{'label': s, 'value': s} for s in attr_list]
    else:
        return []


# plot attr time series
@app.callback(Output('graphs-db', 'children'),
              [Input('select-attr', 'value')],
              [State('select-entity', 'value'),
               State('inter-value', 'children')])
def update_graph_attr(attrs, entities, data):
    ctx = dash.callback_context
    graphs = []
    # figs = make_subplots(rows=len(attrs), cols=1, shared_xaxes=True,
    #                      vertical_spacing=0.001)

    start_date = datetime.datetime(2015, 1, 1)  # TODO: prendere dallo scenario
    if ctx.triggered[0]['prop_id'].split('.')[0] == 'select-attr':
        if entities is not None:
            if attrs is not None:
                # if len(attrs) > 2:
                #     class_choiche = 'col-4'
                # elif len(attrs) == 2:
                #     class_choiche = 'col-2'
                # else:
                #     class_choiche = 'col'
                d = json.loads(data)
                for entity in entities:
                    for attr in attrs:
                        id_graph = 1
                        if attr in list(d[entity].keys()):
                            fig = go.Scatter(line={'shape': 'hv'},
                                             x=[start_date + datetime.timedelta(seconds=x) for x in d['time']['t']],
                                             y=d[entity][attr],
                                             name=entity + '.' + attr,
                                             mode='lines+markers',
                                             # fill='tozeroy',
                                             # fillcolor='#6897bb',
                                             marker=dict(size=3))
                            #
                            # figs.add_trace(fig, row=id_graph,col=1)
                            # figs.add_traces()
                            # id_graph = id_graph +1
                            graphs.append(html.Div(dcc.Graph(
                                id=str(id_graph),  # entity + '.' + attr,
                                figure={'data': [fig], 'layout': go.Layout(title='{}'.format(entity + '.' +
                                                                                             attr), yaxis=dict(
                                    range=[min(d[entity][attr]),
                                           max(d[entity][attr])]))}
                            ), className='col'))  # class_choiche))
                            id_graph = +1

        # graphs = html.Div(dcc.Graph(figure=figs))

    return graphs


# @app.callback(Output('relayout','children'),
#               [Input('0','relayoutData')])
# def relayout_event():

if __name__ == '__main__':
    app.run_server(debug=True)  # , threaded=False, processes=4)
    # processes permits to o enable your dash app to handle multiple callbacks in parallel. For production
    # applications, it’s recommended that you use gunicorn.
