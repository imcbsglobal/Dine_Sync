"""
Build script to create executable from sync.py
This script uses PyInstaller to create a standalone executable

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
            print(f"✓ {package} installed successfully")
        except subprocess.CalledProcessError:
            print(f"✗ Failed to install {package}")
            return False
    return True

def build_executable():
    """Build executable using PyInstaller"""
    try:
        print("\nBuilding executable...")
        
        # PyInstaller command
        cmd = [
            'pyinstaller',
            '--onefile',           # Create a single executable file
            '--windowed',          # No console window (remove this if you want console)
            '--name=sync',         # Name of the executable
            '--clean',             # Clean build
            '--distpath=dist',     # Output directory
            'sync.py'              # Source file
        ]
        
        # Run PyInstaller
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✓ Executable built successfully!")
            
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
                    else:
                        shutil.copy2(file_path, dist_dir)
                    print(f"✓ Copied {file_path}")
                else:
                    print(f"✗ Warning: {file_path} not found")
            
            # Create README
            readme_content = """Database Sync Tool
==================

Files in this folder:
- sync.exe: The main sync executable
- config.json: Configuration file (edit as needed)
- sync.bat: Batch file to run the sync tool
- README.txt: This file

Instructions:
1. Edit config.json with your database details
2. Double-click sync.bat to run the sync
3. Or double-click sync.exe directly

Configuration:
- Update the DSN name in config.json to match your ODBC data source name
- Update username and password if different
- Update API URL if your web server is running on a different address

Support:
Check sync.log file for detailed error messages if sync fails.
"""
            
            with open(os.path.join(dist_dir, 'README.txt'), 'w') as f:
                f.write(readme_content)
            
            print(f"\n✓ Distribution package created in '{dist_dir}' folder")
            print("You can now distribute this folder to users.")
            
            return True
        else:
            print(f"✗ Build failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"✗ Build error: {str(e)}")
        return False

def cleanup():
    """Clean up build artifacts"""
    try:
        folders_to_remove = ['build', 'dist', '__pycache__']
        files_to_remove = ['sync.spec']
        
        for folder in folders_to_remove:
            if os.path.exists(folder):
                shutil.rmtree(folder)
                print(f"✓ Cleaned up {folder}")
        
        for file in files_to_remove:
            if os.path.exists(file):
                os.remove(file)
                print(f"✓ Cleaned up {file}")
                
    except Exception as e:
        print(f"Warning: Cleanup error: {str(e)}")

def main():
    print("=== Database Sync Tool Builder ===")
    print("This script will create a standalone executable for the sync tool.\n")
    
    # Check if sync.py exists
    if not os.path.exists('sync.py'):
        print("✗ Error: sync.py not found in current directory")
        input("Press Enter to exit...")
        return
    
    # Check if config.json exists
    if not os.path.exists('config.json'):
        print("✗ Error: config.json not found in current directory")
        input("Press Enter to exit...")
        return
    
    try:
        # Install requirements
        if not install_requirements():
            print("✗ Failed to install requirements")
            input("Press Enter to exit...")
            return
        
        # Build executable
        if build_executable():
            print("\n🎉 Build completed successfully!")
            print("The sync tool is ready for distribution.")
        else:
            print("\n✗ Build failed")
        
        # Cleanup
        cleanup()
        
    except KeyboardInterrupt:
        print("\n\nBuild cancelled by user")
    except Exception as e:
        print(f"\n✗ Unexpected error: {str(e)}")
    
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()