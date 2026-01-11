# Ne pas importer les dataclasses de production/consumption ici
# Seul Django ORM doit être importé ici

from .production import SolarInstallation      # dataclass de calcul
from .consumption import ConsumptionProfile   # dataclass de calcul