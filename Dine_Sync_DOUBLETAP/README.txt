Database Sync Tool - Console Version
========================================

Files in this folder:
- sync.exe: The main sync executable (console application)
- config.json: Configuration file (edit as needed)
- sync_console.bat: Batch file to run sync with console window
- sync_background.bat: Batch file to run sync in background
- README.txt: This file

How to Use:
-----------

Method 1: Double-click sync.exe
- Shows real-time progress in console window
- Window stays open until you press Enter

Method 2: Use sync_console.bat
- Same as Method 1 but with better window title
- Recommended for regular use

Method 3: Use sync_background.bat
- Runs sync without showing window
- Good for scheduled tasks

Configuration:
--------------
Edit config.json to update:
- DSN name (match your ODBC data source name)
- Database username and password
- API URL (if your web server is on different address)

Troubleshooting:
---------------
- Check sync.log file for detailed error messages
- Make sure your database is running and accessible
- Verify your API server is running
- Check your ODBC connection settings

Support:
--------
The sync tool will show detailed progress and any errors in the console window.
All activities are also logged to sync.log file for later review.
