from datetime import datetime
from time import perf_counter
import pytz

t = pytz.timezone("America/Bogota")

print(hasattr(t, 'fromutc'))




datetime.now()