import os
import re
import subprocess
from coesi.definitions import MODELS_ROOT

class Watershed:
    def __init__(self, _nameFile):
        self.nameFile = MODELS_ROOT + '/graps/inflow_files/' + _nameFile + '.dat'
        self.nameWatershed = _nameFile.split('_')[0]
        self.inflow = 0.0
    def step(self,_inflow):
        self.inflow = _inflow
        with open(self.nameFile, 'w') as file:
            file.write(str(self.inflow) + '\n')

class Reservoir:
    def __init__(self, _nameReservoir, _latitude, _longitude, _minElevation, _maxElevation, _maxStorage, _minStorage, _currentStorage, _alpha1, _beta1, _gamma1, _alpha2, _beta2, _numSpillways, _numOutlets, _restrictionLevels, _numChildren, _numParents, _targetStorage, _targetStorageRealibility, _evaporationDepth, _targetRestrictionProbability):
        self.nameReservoir = _nameReservoir
        self.timeStep = 0
        self.latitude = _latitude
        self.longitude = _longitude
        self.maxElevation = _minElevation
        self.minElevation = _maxElevation
        self.maxStorage = _maxStorage
        self.minStorage = _minStorage
        self.currentStorage = _currentStorage
        self.alpha1 = _alpha1
        self.beta1 = _beta1
        self.gamma1 = _gamma1
        self.alpha2 = _alpha2
        self.beta2 = _beta2
        self.numSpillways = _numSpillways
        self.numOutlets = _numOutlets
        self.restrictionLevels = _restrictionLevels
        self.numChildren = _numChildren
        self.numParents = _numParents
        self.targetStorage = _targetStorage
        self.targetStorageRealibility = _targetStorageRealibility
        self.evaporationDepth = _evaporationDepth
        self.targetRestrictionProbability = _targetRestrictionProbability

class User:
    def __init__(self, _nameUser, _demand, _UserId, _UserType, _numChildren, _numParents, _RestrictionLevels, _restrictionFraction, _restrictionCompensation, _nlags, _timeStepLength):
        self.nameUser = _nameUser
        self.timeStep = 0
        self.timeStepLength = _timeStepLength
        self.demand = _demand
        self.demandLength = len(self.demand)
        self.UserId = _UserId
        self.UserType = _UserType
        self.numChildren = _numChildren
        self.numParents = _numParents
        self.RestrictionLevels = _RestrictionLevels
        self.restrictionFraction = _restrictionFraction
        self.restrictionCompensation = _restrictionCompensation
        self.nlags = _nlags

