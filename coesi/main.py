#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Co-simulation for Energy Systems Integration (CoESI).

Tool-chain web app application to perform simulation of urban energy scenarios and use cases, based on co-simulation
and FunctionalMock-up Interface through Mosaik engine implementation.

Main run script for running scenario.

Research group of Politecnico di Torino Energy Center Lab.

- author: Daniele Salvatore Schiera
- maintainer: Daniele Salvatore Schiera
- email: daniele.schiera@polito.it
- status: Development
"""
import sys
import argparse
import logging
from datetime import *
import collections
import socket

import mosaik
from mosaik import util
from networkx.readwrite.graphml import write_graphml

from definitions import *


sys.path.insert(0, PROJECT_ROOT)

#from tests import villas_pb2

from utils import *



# TODO: usare ATTRDICT che è migliore per il parsing con yaml si puo suare la notazione col dot
def main(configs, SCENARIO_NAME, START_DATE, DAYS, STOP_TIME, RT_FACTOR, RT=False):
    # Scenario setup
    # SCENARIO_NAME, START_DATE, DAYS = list(configs['SCEN_CONFIG'].values())
    # STOP_TIME = (DAYS) * (60 * 60 * 24)

    ## World set up: Mosaik, Simulators setup and start
    simulators, models = simulators_settings(configs, START_DATE, DAYS)

    ## Instantiationg models
    G = nx.DiGraph()
    entities = models_instantiation(simulators, models, G)

    connection_entities(entities, configs, G)
    write_graphml(G, TEMP_ROOT + '/temp_gr_dataflow.graphml')

    time.sleep(1)

    if RT == False:
        run = input('Run Simulation? y/N')
        if run == 'y':
            sim_start_time = datetime.now()
            world.run(until=STOP_TIME, rt_factor=RT_FACTOR, rt_strict=False, lazy_stepping=False)
            # lazy stepping False fa proseguire i sim allo steps fin dove richiesto! piu memoria ma piu veloce!
            # TODO non usare
            # linee
            # di
            # codice
            # ricopiare, piuttosto fare una funzione (è presente qui e nell'altro ciclo)
            # rtfactor = 1 1 simulation time unit == takes 1 second
            delta_sim_time = datetime.now() - sim_start_time
            print(f'\nSimulation took {delta_sim_time}')
        else:
            sys.exit()
    elif RT == True:
        localIP = '130.192.177.102'
        localPort = 13000
        bufferSize = 1024

        UDPServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        UDPServerSocket.bind((localIP, localPort))

        # print("UDP server up and listening")
        # start = False
        # msg = villas_pb2.Message()
        # print("Waiting")
        # while (not start):
        #     payload = UDPServerSocket.recv(bufferSize)
        #     print(payload)
        #     msg.ParseFromString(payload)
        #     STOP_TIME = msg.samples[0].values[0].f
        #     start = True
        #     UDPServerSocket.close()

        sim_start_time = datetime.now()
        print(STOP_TIME)
        world.run(until=int(STOP_TIME), rt_factor=RT_FACTOR, rt_strict=False, lazy_stepping=False)
        # rtfactor = 1 1 simulation time unit == takes 1 second
        delta_sim_time = datetime.now() - sim_start_time
        print(f'\nSimulation took {delta_sim_time}')
    return world, entities


def simulators_settings(configs, START_DATE, DAYS):
    sims_configs = configs['SIM_CONFIG']
    num_sims = len(configs['SIM_CONFIG'])

    ## Mosaik setup
    MK_CONFIG = {
        'addr': ('127.0.0.1', 5555),
        'start_timeout': 120,  # seconds default 10
        'stop_timeout': 30,  # seconds default 10
    }

    ## Simulators setup
    SIM_CONFIG = {}
    SIM_META = collections.defaultdict(dict)
    # SIM_META = {}
    SIM_MODEL_PARAM_VALUES = collections.defaultdict(dict)

    for sim, conf in sims_configs.items():  # TODO: rivedere bene tutto il ciclo
        SIM_CONFIG[sim] = conf['RUN_PROCESS']
        SIM_META[sim]['models'] = {}
        if 'cwd' not in SIM_CONFIG[sim]:
            SIM_CONFIG[sim]['cwd'] = SIM_ROOT + '/'  # TODO: migliorare
        if 'python' in SIM_CONFIG[sim]:
            SIM_CONFIG[sim]['python'] = 'mk_sims.' + SIM_CONFIG[sim]['python']
        if 'py_lib' in SIM_CONFIG[sim]:
            SIM_CONFIG[sim]['python'] = SIM_CONFIG[sim]['py_lib']



        for model, meta in conf['MODELS'].items():
            dict_params = meta['PARAMS']  # dizionario attributi e valori
            if isinstance(meta['PARAMS'], dict):
                meta['PARAMS'] = list(dict_params.keys())
            else:
                meta['PARAMS'] = []
            # SIM_META[sim] = {'models': {model: {}}}
            SIM_META[sim]['models'][model] = {}
            for key, attr in meta.items():
                SIM_META[sim]['models'][model][f'{key}'.lower()] = attr

            # SIM_MODEL_PARAM_VALUES[sim] = {model: dict_params}
            SIM_MODEL_PARAM_VALUES[sim][model] = dict_params

    if 'time_resolution' in configs['SCEN_CONFIG']:
        time_res = configs['SCEN_CONFIG']['time_resolution']
    else:
        time_res = 1.

    global world
    world = mosaik.World(sim_config=SIM_CONFIG, mosaik_config=MK_CONFIG, time_resolution=time_res, debug=True)
    ## Starting Simulator
    simulators = {}

    for sim in sims_configs:
        if 'start_date' in sims_configs[sim]['PARAMS']:
            if sims_configs[sim]['PARAMS']['start_date'] == 'START_DATE':
                sims_configs[sim]['PARAMS']['start_date'] = START_DATE
        if 'days' in sims_configs[sim]['PARAMS']:
            if sims_configs[sim]['PARAMS']['days'] == 'DAYS':
                sims_configs[sim]['PARAMS']['days'] = DAYS
        # if 'time_resolution' in sims_configs[sim]['PARAMS']:
        #     time_res = sims_configs[sim]['PARAMS']['time_resolution']
        #     del sims_configs[sim]['PARAMS']['time_resolution']
        if 'py_lib' in SIM_CONFIG[sim].keys():
            simulators[sim] = world.start(sim, **sims_configs[sim][
                'PARAMS'])
        else:
            simulators[sim] = world.start(sim, sim_meta=SIM_META[sim], **sims_configs[sim]['PARAMS'])

        if 'solver' in sims_configs[sim]['PARAMS'].keys():
            getattr(simulators[sim], "solver_call")(sims_configs[sim]['PARAMS']['solver'])
    return simulators, SIM_MODEL_PARAM_VALUES


def models_instantiation(simulators, models, G):
    #TODO dict con i nomi dei sim
    #TODO nel sid evidare l'aggiunta di -int perchè tnato il sid viene preso dal nome univoco nello yaml
    #todo children name potrebbero non doversi portare il nome del model visto che abbiamo cambiato entities


    entities = {}
    for sim, mod in models.items():
        entities[sim]={}
        if sim == 'heating_system': ## questa ggiunta mi serve per automatizzare gli scenari sto semplicemente riordinando il dict in funzione dei numeri dei sim
            from collections import OrderedDict
            skeys = sorted(mod.keys(), key=lambda s: int(s.split(' ')[-1]))
            mod = OrderedDict((k, mod[k]) for k in skeys)
        for model, param in mod.items():
            if param == []:
                param = {}
            if "num" in param.keys():
                num = param['num']
                del param['num']

                entity = getattr(getattr(simulators[sim], model),'create')(num,**param)
                for n in range(num):
                    entities[sim][entity[n].eid] = entity[n]
                # if entity.eid != 'zmq' and 'db':  # TODO da controllare questa logica
                #     G.add_node(entity.eid)
            else:
                entity = getattr(simulators[sim], model)(**param)
                entities[sim][entity.eid] = entity
                # if entity.eid != 'zmq' and 'db':  # TODO da controllare questa logica
                #     G.add_node(entity.eid)
    #todo add a graphical visualization of entities in the simulation world
    return entities

def entity_eid(entity, entities):
    if len(entity.split('.')) > 2:
        sim,model,child_name = entity.split('.')
        id_child = [getattr(i,'eid') for i in getattr(entities[sim][model],'children')].index(child_name)
        return getattr(entities[sim][model],'children')[id_child]
    else:
        sim, model = entity.split('.')
        return entities[sim][model]

def connection_entities(entities, configs, G):
    connections = configs['CONNECTIONS']

    if connections is not None:
        for cn in connections.values():
            attrs_pairs = []
            for attr in cn['ATTRS']:
                if isinstance(attr, list):
                    attrs_pairs.append(tuple(attr))
                else:
                    attrs_pairs.append(attr)

            #CONNESSIONI MULTIPLE many_to_one
            #lato FROM
            if isinstance(cn['FROM'], list):
                many = [ entity_eid(entity,entities) for entity in cn['FROM']]
                one = entity_eid(cn['TO'], entities)
                if 'PARAMS' in cn:
                    util.connect_many_to_one(world, many, one, *attrs_pairs, **cn['PARAMS'])
                else:
                    util.connect_many_to_one(world, many, one, *attrs_pairs)

            #lato TO
            elif isinstance(cn['TO'], list):
                many = [entity_eid(entity, entities) for entity in cn['TO']]
                one = entity_eid(cn['FROM'], entities)
                if 'PARAMS' in cn:
                    for to in many:
                        world.connect(one, to, *cn['ATTRS'], **cn['PARAMS'])
                else:
                    for to in many:
                        world.connect(one, to, *cn['ATTRS'])
            #CONNESSIONI SINGOLE one_to_one

            else:
                fro = entity_eid(cn['FROM'], entities)
                to = entity_eid(cn['TO'], entities)
                if 'PARAMS' in cn:
                    world.connect(fro, to, *attrs_pairs, **cn['PARAMS'])
                else:
                    world.connect(fro, to, *attrs_pairs)



    if configs['SCEN_OUTPUTS'] != None:
        for scn_out in configs['SCEN_OUTPUTS'].keys():
            # for entity in entities.values():
            #     # todo. AGIRE SUL YAML PER SCEN_OUPUTS PER INDICARE SIA L'ENTITA CHE L'ATTRIBUTO DA ESPORTARE. MA
            #     #  SOPRATTUTTO
            #     #  DA CHE ENTITA PARTE.
            #     for attr in entity.sim.meta['models'][entity.type]['attrs']:
            #         eid_attr = entity.eid + '.' + attr
            #         if eid_attr in configs['SCEN_OUTPUTS'][scn_out]['attrs']:
            #             world.connect(entity, entities[scn_out.lower()], attr)
            sim_model = 'database.'+scn_out.lower()
            for ent_attr in configs['SCEN_OUTPUTS'][scn_out]['attrs']:
                ent_attr = ent_attr.split('.')
                if len(ent_attr) == 3:
                    entity = '.'.join(ent_attr[:2])
                    world.connect(entity_eid(entity, entities), entity_eid(sim_model, entities), ent_attr[2])
                elif len(ent_attr) == 4:
                    entity = '.'.join(ent_attr[:3])
                    world.connect(entity_eid(entity, entities), entity_eid(sim_model, entities), ent_attr[3])
                else:
                    # todo caNCELLARE Non serve
                    # world.connect(getattr(entities[ent_attr[0]],"children")[int(ent_attr[1])],
                    #               entities[scn_out.lower()],
                    #               ent_attr[2])
                    world.connect(getattr(entities[ent_attr[0]],"children")[[a.eid for a in getattr(entities[ent_attr[
                        0]],"children")].index(ent_attr[1])],
                                  entities[scn_out.lower()],
                                  ent_attr[2])


def scenario_config_setup(scn_config):
    configs = scn_config_load(scn_config, SCENARIO_ROOT)
    scn_outputs = configs['SCEN_OUTPUTS']

    START_DATE = configs['SCEN_CONFIG']['START_DATE']
    DAYS = configs['SCEN_CONFIG']['DAYS']
    SCENARIO_NAME = configs['SCEN_CONFIG']['SCENARIO_NAME']
    if 'time_resolution' in configs['SCEN_CONFIG']:
        time_res = configs['SCEN_CONFIG']['time_resolution']
    else:
        time_res = 1.
    STOP_TIME = int((DAYS) * (60 * 60 * 24) / time_res)
    RT_FACTOR = configs['SCEN_CONFIG']['RT_FACTOR']
    # webapp setup
    if configs['SCEN_OUTPUTS'] != None:
        if 'ZMQ' in scn_outputs:
            zmq_config = scn_config_load('webapp_config.yaml', RESOURCE_ROOT + '/sim_templates')  # TODO: da migliorare
            zmq_config['ZMQ']['PARAMS']['step_size'] = scn_outputs['ZMQ']['step_size']
            zmq_config['ZMQ']['PARAMS']['duration'] = STOP_TIME
            configs['SIM_CONFIG'].update(zmq_config)
        # DB setup
        if 'DB' in scn_outputs:
            db_config = scn_config_load('db_hdf5_config.yaml', RESOURCE_ROOT + '/sim_templates')
            db_config['database']['PARAMS']['step_size'] = scn_outputs['DB']['step_size']
            db_config['database']['PARAMS']['duration'] = STOP_TIME
            db_config['database']['MODELS']['db']['PARAMS']['filename'] = SCENARIO_NAME
            configs['SIM_CONFIG'].update(db_config)
            # db_config['database']['MODELS']['db']['PARAMS']['scn_config_file'] = configs
        if 'INFLUXDB' in scn_outputs:
            db_config = scn_config_load('db_influxdb_config.yaml', RESOURCE_ROOT + '/sim_templates')
            db_config['influxdb']['PARAMS']['step_size'] = scn_outputs['INFLUXDB']['step_size']
            db_config['influxdb']['MODELS']['db']['PARAMS']['scenario_name'] = SCENARIO_NAME
            configs['SIM_CONFIG'].update(db_config)
            # db_config['database']['MODELS']['db']['PARAMS']['scn_config_file'] = configs

    return [configs, SCENARIO_NAME, START_DATE, DAYS, STOP_TIME, RT_FACTOR]


if __name__ == '__main__':
    import time
    from pandapipes.pipeflow import set_logger_level_pipeflow

    # logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    # log = logging.getLogger(__name__)
    # log.setLevel(logging.DEBUG)
    # set_logger_level_pipeflow('DEBUG')
    # ch = logging.StreamHandler()
    # ch.setLevel(logging.DEBUG)

    # # Logging settings #TODO: da sviluppare
    # create logger with
    # log = logging.getLogger(__name__)
    # log.setLevel(logging.DEBUG)
    #
    # # create formatter and add it to the handlers
    # formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    #
    # # create file handler which logs even debug messages
    # fh = logging.FileHandler('uesalog.log')
    # fh.setLevel(logging.DEBUG)
    # fh.setFormatter(formatter)
    # log.addHandler(fh)
    #
    # # create console handler with a higher log level
    # ch = logging.StreamHandler()
    # ch.setLevel(logging.ERROR)
    # ch.setFormatter(formatter)
    # log.addHandler(ch)

    print('UESA started.')
    # Run the simulation.

    # Default settings
    scenario_default = r'test_FMU_rc_modelica.yaml'  # r'test_building.yaml'
    webapp = False
    RT = False


    parser = argparse.ArgumentParser(description='Command line execution of scenario with uesa.')
    parser.add_argument('-s', '--scn_config', type=str, help='Name of the scenario configuration yaml file. It must '
                                                             'be in scenarios directory',
                        default=scenario_default)
    parser.add_argument('-w', '--webapp', type=bool, default=webapp, help='Run the WebApp. Default deactivated.')
    parser.add_argument('-rt', '--real_time', type=bool, default=RT, help='Run the RT simulation with Opal-RT. '
                                                                          'Default deactivated.')

    args = parser.parse_args()
    if len(sys.argv) < 2:
        scenario = input("Scenario name (leave empty for scenario demo): ")
        if scenario == '':
            scenario = scenario_default
            print(f"It was not specified any scenario configuration file. The scenario default {scenario_default} "
                  f"will "
                  f"be "
                  f"used.\n Use -h to "
                  f"get "
                  "more details on how to use uesa commands.\n")
        else:
            scenario = scenario + '.yaml'
            print(f'{scenario}.yaml selected.')
        args.scn_config = scenario





    act_wa = 'deactivated'
    act_rt = 'deactivated'
    if args.webapp:
        act_wa = 'activated'
    if args.real_time:
        act_rt = 'activated'

    print(f"Scenario {args.scn_config} loaded.\n"
          f"Webapp dashboard {act_wa}.\n"
          f"Real-Time simulation {act_rt}.")

    configs, SCENARIO_NAME, START_DATE, DAYS, STOP_TIME, RT_FACTOR = scenario_config_setup(args.scn_config)

    if configs['SCEN_OUTPUTS'] != None:
        if args.webapp or 'ZMQ' in configs['SCEN_OUTPUTS'].keys():
            # start_webapp()
            print('WebDash starting..')
            from subprocess import Popen, PIPE


            process = Popen(['python', 'webapp.py'])  # , stdout=PIPE)
            time.sleep(3)
            # flag = 0
            # while True:
            #     x = process.stdout.readline().strip().decode('utf-8')
            #     # if "Dash" in x:
            #     #     break
            #     print(x)
            #     flag += 1
            #     if flag == 7:
            #         break
            print('WebDash activated.')

    # import tempfile # TODO: per controllare il processo se è ancora in corso
    # temp = tempfile.NamedTemporaryFile(prefix='pid_uesa_')
    # pid = str(os.getpid())
    # temp.write(pid)

    print('\nRunning Simulation..\n')
    world, entities = main(configs, SCENARIO_NAME, START_DATE, DAYS, STOP_TIME, RT_FACTOR, RT=args.real_time)

    # remember to close the handlers
    # for handler in log.handlers:
    #     handler.close()
    #     log.removeFilter(handler)
    # sys.exit(0)  # comment if you want outputs in console
