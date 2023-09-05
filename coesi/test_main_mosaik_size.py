import time

import mosaik.util

from scenario import World

from definitions import *
from mosaik import util

import numpy as np
import json


t = time.time()

""" Setup Mosaik """

MK_CONFIG = {
    'addr': ('127.0.0.1', 5555),
    'start_timeout': 10,  # seconds default 10
    'stop_timeout': 10,  # seconds default 10
}

SIM_CONFIG = {
    "agentsim1": {
        #"connect": "192.168.177.119:5680"
        "cmd": "python test_mk_agent.py %(addr)s",
        "cwd": SIM_ROOT + '/'
    },
    "agentsim2": {
        "connect": "192.168.177.119:5680"
        # "cmd": "python test_mk_agent.py %(addr)s",
        # "cwd": SIM_ROOT + '/'
    },
    "database": {
        "python": "mk_sims.mk_hdf5:MosaikHdf5",
        "cwd": SIM_ROOT + '/'
    }
}

START_DATE = '2015-01-01 00:00:00'

""" Starting Simulators """
world = World(sim_config=SIM_CONFIG, mosaik_config=MK_CONFIG)

START_DAY = 0
DAYS = 0.00001

START_TIME = START_DAY * (60 * 60 * 24)
STOP_TIME = 2#(DAYS + START_DAY) * (60 * 60 * 24)

## System Simulators ##
sim_meta = {
    'models': {
        'agent1': {
            'public': True,
            'params': ["start_vrs_u", "start_vrs_y"],
            'attrs': ["u1", "y1", "memory", "output"],
        },
    }
}

agentsim1 = world.start("agentsim1", step_size=1, sim_meta=sim_meta)

sim_meta = {
    'models': {
        'agent2': {
            'public': True,
            'params': ["start_vrs_u", "start_vrs_y"],
            'attrs': ["u1", "y1", "memory", "output"],
        },
    }
}

agentsim2 = world.start('agentsim2', step_size=1, sim_meta=sim_meta)

sim_meta_db = {
    'models': {
        'db': {
            'public': True,
            'any_inputs': True,
            'params': ["filename", "scn_config_file", "buf_size", "dataset_opts"],
            'attrs': [],
        }
    }
}
database = world.start('database', step_size=1,duration=STOP_TIME,sim_meta=sim_meta_db)

""" Instantiating models """

## Communication models ##


size = 2000 # 2000 to obtain total of more 10 Mb of data
value = 1
start_vrs_u = {"u1": size} # dimensione matrice quadrata size*size
# start all INPUT variables
start_vrs_y = {"y1": value} # size of u, with number in y
#agents1 = agentsim1.agent1.create(num=1,start_vrs_u=start_vrs_u, start_vrs_y=start_vrs_y)
agent1 = agentsim1.agent1(start_vrs_u=start_vrs_u, start_vrs_y=start_vrs_y)

start_vrs_u = {"u1": size}
# start all INPUT variables
start_vrs_y = {"y1": value}
#agents2 = agentsim2.agent2.create(num=1,start_vrs_u=start_vrs_u, start_vrs_y=start_vrs_y)
agent2 = agentsim2.agent2(start_vrs_u=start_vrs_u, start_vrs_y=start_vrs_y)


db = database.db(filename="test_mosaik_size")


""" Connecting entities """


#util.connect_randomly(world, agents1, agents2, ("y1", "u1"), evenly=True)

# util.connect_many_to_one(world, agents1, db, "memory", "output")
#
# util.connect_many_to_one(world, agents2, db, "memory", "output")


world.connect(agent1,agent2,("y1","u1"))
world.connect(agent2,agent1,("y1","u1"),time_shifted=True, initial_data={'y1': json.dumps(np.full((size, size),
                                                                                                  value).tolist())})
world.connect(agent1,db, "memory", "output")
world.connect(agent2,db, "memory", "output")

""" Running the simulation """
world.run(until=STOP_TIME)

elapsed = time.time() - t



print('Simulation time : ', elapsed)
