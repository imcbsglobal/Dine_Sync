# sync.py
import pyodbc
import requests
import json
import logging
import sys
import os
from datetime import datetime
from decimal import Decimal

# ---------- HELPERS ----------
def decimal_to_float(obj):
    """JSON encoder helper: Decimal → float"""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError


class BaseSync:
    def __init__(self, cfg_key):
        self.config_key = cfg_key
        self.config = self.load_config()
        self.setup_logging()

    # ---------- CONFIG / LOG ----------
    def load_config(self):
        cfg_path = os.path.join(os.path.dirname(__file__), 'config.json')
        try:
            with open(cfg_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print("ERROR: config.json not found!")
            sys.exit(1)
        except json.JSONDecodeError:
            print("ERROR: Invalid JSON in config.json!")
            sys.exit(1)

    def setup_logging(self):
        level = getattr(logging, self.config['sync']['log_level'], logging.INFO)
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('sync.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(self.__class__.__name__)

    # ---------- DATABASE ----------
    def connect_to_database(self):
        try:
            db_cfg = self.config['database']
            conn_str = f"DSN={db_cfg['dsn']};UID={db_cfg['username']};PWD={db_cfg['password']}"
            self.logger.info(f"Connecting to DSN: {db_cfg['dsn']}")
            conn = pyodbc.connect(conn_str)
            self.logger.info("Database connection successful")
            return conn
        except pyodbc.Error as e:
            self.logger.error(f"Database connection failed: {e}")
            print(f"\nERROR: Could not connect to database. Check ODBC configuration.")
            print(f"DSN: {db_cfg['dsn']}\nError: {e}")
            return None

    # ---------- API ----------
    def api_post(self, endpoint, data):
        url = f"{self.config['api']['base_url']}{endpoint}"
        headers = {'Content-Type': 'application/json'}
        try:
            resp = requests.post(
                url,
                data=json.dumps(data, default=decimal_to_float),
                headers=headers,
                timeout=self.config['api']['timeout']
            )
            return resp.status_code == 200, resp.json() if resp.text else {}
        except requests.RequestException as e:
            return False, str(e)


# ---------- ACC_USERS ----------
class AccUsersSync(BaseSync):
    def __init__(self):
        super().__init__('sync')

    def fetch(self, conn):
        cursor = conn.cursor()
        cursor.execute("SELECT id, pass AS password FROM acc_users")
        rows = [
            {
                'id': row.id.strip() if row.id else '',
                'password': row.password.strip() if row.password else ''
            }
            for row in cursor
        ]
        cursor.close()
        self.logger.info(f"Fetched {len(rows)} acc_users records")
        return rows

    def run(self):
        conn = self.connect_to_database()
        if not conn:
            return False
        try:
            data = self.fetch(conn)
            if data is None:
                return False
            ok, _ = self.api_post(self.config['api']['endpoint'], data)
            if ok:
                self.logger.info("AccUsers sync completed")
            return ok
        finally:
            conn.close()


# ---------- ITEM MASTER ----------
class ItemsSync(BaseSync):
    def __init__(self):
        super().__init__('items_sync')

    def fetch(self, conn):
        fields = self.config['items_sync']['fields']
        sql = f"SELECT {', '.join(fields)} FROM tb_item_master"
        cursor = conn.cursor()
        cursor.execute(sql)
        rows = [dict(zip(fields, row)) for row in cursor]
        cursor.close()
        self.logger.info(f"Fetched {len(rows)} tb_item_master records")
        return rows

    def run(self):
        conn = self.connect_to_database()
        if not conn:
            return False
        try:
            data = self.fetch(conn)
            if data is None:
                return False
            ok, _ = self.api_post(self.config['api']['items_endpoint'], data)
            if ok:
                self.logger.info("Items sync completed")
            return ok
        finally:
            conn.close()


# ---------- MAIN ----------
def main():
    print("=== Starting Full Sync ===")
    ok1 = AccUsersSync().run()
    ok2 = ItemsSync().run()

    print("\n" + "=" * 50)
    if ok1 and ok2:
        print("All tables synced successfully!")
    else:
        print("One or more tables failed. Check sync.log")
    print("=" * 50)
    input("Press Enter to exit...")


if __name__ == "__main__":
    main()