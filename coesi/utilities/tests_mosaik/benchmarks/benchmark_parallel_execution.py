import os
import sys

import mosaik

from utilities.tests_mosaik.benchmarks.argparser import argparser

sys.path.insert(0, os.getcwd())

print(sys.path)
from utilities.tests_mosaik.plotting.execution_graph_tools import plot_execution_graph, plot_execution_graph_st


args, world_args, run_args = argparser(until=10,remote=1)
if args.plot:
    world_args['debug'] = True

SIM_CONFIG = {
    0: {'TestSim': {'python': 'uesa.utilities.tests_mosaik.simulators.generic_test_simulator:TestSim'}},
    1: {'TestSim': {'cmd': '%(python)s generic_test_simulator.py %(addr)s',
                    "cwd": r"D:\Projects\PycharmProjects\casestudy\uesa\utilities\tests_mosaik\simulators"}}
}

world = mosaik.World(SIM_CONFIG[args.remote], **world_args)

a = world.start('TestSim', step_size=1, wallclock_duration=.05).A()
b = world.start('TestSim', step_size=2, wallclock_duration=.05).A()

world.connect(a, b, ('val_out', 'val_in'))

world.run(**run_args)

if args.plot:
    plot_execution_graph(world)
    plot_execution_graph_st(world)
