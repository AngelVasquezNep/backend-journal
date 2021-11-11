class VotingBooth:

    def __init__(self, identifier, country):
        self._identifier = identifier
        self._country = country
        self._region = None

    @property
    def region(self):
        return self._region

    @region.setter
    def region(self, region):
        if region in self._country:
            self._region = region
        else:
            raise ValueError(f'Region {region} is not allowed')


booth = VotingBooth(123, ['Mexico', 'Morelos'])
print(booth.region)
booth.region = 'Mexico'
print(booth.region)
