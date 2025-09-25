# Database Sync Tool - Terminal Version Setup Guide

## Step 1: Create New Project Folder

1. Create a new folder for your sync tool project (e.g., `database_sync_tool`)
2. Copy these files into the new folder:
   - `sync.py` (use the modified version from above)
   - `build.py` (use the modified version from above)
   - `config.json` (your existing config file)

## Step 2: Folder Structure

Your project folder should look like this:
```
database_sync_tool/
├── sync.py          # Main sync script (modified for terminal display)
├── build.py         # Build script (modified for console app)
├── config.json      # Database and API configuration
└── README.md        # This setup guide
```

## Step 3: Build the Executable

1. Open Command Prompt or PowerShell
2. Navigate to your project folder:
   ```cmd
   cd path\to\your\database_sync_tool
   ```
3. Run the build script:
   ```cmd
   python build.py
   ```

## Step 4: Distribution Folder

After building, you'll get a `sync_tool_dist` folder containing:
```
sync_tool_dist/
├── sync.exe              # Main executable (console application)
├── config.json           # Configuration file
├── sync_console.bat      # Recommended way to run
├── sync_background.bat   # Run without showing window
└── README.txt            # User instructions
```

## Step 5: How Users Will Use It

### Method 1: Double-click sync.exe
- Opens a console window showing real-time progress
- Displays colorful status messages with timestamps
- Shows progress bars and batch information
- Window stays open until user presses Enter

### Method 2: Double-click sync_console.bat (Recommended)
- Same as Method 1 but with better window title and colors
- More user-friendly experience

### Method 3: Use sync_background.bat
- Runs sync without showing window
- Good for scheduled tasks or background operations

## What Users Will See

When they double-click the executable, they'll see:

```
======================================================================
🔄 DATABASE SYNC TOOL
======================================================================
⏰ Started at: 2025-09-25 14:30:15
======================================================================

[14:30:15] 🔄 Initializing sync process...
[14:30:15] ℹ️  Syncing 6 tables: acc_users, tb_item_master, dine_bill (7 days), dine_bill_month (ALL), dine_kot_sales_detail, cancelled_bills

[14:30:15] 🔄 Step 1/6: Syncing User Accounts
[14:30:15] 🔄 Connecting to database: DINE
[14:30:16] ✅ Database connection successful
[14:30:16] ✅ Fetched 2 user records
[14:30:16] 🔄 Sending 2 user records to API...
[14:30:17] ✅ User Accounts sync completed

[14:30:17] 🔄 Step 2/6: Syncing Item Master
[14:30:17] 🔄 Connecting to database: DINE
[14:30:17] ✅ Database connection successful
[14:30:18] ✅ Fetched 133 item records
[14:30:18] 🔄 Processing 133 records in batches of 1000
[14:30:18] 🔄 Sending batch 1/1 (133 records)
[14:30:20] ✅ Items sync completed

... and so on for all 6 tables ...

======================================================================
📊 SYNC RESULTS SUMMARY
======================================================================
acc_users                          - ✅ SUCCESS
tb_item_master                      - ✅ SUCCESS
dine_bill (7 days)                  - ✅ SUCCESS
dine_bill_month (ALL)               - ✅ SUCCESS
dine_kot_sales_detail               - ✅ SUCCESS
cancelled_bills                     - ✅ SUCCESS
======================================================================
📈 Summary: 6/6 tables synced successfully
🎉 All synchronizations completed successfully!
======================================================================

🔚 Sync process completed.
📄 Check sync.log file for detailed information.

⏸️  Press Enter to exit...
```

## Key Features

### Real-time Progress Display
- Timestamped messages showing exactly what's happening
- Color-coded status indicators (✅ success, ❌ error, 🔄 progress)
- Batch progress indicators for large datasets
- Clear step-by-step progression

### Error Handling
- Clear error messages if database connection fails
- API connection error reporting
- Detailed error logging to sync.log file
- Graceful handling of missing configuration

### User Experience
- Console window stays open so users can see results
- Summary at the end showing success/failure for each table
- Instruction to check log file for detailed information
- Professional appearance with headers and separators

## Configuration

Users can edit `config.json` to change:
- Database connection settings (DSN, username, password)
- API endpoints and server URL
- Batch sizes for large datasets
- Logging levels

## Deployment

The `sync_tool_dist` folder contains everything needed:
- No installation required
- No dependencies to install
- Works on any Windows machine with the database drivers
- Self-contained executable

## Benefits of This Approach

1. **Visual Feedback**: Users can see exactly what's happening
2. **Error Transparency**: Clear error messages and logging
3. **Professional Appearance**: Clean, organized output
4. **User Control**: Window stays open until dismissed
5. **Multiple Run Options**: Console, background, or direct executable
6. **Self-contained**: No external dependencies needed
7. **Logging**: Detailed logs for troubleshooting

This setup gives you a professional, user-friendly sync tool that provides excellent visibility into the synchronization process.