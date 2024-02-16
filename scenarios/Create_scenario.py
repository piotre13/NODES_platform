
import os
from utils.Utils import read_yaml_file,write_yaml_file
import geopandas as gpd
import re
from copy import deepcopy
class Scenario_Yaml():
	def __init__(self, name, scen_conf):
		self.scenario_name = name
		self.scenario = read_yaml_file("templates/empty_scenario.yaml")
		self.fids = {'fids':[]}
		self.set_scen_config(scen_conf)

	def set_scen_config(self, conf):
		self.scenario['SCEN_CONFIG'] = conf
	def add_new_eid_list (self,eid_type):
		key = eid_type+'_fids'
		if key not in self.fids.keys():
			self.fids[key]=[]
		else:
			print('eid typology already present')
	def add_connection (self,FROM, TO, attrs, type = 'classic', **params):
		templ = self.get_template('connection')
		templ['ATTRS'] = attrs
		templ['FROM'] = FROM
		templ['TO'] = TO
		if type == 'classic':
			del templ['PARAMS']
		elif type == 'time_shifted':
			templ['PARAMS'] = params
		if len(self.scenario['CONNECTIONS']) == 0:
			self.scenario['CONNECTIONS']['0'] = templ
		else:
			n_connections = sorted(self.scenario['CONNECTIONS'].keys(), key=lambda x: int(x))
			i = str(int(n_connections[-1]) +1)
			self.scenario['CONNECTIONS'][i] = templ

	def get_template(self,typology):
		if typology == 'fmu':
			return read_yaml_file('templates/pyfmi.yaml')
		elif typology == 'heating_sys':
			return read_yaml_file('templates/heating_sys.yaml')
		elif typology == 'scheduler':
			return read_yaml_file('templates/scheduler.yaml')
		elif typology == 'timeseries':
			return read_yaml_file('templates/timeseries.yaml')
		elif typology == 'connection':
			return read_yaml_file('templates/connection.yaml')
		else:
			print('template not recognized')
	def make_eid(self, model_name, mod_num, ch_id=None ):
		if ch_id is None:
			return model_name+'_'+str(mod_num)
		else:
			return model_name+'_'+str(mod_num)+'.'+str(ch_id)
	def make_fullid(self,sim_id,eid):
		return sim_id+'.'+eid

