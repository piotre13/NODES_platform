class User:
    def __init__(self, _nameUser, _demand, _UserId, _UserType, _numChildren, _numParents, _RestrictionLevels, _restrictionFraction, _restrictionCompensation, _nlags, _timeStepLength):
        self.type = 0
        self.minimumRelease = 0.0
        self.maximumRelease = 0.0
        self.tariff = 0.0
        self.penalityVolume = 0.0
        self.reliability = 0.0
        self.contractRestrictionVolume = 0.0
        self.penalityCompensation = 0.0
        self.restrictionCompensation = 0.0
        self.restrictionFraction = 0.0

        #input
        self.demand = 0.0

        #output
        self.release = 0.0