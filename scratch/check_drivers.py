import fastf1
from fastf1.ergast import Ergast

ergast = Ergast()
drivers = ergast.get_driver_info(season='current')
print(drivers.columns)
print(drivers.head())