class AutoScenario_basicNODES(Scenario_Yaml):
	'''this scenario making works as follows:
	- create a sim for each of the buildings FMUs --- Eplus FMUS of a specific type
	- create a sim for each HVAC system for each building, same type for all but with different sizings
	- create a single scheduler for Zone set-point
	- create a timeseries for the weather file
	- create a timeseries for each type of schedule we want to connect to each building
	- a DB collecting everything
	CONNECTIONS:
	- each building is timeshifted connected with hvac
	- each hvac receives t_ext from timeseries weather
	- each building receives zone set point by scheduler
	- every sim sends all its attrs to the DB'''
	def __init__(self, name, scen_conf ,fmus_dir, gdf_file, meteo_file,schedule_file):
		Scenario_Yaml.__init__(self,name, scen_conf)
		self.gdf = gpd.read_file(gdf_file)
		self.fmus_dir = fmus_dir
		self.meteo_file = meteo_file
		self.schedule_file = schedule_file

	def save_scenario(self):
		path = self.scenario_name+'.yaml'
		write_yaml_file(path,self.scenario)
	def add_sims(self, **params):
		self.add_fmus(**params)
		self.add_hvac(**params)
		self.add_weather(**params)
		self.add_scheduler(**params)
		self.add_schedules(**params)

	def add_collector (self): # tODO should be moved inside mother class
		self.scenario['SCEN_OUTPUTS']['DB']['step_size'] = 600
		for sid, val in self.scenario['SIM_CONFIG'].items():
			if sid.startswith('p') or sid.startswith('h') or sid.startswith('w'):
				for mid, val in val['MODELS'].items():
					if val['PARAMS']['num'] == 1:
						for attr in val['ATTRS']:
							if attr in ['TBuilding','HeatingLoadTarget','Qt','fuel','En_auxel', 'DryBulb']:
								full_attr = sid +'.'+mid+'_0.'+attr
								self.scenario['SCEN_OUTPUTS']['DB']['attrs'].append(full_attr)
					else:
						for j in range(val['PARAMS']['num']):
							for attr in val['ATTRS']:
								full_attr = sid + '.' + mid + '_'+j+'.' + attr
								self.scenario['SCEN_OUTPUTS']['DB']['attrs'].append(full_attr)

	def connections(self):
		# connect weather and hvacs (one_tomany)
		fro = self.fids['weather_fids'][0]
		to = self.fids ['hvac_fids']
		attrs = [['DryBulb','Text']]
		self.add_connection(fro, to, attrs)

		# connect scheduler and buildings (one_tomany)
		fro = self.fids['scheduler_fids'][0]
		to = [fid for fid in self.fids['buildings_fids']]
		attrs = [['Tset','ZoneSetPoint']]
		self.add_connection(fro,to,attrs)
		# connect schedules and buildings
		i=0
		for fid in self.fids['occupancy_fids']:
			fro = fid
			to = self.fids ['buildings_fids'][i]
			attrs = [['P','EEquipWatt']]
			self.add_connection(fro, to, attrs)
			attrs = [['Pres','PeopleNumber']]
			self.add_connection(fro, to, attrs)

			i+=1
		# connect hvac and buildings
		j=0
		for fid in self.fids['hvac_fids']:
			fro = self.fids['buildings_fids'][j]
			to = fid
			attrs = [['HeatingLoadTarget','Qt']]
			par = {'initial_data': {attrs[0][0]: 0.0}, 'time_shifted': True}
			self.add_connection(fro,to,attrs, type='time_shifted', **par)
			attrs = [['Qt','OthEquRadWatt']]
			#par = { 'initial_data':{attrs[0][0]: 0.0}, 'time_shifted':True}
			#self.add_connection(to, fro, attrs,type='time_shifted', **par)
			self.add_connection(to,fro,attrs)
			j+=1
		pass


	def add_fmus(self,**params):
		self.add_new_eid_list('buildings')
		i = 0
		for fmu in os.listdir(self.fmus_dir):
			if i == 400:
				print('More than 400 EPLUS FMUs Instances : ENERGYPLUS WILL NOT BE ABLE TO HANDLE ALL THESE INSTANCES')

			if fmu.endswith('.fmu'):

				templ = self.get_template('fmu')
				mod_id = fmu.split('.')[0]
				sid = 'pyfmi%s'%i
				templ[sid] = templ.pop('fmu_pyfmi_sim0')
				templ[sid]['MODELS'][mod_id] = templ[sid]['MODELS'].pop('rc')
				templ[sid]['MODELS'][mod_id]['PARAMS']['fmu_name'] = fmu.split('.')[0]
				if len(params)>0 and 'fmu' in params.keys():
					templ[sid]['PARAMS'] = deepcopy(params['fmu']['PARAMS'])
				eid = self.make_eid(mod_id,0)
				full_id = self.make_fullid(sid, eid)
				self.fids['fids'].append(full_id)
				self.fids['buildings_fids'].append(full_id)
				self.scenario['SIM_CONFIG'][sid]=templ[sid]

			i += 1
		self.fids['fids'].sort(key=lambda x: int(list(re.findall(r'\d+', x.split('_')[-2]))[0]))
		self.fids['buildings_fids'].sort(key=lambda x: int(list(re.findall(r'\d+', x.split('_')[-2]))[0]))
	def add_hvac(self, **params):
		EPC_rating = {'high': 'A3', 'med': 'B', 'low': 'F'}
		self.add_new_eid_list('hvac')
		for i in range(len(self.fids['buildings_fids'])):
			templ = self.get_template('heating_sys')
			sid = 'heating%s'%i
			mod_id = 'hs'
			templ[sid] = templ.pop('heating_system')
			templ[sid]['MODELS'][mod_id] = templ[sid]['MODELS'].pop('hs')
			if len(params)>0 and 'hvac' in params.keys():
				templ[sid]['PARAMS'] = params['hvac']['PARAMS']
				templ[sid]['MODELS'][mod_id]['PARAMS'] = deepcopy(params['hvac']['mod_params'])
				bui_id = self.fids['buildings_fids'][i].split('_')[0].split('.')[1]
				templ[sid]['MODELS'][mod_id]['PARAMS']['leased_area'] = float(self.gdf.loc[self.gdf['b_id']== bui_id]['net_leased_area'].iloc[0])
				templ[sid]['MODELS'][mod_id]['PARAMS']['EPC_rating'] = EPC_rating[params['hvac']['mod_params']['EPC_rating']]

			eid = self.make_eid(mod_id, 0)
			full_id = self.make_fullid(sid, eid)
			self.fids['fids'].append(full_id)
			self.fids['hvac_fids'].append(full_id)
			self.scenario['SIM_CONFIG'][sid] = templ[sid]

	def add_weather(self, **params):
		#TODO better generalization for now is quite hardcoded
		self.add_new_eid_list('weather')
		templ = self.get_template('timeseries')
		sid = 'weather'
		mod_id = 'ts'
		templ[sid] = templ.pop('timeseries')
		if len(params)>0 and 'weather' in params.keys():
			templ[sid]['PARAMS'] = params['weather']['PARAMS']
			templ[sid]['MODELS'][mod_id]['PARAMS'] = deepcopy(params['weather']['mod_params'])
		eid = self.make_eid(mod_id, 0)
		full_id = self.make_fullid(sid, eid)
		self.fids['fids'].append(full_id)
		self.fids['weather_fids'].append(full_id)
		self.scenario['SIM_CONFIG'][sid] = templ[sid]
	def add_scheduler(self,**params):
		self.add_new_eid_list('scheduler')
		templ = self.get_template('scheduler')
		sid = 'scheduler'
		mod_id = 'schedule'
		if len(params)>0 and 'scheduler' in params.keys():
			templ[sid]['MODELS'][mod_id]['PARAMS'] = deepcopy(params['scheduler']['mod_params'])
		eid = self.make_eid(mod_id, 0)
		full_id = self.make_fullid(sid, eid)
		self.fids['fids'].append(full_id)
		self.fids['scheduler_fids'].append(full_id)
		self.scenario['SIM_CONFIG'][sid] = templ[sid]
	def add_schedules(self,**params):
		self.add_new_eid_list('occupancy')
		for i in range(len(self.fids['buildings_fids'])):
			sid = 'occupancy%s'%i
			mod_id = 'occ'
			templ = self.get_template('timeseries')
			templ[sid] = templ.pop('timeseries')
			templ[sid]['MODELS'][mod_id] = templ[sid]['MODELS'].pop('ts')
			if len(params)>0 and 'occupancy' in params.keys():
				templ[sid]['MODELS'][mod_id]['PARAMS'] = deepcopy(params['occupancy']['mod_params'])
				templ[sid]['MODELS'][mod_id]['ATTRS'] = params['occupancy']['mod_attrs']
				templ[sid]['PARAMS']=params['occupancy']['PARAMS']
				bui_id = self.fids['buildings_fids'][i].split('_')[0].split('.')[1]
				mul = int(self.gdf.loc[self.gdf['b_id']== bui_id]['n_fam'].iloc[0])
				templ[sid]['PARAMS']['conv_dict']['P'] = '%s:0'%mul
				templ[sid]['PARAMS']['conv_dict']['Pres'] = '%s:0'%mul
				eid = self.make_eid(mod_id, 0)
				full_id = self.make_fullid(sid, eid)
				self.fids['fids'].append(full_id)
				self.fids['occupancy_fids'].append(full_id)
				self.scenario['SIM_CONFIG'][sid] = templ[sid]




