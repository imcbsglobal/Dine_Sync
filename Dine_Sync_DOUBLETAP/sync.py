# sync.py - Complete Database Sync Tool with Terminal Display
import pyodbc
import requests
import json
import logging
import sys
import os
from datetime import datetime
from decimal import Decimal
import time

# ---------- HELPERS ----------
def decimal_to_float(obj):
    """JSON encoder helper: Decimal → float"""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

def print_header():
    """Print a nice header for the sync process"""
    print("=" * 70)
    print("DATABASE SYNC TOOL")
    print("=" * 70)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print()

def print_status(message, status="INFO"):
    """Print status messages with timestamps"""
    timestamp = datetime.now().strftime('%H:%M:%S')
    if status == "SUCCESS":
        print(f"[{timestamp}] SUCCESS: {message}")
    elif status == "ERROR":
        print(f"[{timestamp}] ERROR: {message}")
    elif status == "PROGRESS":
        print(f"[{timestamp}] PROGRESS: {message}")
    else:
        print(f"[{timestamp}] INFO: {message}")
    
    # Force flush to ensure immediate display
    sys.stdout.flush()

def print_summary(results):
    """Print final summary"""
    print("\n" + "=" * 70)
    print("SYNC RESULTS SUMMARY")
    print("=" * 70)
    
    success_count = sum(1 for _, success in results if success)
    total_count = len(results)
    
    for table_name, success in results:
        status = "SUCCESS" if success else "FAILED"
        print(f"{table_name:35} - {status}")
    
    print("=" * 70)
    print(f"Summary: {success_count}/{total_count} tables synced successfully")
    
    if success_count == total_count:
        print("All synchronizations completed successfully!")
    else:
        print("One or more synchronizations failed. Check sync.log for details.")
    
    print("=" * 70)


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
            print_status("config.json not found!", "ERROR")
            sys.exit(1)
        except json.JSONDecodeError:
            print_status("Invalid JSON in config.json!", "ERROR")
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
            print_status(f"Connecting to DSN: {db_cfg['dsn']}", "PROGRESS")
            conn = pyodbc.connect(conn_str)
            print_status("Database connection successful", "SUCCESS")
            return conn
        except pyodbc.Error as e:
            print_status(f"Database connection failed: {e}", "ERROR")
            print(f"\nERROR: Could not connect to database. Check ODBC configuration.")
            print(f"DSN: {db_cfg['dsn']}\nError: {e}")
            return None

    # ---------- API ----------
    def api_post(self, endpoint, data, timeout=None):
        url = f"{self.config['api']['base_url']}{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        # Use custom timeout if provided, otherwise use config timeout
        request_timeout = timeout or self.config['api']['timeout']
        
        try:
            resp = requests.post(
                url,
                data=json.dumps(data, default=decimal_to_float),
                headers=headers,
                timeout=request_timeout
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
        print_status(f"Fetched {len(rows)} user records", "SUCCESS")
        return rows

    def run(self):
        print_status("Starting User Accounts sync...", "PROGRESS")
        conn = self.connect_to_database()
        if not conn:
            return False
        try:
            data = self.fetch(conn)
            if data is None:
                return False
            
            print_status(f"Sending {len(data)} user records to API...", "PROGRESS")
            ok, _ = self.api_post(self.config['api']['endpoint'], data)
            if ok:
                self.logger.info("AccUsers sync completed")
                print_status("User Accounts sync completed", "SUCCESS")
            else:
                print_status("User Accounts sync failed", "ERROR")
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
        print_status(f"Fetched {len(rows)} item records", "SUCCESS")
        return rows

    def run(self):
        print_status("Starting Items sync...", "PROGRESS")
        conn = self.connect_to_database()
        if not conn:
            return False
        try:
            data = self.fetch(conn)
            if data is None:
                return False
            
            # Process in batches with longer timeout to avoid timeout
            batch_size = 1000
            total_records = len(data)
            
            if total_records == 0:
                self.logger.info("No items to sync")
                print_status("No items to sync", "INFO")
                return True
            
            self.logger.info(f"Processing {total_records} records in batches of {batch_size}")
            print_status(f"Processing {total_records} records in batches of {batch_size}", "PROGRESS")
            
            for i in range(0, total_records, batch_size):
                batch = data[i:i + batch_size]
                batch_num = (i // batch_size) + 1
                total_batches = (total_records + batch_size - 1) // batch_size
                
                self.logger.info(f"Sending batch {batch_num}/{total_batches} ({len(batch)} records)")
                print_status(f"Sending batch {batch_num}/{total_batches} ({len(batch)} records)", "PROGRESS")
                
                # Use longer timeout for items (2 minutes)
                ok, response = self.api_post(self.config['api']['items_endpoint'], batch, timeout=120)
                if not ok:
                    self.logger.error(f"Batch {batch_num} failed. Response: {response}")
                    print_status(f"Batch {batch_num} failed: {response}", "ERROR")
                    return False
                
                # Add small delay between batches to prevent overwhelming the server
                if batch_num < total_batches:
                    time.sleep(0.5)
                    
            self.logger.info("Items sync completed")
            print_status("Items sync completed", "SUCCESS")
            return True
        finally:
            conn.close()


# ---------- DINE BILLS (7 days only) ----------
class BillsSync(BaseSync):
    def __init__(self):
        super().__init__('bills_sync')

    def fetch(self, conn):
        fields = self.config['bills_sync']['fields']
        # Quote field names to handle reserved keywords like 'time', 'user', and 'date'
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
                
                # Handle date conversion - ADDED
                if row_dict.get('date'):
                    if hasattr(row_dict['date'], 'isoformat'):
                        row_dict['date'] = row_dict['date'].isoformat()
                    elif row_dict['date'] is not None:
                        # Convert to string if it's not None and doesn't have isoformat
                        row_dict['date'] = str(row_dict['date'])
                
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
        print_status(f"Fetched {len(rows)} bill records from last 7 days", "SUCCESS")
        return rows

    def run(self):
        print_status("Starting Bills (7 days) sync...", "PROGRESS")
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
                print_status(f"Processing {len(data)} recent bill records", "PROGRESS")
            else:
                self.logger.info("No bill records found in the last 7 days")
                print_status("No recent bill records found", "INFO")
            
            ok, response = self.api_post(self.config['api']['bills_endpoint'], data)
            if ok:
                self.logger.info("Bills sync completed")
                print_status("Bills (7 days) sync completed", "SUCCESS")
            else:
                self.logger.error(f"Bills sync failed. Response: {response}")
                print_status(f"Bills sync failed: {response}", "ERROR")
            return ok
        except Exception as e:
            self.logger.error(f"Bills sync error: {str(e)}")
            print_status(f"Bills sync error: {str(e)}", "ERROR")
            return False
        finally:
            conn.close()


# ---------- NEW: DINE BILLS MONTH (ALL data) ----------
class BillsMonthSync(BaseSync):
    def __init__(self):
        super().__init__('bills_sync')  # Use same config as bills_sync

    def fetch(self, conn):
        fields = self.config['bills_sync']['fields']
        # Quote field names to handle reserved keywords like 'time', 'user', and 'date'
        quoted_fields = [f'"{field}"' for field in fields]
        
        # SQL query to get ALL data (no date filter)
        sql = f"""SELECT {', '.join(quoted_fields)} 
                  FROM dine_bill 
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
                
                # Handle date conversion
                if row_dict.get('date'):
                    if hasattr(row_dict['date'], 'isoformat'):
                        row_dict['date'] = row_dict['date'].isoformat()
                    elif row_dict['date'] is not None:
                        # Convert to string if it's not None and doesn't have isoformat
                        row_dict['date'] = str(row_dict['date'])
                
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
        self.logger.info(f"Fetched {len(rows)} dine_bill records (ALL data)")
        print_status(f"Fetched {len(rows)} bill records (ALL data)", "SUCCESS")
        return rows

    def run(self):
        print_status("Starting Bills Month (ALL) sync...", "PROGRESS")
        conn = self.connect_to_database()
        if not conn:
            return False
        try:
            data = self.fetch(conn)
            if data is None:
                return False
            
            total_records = len(data)
            
            if total_records == 0:
                self.logger.info("No bill records found")
                print_status("No bill records found", "INFO")
                return True
            
            # Process in batches to avoid timeout with large datasets
            batch_size = 500  # Smaller batch size for large datasets
            self.logger.info(f"Processing {total_records} records in batches of {batch_size}")
            print_status(f"Processing {total_records} records in batches of {batch_size}", "PROGRESS")
            
            for i in range(0, total_records, batch_size):
                batch = data[i:i + batch_size]
                batch_num = (i // batch_size) + 1
                total_batches = (total_records + batch_size - 1) // batch_size
                
                self.logger.info(f"Sending Bills Month batch {batch_num}/{total_batches} ({len(batch)} records)")
                print_status(f"Sending Bills Month batch {batch_num}/{total_batches} ({len(batch)} records)", "PROGRESS")
                
                # Use longer timeout for large datasets (5 minutes)
                ok, response = self.api_post(self.config['api']['bills_month_endpoint'], batch, timeout=300)
                if not ok:
                    self.logger.error(f"Bills Month batch {batch_num} failed. Response: {response}")
                    print_status(f"Bills Month batch {batch_num} failed: {response}", "ERROR")
                    return False
                
                # Add delay between batches for large datasets
                if batch_num < total_batches:
                    time.sleep(1.0)
            
            self.logger.info("Bills Month sync completed")
            print_status("Bills Month sync completed", "SUCCESS")
            return True
        except Exception as e:
            self.logger.error(f"Bills Month sync error: {str(e)}")
            print_status(f"Bills Month sync error: {str(e)}", "ERROR")
            return False
        finally:
            conn.close()


# ---------- KOT SALES DETAIL ----------
class KotSalesSync(BaseSync):
    def __init__(self):
        super().__init__('kot_sales_sync')

    def fetch(self, conn):
        fields = self.config['kot_sales_sync']['fields']
        # Quote field names to handle any reserved keywords
        quoted_fields = [f'"{field}"' for field in fields]
        
        # SQL query to get ALL data (no date filter)
        sql = f"""SELECT {', '.join(quoted_fields)} 
                  FROM dine_kot_sales_detail
                  ORDER BY "slno" DESC"""
        
        cursor = conn.cursor()
        cursor.execute(sql)
        
        rows = []
        for row in cursor:
            try:
                row_dict = dict(zip(fields, row))
                
                # Convert slno to string for JSON serialization
                if row_dict.get('slno') is not None:
                    row_dict['slno'] = str(int(float(row_dict['slno'])))
                
                # Convert billno to string for JSON serialization
                if row_dict.get('billno') is not None:
                    row_dict['billno'] = str(int(float(row_dict['billno'])))
                
                # Handle item field - strip whitespace if it exists
                if row_dict.get('item'):
                    row_dict['item'] = str(row_dict['item']).strip()
                
                # Handle qty - ensure it's a proper decimal/float
                if row_dict.get('qty') is not None:
                    row_dict['qty'] = float(row_dict['qty'])
                
                # Handle rate - ensure it's a proper decimal/float
                if row_dict.get('rate') is not None:
                    row_dict['rate'] = float(row_dict['rate'])
                
                rows.append(row_dict)
                
            except Exception as e:
                self.logger.error(f"Error processing KOT row {row}: {str(e)}")
                continue
        
        cursor.close()
        self.logger.info(f"Fetched {len(rows)} dine_kot_sales_detail records (ALL data)")
        print_status(f"Fetched {len(rows)} KOT sales detail records (ALL data)", "SUCCESS")
        return rows

    def run(self):
        print_status("Starting KOT Sales Detail sync...", "PROGRESS")
        conn = self.connect_to_database()
        if not conn:
            return False
        try:
            data = self.fetch(conn)
            if data is None:
                return False
            
            total_records = len(data)
            
            if total_records == 0:
                self.logger.info("No KOT sales detail records found")
                print_status("No KOT sales detail records found", "INFO")
                return True
            
            # Process in batches to avoid timeout with large datasets
            batch_size = 500  # Reduced batch size for very large datasets
            self.logger.info(f"Processing {total_records} records in batches of {batch_size}")
            print_status(f"Processing {total_records} records in batches of {batch_size}", "PROGRESS")
            
            for i in range(0, total_records, batch_size):
                batch = data[i:i + batch_size]
                batch_num = (i // batch_size) + 1
                total_batches = (total_records + batch_size - 1) // batch_size
                
                self.logger.info(f"Sending KOT batch {batch_num}/{total_batches} ({len(batch)} records)")
                print_status(f"Sending KOT batch {batch_num}/{total_batches} ({len(batch)} records)", "PROGRESS")
                
                # Use longer timeout for large datasets (5 minutes)
                ok, response = self.api_post(self.config['api']['kot_sales_endpoint'], batch, timeout=300)
                if not ok:
                    self.logger.error(f"KOT batch {batch_num} failed. Response: {response}")
                    print_status(f"KOT batch {batch_num} failed: {response}", "ERROR")
                    return False
                
                # Add longer delay between batches for very large datasets
                if batch_num < total_batches:
                    time.sleep(1.0)  # Increased from 0.5 to 1.0 second
            
            self.logger.info("KOT Sales Detail sync completed")
            print_status("KOT Sales Detail sync completed", "SUCCESS")
            return True
        except Exception as e:
            self.logger.error(f"KOT Sales Detail sync error: {str(e)}")
            print_status(f"KOT Sales Detail sync error: {str(e)}", "ERROR")
            return False
        finally:
            conn.close()


# ---------- CANCELLED BILLS ----------
class CancelledBillsSync(BaseSync):
    def __init__(self):
        super().__init__('cancelled_bills_sync')

    def fetch(self, conn):
        fields = self.config['cancelled_bills_sync']['fields']
        # Quote field names to handle reserved keywords like 'date'
        quoted_fields = [f'"{field}"' for field in fields]
        
        # SQL query to get ALL records from dine_bill table where colnstatus = 'C'
        # (no date filter - fetch all cancelled bills)
        sql = f"""SELECT {', '.join(quoted_fields)} 
                  FROM dine_bill 
                  WHERE "colnstatus" = 'C'
                  ORDER BY "billno" DESC"""
        
        cursor = conn.cursor()
        cursor.execute(sql)
        
        rows = []
        for row in cursor:
            try:
                row_dict = dict(zip(fields, row))
                
                # Convert billno to string for JSON serialization
                if row_dict.get('billno') is not None:
                    row_dict['billno'] = str(int(float(row_dict['billno'])))
                
                # Handle date conversion
                if row_dict.get('date'):
                    if hasattr(row_dict['date'], 'isoformat'):
                        row_dict['date'] = row_dict['date'].isoformat()
                    elif row_dict['date'] is not None:
                        # Convert to string if it's not None and doesn't have isoformat
                        row_dict['date'] = str(row_dict['date'])
                
                # Handle creditcard field - strip whitespace if it exists
                if row_dict.get('creditcard'):
                    row_dict['creditcard'] = str(row_dict['creditcard']).strip()
                
                # Handle colnstatus field - strip whitespace if it exists
                if row_dict.get('colnstatus'):
                    row_dict['colnstatus'] = str(row_dict['colnstatus']).strip()
                
                rows.append(row_dict)
                
            except Exception as e:
                self.logger.error(f"Error processing cancelled bills row {row}: {str(e)}")
                continue
        
        cursor.close()
        self.logger.info(f"Fetched {len(rows)} cancelled_bills records (colnstatus='C', ALL data)")
        print_status(f"Fetched {len(rows)} cancelled bills records (colnstatus='C', ALL data)", "SUCCESS")
        return rows

    def run(self):
        print_status("Starting Cancelled Bills sync...", "PROGRESS")
        conn = self.connect_to_database()
        if not conn:
            return False
        try:
            data = self.fetch(conn)
            if data is None:
                return False
            
            # Log sample data for debugging
            if data:
                self.logger.info(f"Sample cancelled bill record: {data[0]}")
                self.logger.info(f"Date range: All data where colnstatus='C'")
                print_status(f"Processing {len(data)} cancelled bill records", "PROGRESS")
            else:
                self.logger.info("No cancelled bill records (colnstatus='C') found")
                print_status("No cancelled bill records (colnstatus='C') found", "INFO")
            
            ok, response = self.api_post(self.config['api']['cancelled_bills_endpoint'], data)
            if ok:
                self.logger.info("Cancelled Bills sync completed")
                print_status("Cancelled Bills sync completed", "SUCCESS")
            else:
                self.logger.error(f"Cancelled Bills sync failed. Response: {response}")
                print_status(f"Cancelled Bills sync failed: {response}", "ERROR")
            return ok
        except Exception as e:
            self.logger.error(f"Cancelled Bills sync error: {str(e)}")
            print_status(f"Cancelled Bills sync error: {str(e)}", "ERROR")
            return False
        finally:
            conn.close()


# ---------- MAIN ----------
def main():
    # Clear screen and show header
    os.system('cls' if os.name == 'nt' else 'clear')
    print_header()
    
    print_status("Initializing sync process...", "PROGRESS")
    print_status("Syncing 6 tables: acc_users, tb_item_master, dine_bill (7 days), dine_bill_month (ALL), dine_kot_sales_detail, cancelled_bills", "INFO")
    print()
    
    # Run all syncs automatically
    sync_results = []
    
    print_status("Step 1/6: Syncing User Accounts", "PROGRESS")
    ok1 = AccUsersSync().run()
    sync_results.append(("acc_users", ok1))
    print()
    
    print_status("Step 2/6: Syncing Item Master", "PROGRESS")
    ok2 = ItemsSync().run()
    sync_results.append(("tb_item_master", ok2))
    print()
    
    print_status("Step 3/6: Syncing Recent Bills (7 days)", "PROGRESS")
    ok3 = BillsSync().run()
    sync_results.append(("dine_bill (7 days)", ok3))
    print()
    
    print_status("Step 4/6: Syncing All Bills (Month)", "PROGRESS")
    ok4 = BillsMonthSync().run()
    sync_results.append(("dine_bill_month (ALL)", ok4))
    print()
    
    print_status("Step 5/6: Syncing KOT Sales Detail", "PROGRESS")
    ok5 = KotSalesSync().run()
    sync_results.append(("dine_kot_sales_detail", ok5))
    print()
    
    print_status("Step 6/6: Syncing Cancelled Bills", "PROGRESS")
    ok6 = CancelledBillsSync().run()
    sync_results.append(("cancelled_bills", ok6))
    print()
    
    # Print final summary
    print_summary(sync_results)
    
    # Keep window open
    print("\nSync process completed.")
    print("Check sync.log file for detailed information.")
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()