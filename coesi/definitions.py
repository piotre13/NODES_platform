import os
from pathlib import Path


pathroot = os.path.abspath(os.path.dirname(__file__))

PROJECT_ROOT = str(Path(__file__).resolve().parents[1]).replace('\\','/')
SCENARIO_ROOT = os.path.join(PROJECT_ROOT, 'scenarios').replace('\\','/')
UESA_ROOT = os.path.join(PROJECT_ROOT, 'coesi').replace('\\','/')
SIM_ROOT = os.path.join(UESA_ROOT, 'mk_sims').replace('\\','/')
MODELS_ROOT = os.path.join(PROJECT_ROOT, 'models').replace('\\','/')
OUTPUTS_ROOT = os.path.join(PROJECT_ROOT, 'Outputs').replace('\\','/')
TEMP_ROOT = os.path.join(PROJECT_ROOT, 'coesi/resources/temp').replace('\\','/')
RESOURCE_ROOT = os.path.join(PROJECT_ROOT, 'coesi/resources').replace('\\','/')

# Define matlab root exec
MATLABROOT = r"C:\Program Files\MATLAB\R2020a\toolbox\shared\fmu_share\script"