if __name__ == '__main__':
	fmu_dir = '../models/fmus/frassinetto_debug'
	gdf = '../data/geometric/outcomes/frassinetto_test_high.geojson'
	meteo_file = '../data/meteo_file/meteo_bousson.csv'
	schedule_file = '../data/occupancy/famiglia.csv'
# TODO add attrs to conf files
	scen_conf = {'DAYS': 15,
				 'RT_FACTOR': None,
				 'SCENARIO_NAME': 'test_scenario',
				 'START_DATE': '2021-01-01 01:00:00'}

	fmusim_conf = {'PARAMS':{'fmu_log': 0, 'step_size': 600, 'stop_time': 31536000, 'work_dir': fmu_dir.split('/')[-1]}}
	hvacsim_conf = {'PARAMS':{'step_size':600}, 'mod_params':{'EPC_rating':'high', 'leased_area':0,'num':1,'type':'gb'}}
	weather_conf = {'PARAMS':{'conv_dict': {'DewPoint': '1:273.15', 'DryBulb': '1:273.15', 'OpaqSkyCvr': '0.1:0', 'TotSkyCvr': '0.1:0', 'WindDir': '3.14159265359/180.0:0'},
							  'datafile': 'meteo_file/meteo_frassinetto.csv', 'start_date': 'START_DATE', 'stepsize': 600, 'stop_date': '2021-01-30 00:00:00'},'mod_params':{'num':1}}
	scheduler_conf = {'mod_params':{'schedule':['0:21'], 'num':1}}
	occupancy_conf = {'PARAMS':{'conv_dict': {'P': '1:0', 'Pres': '1:0'},
							  'datafile': 'occupancy/famiglia.csv', 'start_date': 'START_DATE', 'stepsize': 600, 'stop_date': '2021-01-30 00:00:00'}, 'mod_params':{'num':1}, 'mod_attrs':['P', 'Pres']}
	params= { 'fmu' : fmusim_conf, 'hvac':hvacsim_conf, 'weather':weather_conf, 'scheduler':scheduler_conf, 'occupancy':occupancy_conf}

	scen = AutoScenario_basicNODES(scen_conf['SCENARIO_NAME'],scen_conf,fmu_dir,gdf,meteo_file,schedule_file)
	scen.add_sims(**params)
	scen.connections()
	scen.add_collector()
	scen.save_scenario()

