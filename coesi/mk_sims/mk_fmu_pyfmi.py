"""
FMU adapter and simulator for Mosaik implementation based on pyFMI.

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
from memory_profiler import profile
from pathlib import Path

import mosaik_api_v3 as mosaik_api
from fmpy import dump
from pyfmi import load_fmu


PROJECT_ROOT = str(Path(__file__).resolve().parents[2]).replace('\\', '/')
sys.path.append(PROJECT_ROOT)
from coesi.utilities.fmuchecker import fmu_checker as fmuchk
from coesi.definitions import MODELS_ROOT, MATLABROOT


#
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
        self.sid = None

    def init(self, sid, time_resolution=1., work_dir=None, eid_prefix=None, start_time=0, stop_time=0, step_size=
    None, fmu_check=False, fmu_info=False, fmu_log=2, sim_meta=None, solver=None):  # pyfmi require 0.0 as stop
        # time by
        # default
        # TODO general parameters for FMU to set the scenario for the simulator
        """Initialization of the simulator: preprocessed parameters for fmu instantiation and construct meta
        description for mosaik."""
        # if float(time_resolution) != 1.:
        #     raise ValueError('ExampleSim only supports time_resolution=1., but'
        #                      ' %s was set.' % time_resolution)
        #self.time_resolution = time_resolution
        self.time_resolution = time_resolution
        #print(self.time_resolution)
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
        elif num > 1:
            assert len(instance_name) == 1
            instance_name = [instance_name[0]+f'_{x}'for x in range(next_eid, next_eid + num)]
        for i in range(len(instance_name)):
            eid = f'{model}_{instance_name[i]}'

            fmu_path = os.path.join(self.work_dir, f'{fmu_name}.fmu')
            # Check the xml of FMU
            if self.fmu_check:
                fmuchk.fmuchk_xml(fmu_path=fmu_path, log_level=6, summary=True)
            # Print the model information and variables of an FMU
            # if self.fmu_info:
            #     dump(fmu_path)

            # Instantiation of the FMU

            self.entities[eid] = load_fmu(fmu_path, log_level=self.fmu_log)
            model_description = self.entities[eid].get_description()  # TODO verificare
            fmiVersion = self.entities[eid].get_version()

            if fmiVersion == '2.0':
                self.entities[eid].instantiate(name=instance_name[i]) # Todo: load_fmu e instantiate crea due
                # instanze ?? ma è l'unico modo per creare i files con il nome _instance_name
            else:
                self.entities[eid].instantiate_slave(name=instance_name[i])

            # Set all variables start values (start=) like fixed parameters
            if start_vrs:
                self.entities[eid].set(list(start_vrs.keys()), list(start_vrs.values()))

            # Setup experiment: set the independent variable time

            if fmiVersion == '2.0':
                self.entities[eid].setup_experiment(start_time=self.start_time*self.time_resolution, stop_time=self.stop_time*self.time_resolution)

                # Initialization. Set the INPUT values at time = startTime and also variables with initial = exact
                self.entities[eid].enter_initialization_mode()
                if start_in_vrs:
                    self.entities[eid].set(list(start_in_vrs.keys()), list(start_in_vrs.values()))
                self.entities[eid].exit_initialization_mode()
            else:
                if start_in_vrs:
                    self.entities[eid].set(list(start_in_vrs.keys()), list(start_in_vrs.values()))
                self.entities[eid].initialize(start_time=self.start_time*self.time_resolution, stop_time=self.stop_time*self.time_resolution)

            # Children: per comunicare
            # direttamente con il modello oppure eventualmente se sono presenti sotto-modelli (tipo caso Grid)
            entities.append({'eid': eid, 'type': model})  # , 'children':self.entities[eid]})

        return entities

    def solver_call(self, solver, num=1):
        if solver == 'matlab':
            print(f'Starting solver {solver} #{num}.')
            self.command = Popen([MATLABROOT+"/fmu-matlab-setup.cmd", f'{num}'], stdin=PIPE, stdout=PIPE, stderr=PIPE)

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
                self.entities[dest_eid].set(attr, new_attr_value)

        if time != 0:
            for eid, fmu in self.entities.items():
                fmu.do_step(current_t=self.fmu_time*self.time_resolution, step_size=(target_time - self.fmu_time)*self.time_resolution,
                            new_step=True)
                # print('\n')
                # print(fmu.get('recOrSep'))
                # print(fmu.get('h_heater'))
                # print(fmu.get('heaterCooler.h_heater'))
                # print(fmu.get('heaterCooler.pITempHeat.h'))
                # print(fmu.get('heaterCooler.pITempHeat.PI.yMax'))
                # print(fmu.get('heaterCooler.pITempHeat.PI.yMin'))
                # print(fmu.get('heaterCooler.pITempHeat.rangeSwitch'))
                # print(fmu.get('heaterCooler.pITempHeat.PI.y'))
                # print(fmu.get('heaterCooler.heatingPower'))


        self.fmu_time += target_time - self.fmu_time

        return time + self.step_size  # mosaik requires int step size and time

    def get_data(self, outputs):
        data = {}
        for eid, attrs in outputs.items():
            model = self.entities[eid]
            model_type = eid.split('_')[0]
            data[eid] = {}
            attrs = list(set(attrs))  # TODO per eliminare i doppioni, sembra un problema Mosaik. da risolvere
            for attr in attrs:
                if attr not in self.meta['models'][model_type]['attrs']:
                    raise ValueError('Unknown output attribute: %s' % attr)
                data[eid][attr] = model.get(attr).item()
        return data

    def finalize(self):
        for eid, fmu in self.entities.items():
            fmu.terminate()
            # fmu.free_instance() # TODO: se ho più instanze richiede molto tempo (test con pyfmi)
            # print(fmu.print_log())
        if self.solver:
            # self.command.stdin.write('stop\n'.encode())
            self.command.terminate()
            # Popen("TASKKILL /F /PID {pid} /T".format(pid=self.command.pid))


def main():
    return mosaik_api.start_simulation(FMU_Adapter())


if __name__ == '__main__':
    main()
