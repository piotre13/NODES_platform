""" Executable for converting an Energy Plus model to a FMU using the EnergyPlusToFMU module using EnergyPlustoFMUI
author: Daniele Salvatore Schiera"""
from definitions import pathroot, MODELS_ROOT
from os.path import isfile
import subprocess
import shutil
import os

def ep2fmu(model_name,save_dir= os.path.dirname(os.path.abspath( __file__ ))):
	idd = "C:\EnergyPlusV9-2-0\Energy+.idd"
	if not isfile(idd):
		raise("The Energy+.idd in the specified directory does not exist. Change the directory.")

	idf = pathroot + f"/resources/eplus_data/{model_name}.idf"
	#wth = pathroot + "/resources/weather_data/my_epw_file.epw"
	wth = pathroot +r"\resources\weather_data\USA_CA_San.Francisco.Intl.AP.724940_TMY3.epw"
	EnergyPlusToFMU = pathroot + '/utilities/ep2fmu\Scripts\EnergyPlusToFMU.py'
	try:
		# To run EnergyPlustToFMU it must be used python 2.7
		#envpy27 = 'C:/Users/Daniele Schiera/Anaconda3/envs/EP2FMU/python.exe'
		#subprocess.call([envpy27, EnergyPlusToFMU, '-i', idd, "-w", wth, idf])
		# subprocess.call(['python', EnergyPlusToFMU, '-i', idd, "-w", wth, "-a","2.0", idf]) -a for FMI version
		subprocess.call(['python', EnergyPlusToFMU, '-i', idd, "-w", wth,"-a","2.0", idf])
	except:
		raise('To run EnergyPlusToFMU we must use environment python 2.7')

	#shutil.move(save_dir + f"/{model_name}.fmu", MODELS_ROOT + f"/fmus/{model_name}.fmu")
	return print(f'Finished.')# The file {model_name}.fmu is located in models/fmus')

def main():
	model_name = input('Model name: ')  # 'OneZoneUncontrolled_win_2'
	ep2fmu(model_name)

if __name__ == '__main__':
	main()

