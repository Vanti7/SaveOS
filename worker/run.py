"""
Point d'entrée du worker SaveOS.

Séparé de worker/tasks.py à dessein : si tasks.py était lancé directement
via `python -m worker.tasks`, il serait chargé une première fois sous le
nom __main__, puis une seconde fois sous le nom worker.tasks quand RQ
résout par chemin de module le job à exécuter (rq.utils.import_attribute)
— ce qui exécute deux fois le code de niveau module, dont l'enregistrement
des métriques Prometheus (Counter/Histogram), non idempotent :
`ValueError: Duplicated timeseries in CollectorRegistry`.
"""
import os
import shutil

# RQ isole chaque job dans un processus enfant (os.fork() dans
# Worker.fork_work_horse) : un Counter/Histogram en mémoire simple ne
# verrait jamais les incréments faits par les enfants. Mode multiprocess
# de prometheus_client : chaque processus écrit dans des fichiers sous
# PROMETHEUS_MULTIPROC_DIR, agrégés à la lecture (voir start_worker()
# dans worker/tasks.py). Le dossier doit être vidé avant le premier
# import de prometheus_client.metrics (qui lit cette variable pour
# choisir sa classe de stockage), donc avant d'importer worker.tasks.
_multiproc_dir = os.environ.get('PROMETHEUS_MULTIPROC_DIR')
if _multiproc_dir:
    shutil.rmtree(_multiproc_dir, ignore_errors=True)
    os.makedirs(_multiproc_dir, exist_ok=True)

from worker.tasks import start_worker

if __name__ == '__main__':
    start_worker()
