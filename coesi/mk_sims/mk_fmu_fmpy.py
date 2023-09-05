"""
FMU adapter and simulator for Mosaik implementation based on FMpy

Research group of Politecnico di Torino Energy Center Lab.

- author: Daniele Salvatore Schiera
- copyright: Copyright 2020. Energy Center Lab - Politecnico di Torino"
- credits: Daniele Salvatore Schiera
- maintainer: Daniele Salvatore Schiera
- email: daniele.schiera@polito.it
- status: Development

"""
import collections
import os, sys
from subprocess import Popen, PIPE  # replace os.system() and os.spawn*
import json
from pathlib import Path

import mosaik_api
from fmpy import dump, freeLibrary
from fmpy import read_model_description, extract
from fmpy.fmi1 import FMU1Slave
from fmpy.fmi2 import FMU2Slave


PROJECT_ROOT = str(Path(__file__).resolve().parents[2]).replace('\\', '/')
sys.path.append(PROJECT_ROOT)

from coesi.utilities.fmuchecker import fmu_checker as fmuchk
from coesi.definitions import MODELS_ROOT, TEMP_ROOT


# with open('./sim_config.json', 'r') as file:
#     META = json.load(file)['FMUs']

META = {
    'type': 'time-based',
    'models': {
    },
    'extra_methods': [
        'solver_call']
}


