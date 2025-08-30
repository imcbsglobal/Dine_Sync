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


# ---------- DINE BILLS ----------
class BillsSync(BaseSync):
    def __init__(self):
        super().__init__('bills_sync')

    def fetch(self, conn):
        fields = self.config['bills_sync']['fields']
        # Quote field names to handle reserved keywords like 'time' and 'user'
        quoted_fields = [f'"{field}"' for field in fields]
        
        # SQL query to get only last 7 days data
        sql = f"""SELECT {', '.join(quoted_fields)} 
                  FROM dine_bill 
                  WHERE "time" >= DATEADD(day, -7, GETDATE())
                  ORDER BY "time" DESC"""
        
        cursor = conn.cursor()
        cursor.execute(sql)
        
        rows = []
        for row in cursor:
            try:
                row_dict = dict(zip(fields, row))
                
                # Handle datetime conversion
                if row_dict.get('time'):
                    if hasattr(row_dict['time'], 'isoformat'):
                        row_dict['time'] = row_dict['time'].isoformat()
                    elif row_dict['time'] is not None:
                        # Convert to string if it's not None and doesn't have isoformat
                        row_dict['time'] = str(row_dict['time'])
                
                # Convert billno to string for JSON serialization
                if row_dict.get('billno') is not None:
                    row_dict['billno'] = str(int(float(row_dict['billno'])))
                
                # Handle user field - strip whitespace if it exists
                if row_dict.get('user'):
                    row_dict['user'] = str(row_dict['user']).strip()
                
                # Handle amount - ensure it's a proper decimal/float
                if row_dict.get('amount') is not None:
                    row_dict['amount'] = float(row_dict['amount'])
                
                rows.append(row_dict)
                
            except Exception as e:
                self.logger.error(f"Error processing row {row}: {str(e)}")
                continue
        
        cursor.close()
        self.logger.info(f"Fetched {len(rows)} dine_bill records from last 7 days")
        return rows

    def run(self):
        conn = self.connect_to_database()
        if not conn:
            return False
        try:
            data = self.fetch(conn)
            if data is None:
                return False
            
            # Log sample data for debugging
            if data:
                self.logger.info(f"Sample bill record: {data[0]}")
                self.logger.info(f"Date range: Last 7 days from today")
            else:
                self.logger.info("No bill records found in the last 7 days")
            
            ok, response = self.api_post(self.config['api']['bills_endpoint'], data)
            if ok:
                self.logger.info("Bills sync completed")
            else:
                self.logger.error(f"Bills sync failed. Response: {response}")
            return ok
        except Exception as e:
            self.logger.error(f"Bills sync error: {str(e)}")
            return False
        finally:
            conn.close()


# ---------- MAIN ----------
def main():
    print("=== Starting Full Sync ===")
    print("Syncing 3 tables: acc_users, tb_item_master, dine_bill")
    print()
    
    # Run all syncs
    sync_results = []
    
    print("1. Syncing acc_users...")
    ok1 = AccUsersSync().run()
    sync_results.append(("acc_users", ok1))
    
    print("2. Syncing tb_item_master...")
    ok2 = ItemsSync().run()
    sync_results.append(("tb_item_master", ok2))
    
    print("3. Syncing dine_bill...")
    ok3 = BillsSync().run()
    sync_results.append(("dine_bill", ok3))

    print("\n" + "=" * 60)
    print("SYNC RESULTS:")
    print("=" * 60)
    
    all_success = True
    for table_name, success in sync_results:
        status = "✓ SUCCESS" if success else "✗ FAILED"
        print(f"{table_name:20} - {status}")
        if not success:
            all_success = False
    
    print("=" * 60)
    if all_success:
        print("🎉 All tables synced successfully!")
    else:
        print("⚠️  One or more tables failed. Check sync.log for details")
    print("=" * 60)
    input("\nPress Enter to exit...")


if __name__ == "__main__":
    main()