class WaterReservoir:
    def __init__(self, _nameModel, input_names):
        self.nameModel = _nameModel
        self.timeStep = 0
        self.timeStepLength = 0
        self.listWatershed = {}
        self.listStorage = {}
        self.listReservoir = []
        self.listUser = []
        self.readInput()
        for input_name in input_names:
            self.listWatershed[input_name] = Watershed(input_name)
        self.readReservoirDetails()
        self.readUserDetails()
    def readInput(self):
        with open(MODELS_ROOT + '/graps/input_data_files/input.dat', 'r') as file:
            lines = file.readlines()

        self.timeStepLength = int(re.findall(r"[\w']+", lines[0].strip())[0])
        lines[0] = "1 1 1\n"

        with open(MODELS_ROOT + '/graps/input_data_files/input.dat', 'w') as file:
            file.writelines(lines)
    def readReservoirDetails(self):
        with open(MODELS_ROOT + '/graps/input_data_files/reservoir_details.dat', 'r') as file:
            index = 0
            line = file.readline()
            index = index + 1
            while line:
                nameReservoir = file.readline().strip()
                index = index + 1
                line = file.readline()
                line = re.findall(r"[\w']+", line.strip())
                latitude = int(line[0])
                longitude = int(line[1])
                index = index + 1
                line = file.readline()
                line = re.findall(r"(\d*(?:\.\d+)?)", line.strip())
                line = [float(x) for x in line if x != '']
                maxElevation = line[0]
                minElevation = line[1]
                index = index + 1
                line = file.readline()
                line = re.findall(r"(\d*(?:\.\d+)?)", line.strip())
                line = [float(x) for x in line if x != '']
                maxStorage = line[0]
                minStorage = line[1]
                currentStorage = line[2]
                index = index + 1
                line = file.readline()
                line = re.findall(r"(\d*(?:\.\d+)?)", line.strip())
                line = [float(x) for x in line if x != '']
                alpha1 = line[0]
                beta1 = line[1]
                gamma1 = line[2]
                index = index + 1
                line = file.readline()
                line = re.findall(r"[\w']+", line.strip())
                alpha2 = float(line[0] + '.' + line[1])
                beta2 = float(line[2] + '.' + line[3])
                index = index + 1
                line = file.readline()
                line = re.findall(r"[\w']+", line.strip())
                numSpillways = int(line[0])
                numOutlets = int(line[1])
                index = index + 1
                restrictionLevels = file.readline()
                restrictionLevels = re.findall(r"[\w']+", restrictionLevels.strip())
                index = index + 1
                line = file.readline()
                line = re.findall(r"[\w']+", line.strip())
                numChildren = int(line[0])
                numParents = int(line[1])
                for spill in range(numSpillways):
                    line = file.readline()
                    index = index + 1
                for outlet in range(numOutlets):
                    line = file.readline()
                    index = index + 1
                for children in range(numChildren):
                    line = file.readline()
                    index = index + 1
                for parents in range(numParents):
                    line = file.readline()
                    index = index + 1
                line = file.readline()
                line = re.findall(r"[\w']+", line.strip())
                targetStorage = float(line[0])
                targetStorageRealibility = float(line[1])
                index = index + 1
                line = file.readline()
                line = re.findall(r"[\w']+", line.strip())
                support = 0
                evaporationDepth = []
                for i in range(self.timeStepLength):
                    evaporationDepth.append(float(line[support] + '.' + line[support+1]))
                    support = support + 2
                index = index + 1
                targetRestrictionProbability = file.readline().strip()
                index = index + 1
                self.listReservoir.append(Reservoir(nameReservoir, latitude, longitude, minElevation, maxElevation, maxStorage, minStorage, currentStorage, alpha1, beta1, gamma1, alpha2, beta2, numSpillways, numOutlets, restrictionLevels, numChildren, numParents, targetStorage, targetStorageRealibility, evaporationDepth, targetRestrictionProbability))
                line = file.readline()
                index = index + 1
    def readUserDetails(self):
        with open(MODELS_ROOT + '/graps/input_data_files/decisionvar_details.dat', 'r') as other:
            with open(MODELS_ROOT + '/graps/input_data_files/user_details.dat', 'r') as file:
                index = 0
                line = file.readline()
                index = index + 1
                while line:
                    nameUser = file.readline().strip()
                    index = index + 1
                    line = file.readline()
                    line = re.findall(r"[\w']+", line.strip())
                    UserId = line[0]
                    UserType = line[1]
                    numChildren = int(line[2])
                    numParents = int(line[3])
                    RestrictionLevels = int(line[4])
                    index = index + 1
                    for child in range(numChildren):
                        line = file.readline()
                        index = index + 1

                    for parent in range(numParents):
                        line = file.readline()
                        index = index + 1

                    line = file.readline()
                    line = re.findall(r"[\w']+", line.strip())

                    restrictionFraction = file.readline()
                    restrictionFraction = re.findall(r"[\w']+", restrictionFraction.strip())

                    restrictionCompensation= file.readline()
                    restrictionCompensation = re.findall(r"[\w']+", restrictionCompensation.strip())

                    if UserType == 4 : ##User type = 4 --> HYDRO
                        line = file.readline()
                        index = index + 1
                        tailwaterElevation = file.readline()
                        tailwaterElevation = re.findall(r"[\w']+", tailwaterElevation.strip())

                    line = file.readline()
                    line = re.findall(r"[\w']+", line.strip())
                    nlags = int (line[0])

                    for  lag in range(nlags):
                        line = file.readline()
                        index = index + 1

                    demand = []
                    for i in range(self.timeStepLength):
                        demand.append(float(other.readline().strip()))
                    timeStepLength = len(demand)

                    self.listUser.append(User(nameUser, demand, UserId, UserType, numChildren, numParents, RestrictionLevels, restrictionFraction, restrictionCompensation, nlags,timeStepLength))
                    line = file.readline()
                    index = index + 1
                    line = file.readline()
                    index = index + 1

                    if not line.strip():
                        break
    def updateReservoirDetails(self):
        with open(MODELS_ROOT + '/graps/input_data_files/reservoir_details.dat', 'r') as file:
            lines = file.readlines()

            index = 0
            for reservoir in self.listReservoir:
                index = index + 7
                line = lines[index].strip()
                line = re.findall(r"[\w']+", line)
                numSpillways = int(line[0])
                numOutlets = int(line[1])
                index = index + 2
                line = lines[index].strip()
                line = re.findall(r"[\w']+", line)
                numChildren = int(line[0])
                numParents = int(line[1])
                for spill in range(numSpillways):
                    index = index + 1
                for outlet in range(numOutlets):
                    index = index + 1
                for children in range(numChildren):
                    index = index + 1
                for parents in range(numParents):
                    index = index + 1
                index = index + 2
                lines[index] = str(reservoir.evaporationDepth[reservoir.timeStep]) + '\n'
                reservoir.timeStep = reservoir.timeStep + 1
                index = index + 2

        with open(MODELS_ROOT + '/graps/input_data_files/reservoir_details.dat', 'w') as file:
            file.writelines(lines)
    def updateStorage(self):
        with open(MODELS_ROOT + '/graps/input_data_files/reservoir_details.dat', 'r') as file:
            lines = file.readlines()

        with open(MODELS_ROOT + '/graps/output_files/storage.out', 'r') as storage_file:
            storage_lines = storage_file.readlines()

        index = 1
        for reservoir in self.listReservoir:
            index = index + 3
            line = re.findall(r"(\d*(?:\.\d+)?)", lines[index].strip())
            line = [x for x in line if x != '']

            for storage_line in storage_lines:
                storage_data = storage_line.strip().split()

                if storage_data[0] == reservoir.nameReservoir:
                    reservoir.currentStorage = float(storage_data[1])
                    self.listStorage[storage_data[0]] = float(storage_data[1])


            # Aggiorna il valore di currentStorage nel file reservoir_details.dat
            lines[index] = line[0] + ' ' + line[1] + ' ' + str(reservoir.currentStorage) + '\n'

            index = index + 3
            line = re.findall(r"[\w']+", lines[index].strip())
            numSpillways = int(line[0])
            numOutlets = int(line[1])
            index = index + 2
            line = re.findall(r"[\w']+", lines[index].strip())
            numChildren = int(line[0])
            numParents = int(line[1])
            for spill in range(numSpillways):
                index = index + 1
            for outlet in range(numOutlets):
                index = index + 1
            for children in range(numChildren):
                index = index + 1
            for parents in range(numParents):
                index = index + 1
            index = index + 5

        with open(MODELS_ROOT + '/graps/input_data_files/reservoir_details.dat', 'w') as file:
            file.writelines(lines)

    def updateUserDetails(self):
        with open(MODELS_ROOT + '/graps/input_data_files/decisionvar_details.dat', 'w') as file:
            for user in self.listUser:
                file.write(str(user.demand[user.timeStep]) + '\n')
                user.timeStep = user.timeStep + 1

    def step(self):
        self.updateUserDetails()
        self.updateReservoirDetails()
        p = subprocess.Popen('multireservoir.exe', cwd = MODELS_ROOT + '/graps/', shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        exit_codes = p.wait()
        self.updateStorage()



