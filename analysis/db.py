import importlib.util
import pathlib

_spec = importlib.util.spec_from_file_location(
    "_etl_db", pathlib.Path(__file__).resolve().parent.parent / "etl" / "db.py"
)
_etl_db = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_etl_db)

get_conn = _etl_db.get_conn
