class Watershed:
    def __init__(self, _nameFile):
        self.latitude = 0.0
        self.longitude = 0.0
        self.elevationMin = 0.0
        self.elevationMax = 0.0
        self.storageMin = 0.0
        self.storageMax = 0.0
        self.storageElevationAreaParameter = 0.0
        self.targetStorage = 0.0
        self.storageProbability = 0.0
        self.targetRestrictionLevelsProbability = 0.0
        self.spillawayTypes = 0.0
        self.spillawayCrestLevel = 0.0
        self.spillawayMaxDischarge = 0.0
        self.spillawayNumber = 0
        self.outletsElevation = 0.0
        self.outletsCrossSectionArea = 0.0
        self.outletsMaxLossCoefficient = 0.0
        self.outletsMinLossCoefficient = 0.0
        self.currentStorage = 0.0

        self.wathershed = {}
        self.users = {}