class FMU_Adapter(mosaik_api.Simulator):

    def __init__(self):
        super().__init__(META)
        self.eid_prefix = ''  # 'FMU_'
        self.entities = {}
        self.entity_vrs = collections.defaultdict(dict)
        self.sid = None

    def init(self, sid, time_resolution=1., work_dir=None, eid_prefix=None, start_time=0, stop_time=None, step_size=
    None, fmu_check=False, fmu_info=False, fmu_log=2, sim_meta=None, solver=None):
        # TODO general parameters for FMU to set the scenario for the simulator
        """Initialization of the simulator: preprocessed parameters for fmu instantiation and construct meta
        description for mosaik."""
        if float(time_resolution) != 1.:
            raise ValueError('ExampleSim only supports time_resolution=1., but'
                             ' %s was set.' % time_resolution)
        self.sid = sid
        if eid_prefix is not None:
            self.eid_prefix = eid_prefix

        if work_dir is None:
            self.work_dir = os.path.join(MODELS_ROOT, 'fmus')
        else:
            self.work_dir = work_dir  # working directory of fmu blocks

        self.fmu_check = fmu_check
        self.fmu_info = fmu_info
        self.fmu_log = fmu_log
        self.start_time = start_time
        self.stop_time = stop_time
        self.step_size = step_size
        self.fmu_time = self.start_time
        self.solver = solver

        if self.meta['models'] == {}:
            self.meta['models'] = sim_meta['models']

        return self.meta

    def create(self, num, model, extra_call=False, fmu_name=None, instance_name=None,
               start_vrs=None, start_in_vrs=None):

        next_eid = len(self.entities)
        entities = []

        if instance_name == None:
            instance_name = list(range(next_eid, next_eid + num))

        for i in range(len(instance_name)):
            eid = f'{model}_{instance_name[i]}'  # TODO: definire meglio il nome e i parametrei se
            # inizializzo piu entità del modello

            fmu_path = os.path.join(self.work_dir, f'{fmu_name}.fmu')
            # Check the xml of FMU
            if self.fmu_check:
                fmuchk.fmuchk_xml(fmu_path=fmu_path, log_level=6, summary=True)
            # Print the model information and variables of an FMU
            if self.fmu_info:
                dump(fmu_path)

            # Extract model description from xml
            model_description = read_model_description(fmu_path, validate=False)

            # Collect in a dictionaries all the model variables taken from the values reference vrs = {
            # 'variable_name' : value_ref}
            for var in model_description.modelVariables:
                self.entity_vrs[eid][var.name] = var.valueReference

            # Unzip the model in the temp working directory
            unzipdir = extract(fmu_path, unzipdir=os.path.join(TEMP_ROOT, f'{instance_name[i]}').replace('\\', '/'))

            fmiVersion = model_description.fmiVersion

            # Instantiation of the FMU
            if fmiVersion == '1.0':
                self.entities[eid] = FMU1Slave(guid=model_description.guid, unzipDirectory=unzipdir,
                                               modelIdentifier=model_description.coSimulation.modelIdentifier,
                                               instanceName=instance_name[i])
                self.entities[eid].instantiate()
            elif fmiVersion == '2.0':
                self.entities[eid] = FMU2Slave(guid=model_description.guid, unzipDirectory=unzipdir,
                                               modelIdentifier=model_description.coSimulation.modelIdentifier,
                                               instanceName=instance_name[i])
                self.entities[eid].instantiate(loggingOn=self.fmu_log)
                # self.entities[eid].setDebugLogging(loggingOn=True, categories=['logAll'])
            else:
                raise Exception('The FMU-CS version is not supported. Check the FMU version.')

            # Set all variables start values (start=) like fixed parameters

            if start_vrs:
                for var, value in start_vrs.items():
                    if isinstance(value, str):
                        self.entities[eid].setString([self.entity_vrs[eid][var]], [value])  # richiede liste
                    else:
                        self.entities[eid].setReal([self.entity_vrs[eid][var]], [value])

            self.entities[eid].setBoolean([self.entity_vrs[eid]['recOrSep']], [1])

            # Setup experiment: set the independent variable time
            if fmiVersion == '2.0':
                self.entities[eid].setupExperiment(startTime=self.start_time, stopTime=self.stop_time)

                # Initialization. Set the INPUT values at time = startTime and also variables with initial = exact
                self.entities[eid].enterInitializationMode()
                if start_in_vrs:
                    self.entities[eid].setReal([self.entity_vrs[eid][x] for x in start_in_vrs.keys()],
                                               list(start_in_vrs.values()))
                self.entities[eid].setBoolean([self.entity_vrs[eid]['recOrSep']], [1])
                status = self.entities[eid].exitInitializationMode()
                assert status == 0
            else:
                if start_in_vrs:
                    self.entities[eid].setReal([self.entity_vrs[eid][x] for x in start_in_vrs.keys()],
                                               list(start_in_vrs.values()))
                status = self.entities[eid].initialize(tStart=self.start_time, stopTime=self.stop_time)
                assert status == 0

            # Children: per comunicare
            # direttamente con il modello oppure eventualmente se sono presenti sotto-modelli (tipo caso Grid)
            entities.append({'eid': eid, 'type': model})  # , 'children':self.entities[eid]})

        return entities

    def solver_call(self, solver, num=1):
        # TODO: da migliorare
        if solver == 'matlab':
            print(f'Starting solver {solver} #{num}.')
            self.command = Popen(["C:\PROGRA~1\MATLAB\R2019b/toolbox\shared/fmu_share\script/fmu-matlab-setup"
                                  ".cmd", f'{num}'], stdin=PIPE, stdout=PIPE, stderr=PIPE)

            while self.command.stdout.readline().decode('utf-8').split('.')[0] != f'Launched MATLAB #{num}':
                pass

            print(f'Launched MATLAB #{num}')

    def step(self, time, inputs, max_advance):  # time it's current simualtion time
        """Stepping on the simulator during the co-simulation process"""

        target_time = time + self.start_time
        # Set inputs
        for dest_eid, attrs in inputs.items():
            for attr, values in attrs.items():
                new_attr_value = sum(values.values())  # todo: SUM VALUE INPUTS to ONE Attribute IMP TO parametrize
                self.entities[dest_eid].setReal([self.entity_vrs[dest_eid][attr]], [new_attr_value])

        if time != 0:
            for eid, fmu in self.entities.items():
                fmu.doStep(currentCommunicationPoint=self.fmu_time, communicationStepSize=target_time - self.fmu_time)

                print(fmu.getBoolean([self.entity_vrs[eid]['recOrSep']]))
        self.fmu_time += target_time - self.fmu_time

        return time + self.step_size

    def get_data(self, outputs):
        data = {}
        for eid, attrs in outputs.items():
            model = self.entities[eid]
            model_type = eid.split('_')[0]
            data[eid] = {}
            attrs = list(set(attrs))  # TODO per eliminare i doppioni problema Mosaik
            for attr in attrs:
                if attr not in self.meta['models'][model_type]['attrs']:
                    raise ValueError('Unknown output attribute: %s' % attr)
                data[eid][attr] = model.getReal([self.entity_vrs[eid][attr]])[0]
        return data

    def finalize(self):
        for eid, fmu in self.entities.items():
            fmu.terminate()
            # fmu.freeInstance() # TODO: se ho èpiù instanze richiede molto tempo (test con pyfmi)

        if self.solver:
            self.command.kill()


if __name__ == '__main__':
    mosaik_api.start_simulation(FMU_Adapter())
