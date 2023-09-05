import ntpath
import os
from pathlib import Path
from subprocess import Popen, PIPE
from fmpy import dump


def path_leaf(path):
    head, tail = ntpath.split(path)
    return tail or ntpath.basename(head)


def fmuchk_xml(fmu_path, log_level=3, test='cs', summary=True):
    """
    Checking of xml
    :param summary: Show summary results of check
    :param test: Test of xml or cs or me
    :param fmu_path: Path of FMU file
    :param log_level: Log level: 0 - no logging, 1 - fatal errors only, 2 - errors, 3 - warnings, 4 - info,
    5 - verbose, 6 - debug.
    """
    path = os.path.abspath(os.path.dirname(__file__))
    output_path = os.path.join(path,'OutputFMUChecker')
    Path(output_path).mkdir(parents=True,exist_ok=True)

    fmu_name = path_leaf(fmu_path).split('.')[0]
    checker = path + '/fmuCheck.win64.exe'
    p = Popen([checker,
               '-e', f'{output_path}/log_{fmu_name}.txt',
               '-o', f'{output_path}/result_{fmu_name}.csv',
               '-c', ',',
               '-l', f'{log_level}',
               '-s', '2',
               '-h', '1',
               '-k', f'{test}',
               '-f',
               fmu_path], stdin=PIPE, shell=True)

    p.communicate(input=b'\n')

    if summary:
        dump(fmu_path)
        with open(f'{output_path}\log_{fmu_name}.txt') as file:
            lines = file.readlines()
            count = 0
            k = 0
            mylines = []
            for line in lines:
                if 'FMU reported:' in line:
                    k = count
                count += 1
            print(f'FMU check of {fmu_name}.')
            for l in lines[k:]:
                print(l.strip())



if __name__ == '__main__':
    import sys
    from pathlib import Path

    PROJECT_ROOT = str(Path(__file__).resolve().parents[2]).replace('\\', '/')
    sys.path.insert(0, PROJECT_ROOT)
    from definitions import MODELS_ROOT

    print('FMU checker.')
    work_dir = os.path.join(MODELS_ROOT,'fmus')
    fmu_name = input("FMU name: \n")
    fmu_path = work_dir + f'/{fmu_name}.fmu'

    fmuchk_xml(fmu_path, log_level=6, summary=True)
    print('Finish')
