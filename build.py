"""
Build script to create console executable from sync.py
This script uses PyInstaller to create a standalone executable with console window

Requirements:
pip install pyinstaller pyodbc requests

Usage:
python build.py
"""

import os
import subprocess
import sys
import shutil

def install_requirements():
    """Install required packages"""
    requirements = [
        'pyinstaller',
        'pyodbc',
        'requests'
    ]
    
    print("Installing required packages...")
    for package in requirements:
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
            print(f"✅ {package} installed successfully")
        except subprocess.CalledProcessError:
            print(f"❌ Failed to install {package}")
            return False
    return True

def build_executable():
    """Build executable using PyInstaller"""
    try:
        print("\nBuilding console executable...")
        
        # PyInstaller command for CONSOLE application (removed --windowed)
        cmd = [
            'pyinstaller',
            '--onefile',           # Create a single executable file
            '--console',           # Show console window (explicit)
            '--name=sync',         # Name of the executable
            '--clean',             # Clean build
            '--distpath=dist',     # Output directory
            '--add-data=config.json;.',  # Include config.json
            'sync.py'              # Source file
        ]
        
        # Run PyInstaller
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Executable built successfully!")
            
            # Copy files to distribution folder
            dist_dir = 'sync_tool_dist'
            if os.path.exists(dist_dir):
                shutil.rmtree(dist_dir)
            os.makedirs(dist_dir)
            
            # Copy files
            files_to_copy = [
                'dist/sync.exe',
                'config.json',
                'sync.bat'
            ]
            
            for file_path in files_to_copy:
                if os.path.exists(file_path):
                    if file_path.endswith('.exe'):
                        shutil.copy2(file_path, os.path.join(dist_dir, 'sync.exe'))
                        print(f"✅ Copied {file_path}")
                    else:
                        shutil.copy2(file_path, dist_dir)
                        print(f"✅ Copied {file_path}")
                else:
                    print(f"⚠️  Warning: {file_path} not found")
            
            # Create improved batch file
            create_improved_batch(dist_dir)
            
            # Create README
            readme_content = """Database Sync Tool - Console Version
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
"""
            
            with open(os.path.join(dist_dir, 'README.txt'), 'w') as f:
                f.write(readme_content)
                
            print(f"\n✅ Distribution package created in '{dist_dir}' folder")
            print("📁 The executable will show a console window with real-time progress")
            print("🚀 You can now distribute this folder to users.")
            
            return True
        else:
            print(f"❌ Build failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Build error: {str(e)}")
        return False

def create_improved_batch(dist_dir):
    """Create improved batch files"""
    
    # Console batch file
    console_batch_content = """@echo off
title Database Sync Tool - Console
color 0A
echo.
echo ===============================================
echo           DATABASE SYNC TOOL
echo ===============================================
echo.

REM Check if sync.exe exists
if exist sync.exe (
    echo Starting sync process...
    echo.
    sync.exe
) else (
    echo ERROR: sync.exe not found!
    echo Please make sure sync.exe is in the same folder as this batch file.
    echo.
    pause
    exit /b 1
)

echo.
echo Sync process completed.
echo Check sync.log for detailed information.
pause
"""
    
    # Background batch file
    background_batch_content = """@echo off
REM Run sync in background without console window
if exist sync.exe (
    start /min sync.exe
) else (
    echo ERROR: sync.exe not found!
    pause
)
"""
    
    with open(os.path.join(dist_dir, 'sync_console.bat'), 'w') as f:
        f.write(console_batch_content)
    print("✅ Created sync_console.bat")
    
    with open(os.path.join(dist_dir, 'sync_background.bat'), 'w') as f:
        f.write(background_batch_content)
    print("✅ Created sync_background.bat")

def cleanup():
    """Clean up build artifacts"""
    try:
        folders_to_remove = ['build', 'dist', '__pycache__']
        files_to_remove = ['sync.spec']
        
        for folder in folders_to_remove:
            if os.path.exists(folder):
                shutil.rmtree(folder)
                print(f"🧹 Cleaned up {folder}")
        
        for file in files_to_remove:
            if os.path.exists(file):
                os.remove(file)
                print(f"🧹 Cleaned up {file}")
                
    except Exception as e:
        print(f"Warning: Cleanup error: {str(e)}")

def main():
    print("=" * 60)
    print("    DATABASE SYNC TOOL - CONSOLE BUILDER")
    print("=" * 60)
    print("This script will create a console executable for the sync tool.")
    print("The executable will show real-time progress in a terminal window.\n")
    
    # Check if sync.py exists
    if not os.path.exists('sync.py'):
        print("❌ Error: sync.py not found in current directory")
        input("Press Enter to exit...")
        return
    
    # Check if config.json exists
    if not os.path.exists('config.json'):
        print("❌ Error: config.json not found in current directory")
        input("Press Enter to exit...")
        return
    
    try:
        # Install requirements
        if not install_requirements():
            print("❌ Failed to install requirements")
            input("Press Enter to exit...")
            return
        
        # Build executable
        if build_executable():
            print("\n🎉 Build completed successfully!")
            print("📺 The sync tool will now display progress in a console window.")
            print("💡 Double-click sync.exe or run sync_console.bat to start syncing.")
        else:
            print("\n❌ Build failed")
        
        # Cleanup
        cleanup()
        
    except KeyboardInterrupt:
        print("\n\nBuild cancelled by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
    
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()