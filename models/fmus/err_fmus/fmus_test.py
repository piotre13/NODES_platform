import sys
sys.path.insert(0, '/usr/local/EnergyPlus-23-1-0')
from pyenergyplus.plugin import EnergyPlusPlugin
from pyenergyplus.plugin_tester import EnergyPlusPluginTesting
from pyenergyplus.api import EnergyPlusAPI


ARGS = [
        '--weather',
        '/home/pietrorm/Documents/CODE/NODES_platform/data/meteo_file/meteo_bousson.epw' ,
        '--output-directory',
        'outputs',
        '--output-prefix',
        'plug',
        '--readvars',
        '--output-suffix',
        'L',
        'SingleFamilyHouse_0.idf'
    ]

api = EnergyPlusAPI()
state = api.state_manager.new_state()
api.runtime.run_energyplus(state, ARGS)
