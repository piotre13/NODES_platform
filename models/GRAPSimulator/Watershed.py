class Watershed:
    def __init__(self, _nameFile):
        self.nameFile = MODELS_ROOT + '/graps/inflow_files/' + _nameFile + '.dat'
        self.nameWatershed = _nameFile.split('_')[0]
        self.inflow = 0.0
        self.drainageArea = 0.0
    def step(self,_inflow):
        self.inflow = _inflow
        with open(self.nameFile, 'w') as file:
            file.write(str(self.inflow) + '\n')