import os
import subprocess
def Eplus2FMU_single(config):
    cmd = 'python '+ config['path_conv']+ ' -d -i '+ config['idd_file']+ ' -w '+config['weather'] + ' -a '+ config['FMI_v']+ ' ' + config['idf_file']
    print(cmd)
    res = os.system('which python')
    res = os.system('python --version')

    subprocess.call(['python', config['path_conv'], '-i', config['idd_file'], "-w", config['weather'], "-a", "2.0", "-d", config['idf_file']])

    #TODO need to use subprocess but it return an error on the syntax of the idd file?????




    # cmd = []
    # cmd.append("python")
    # #cmd.append('-d')
    # cmd.append("-i")
    # cmd.append(config['idd_file'])
    # cmd.append("-w")
    # cmd.append(config['weather'])
    # cmd.append("-a")
    # cmd.append(config['FMI_v'])
    # cmd.append(config['idf_file'])
    # print(subprocess.list2cmdline(cmd))
    # subprocess.run(cmd)
    # print('converted')



'''python  <path-to-scripts-subdir>EnergyPlusToFMU.py  -i <path-to-idd-file>  \
  -w <path-to-weather-file> -a <fmi-version> <path-to-idf-file>'''



if __name__ == '__main__':
    config ={
        "idf_file": "../data/idf/frassinetto_casestudy_high/SF_high_27.idf",
        "idd_file": "/usr/local/EnergyPlus-23-1-0/Energy+.idd",
        "weather": "/home/pietrorm/Documents/CODE/NODES_platform/data/meteo_file/meteo_bousson.epw",
        "FMI_v": "2.0",
        "path_conv": "/usr/local/EnergyPlus-23-1-0/energyplusToFMU/Scripts/EnergyPlusToFMU.py"
    }
    Eplus2FMU_single(config)