#!/usr/bin/env python3
"""
UV Setup Script for Property Analytics Project
Simple setup with single requirements.txt file
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd, description):
    """Run a command and print the result"""
    print(f"\n🔄 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        if result.stdout:
            print(f"Output: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed")
        print(f"Error: {e.stderr.strip()}")
        return False

def check_uv_installed():
    """Check if uv is installed"""
    try:
        subprocess.run(["uv", "--version"], check=True, capture_output=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def install_uv():
    """Install uv package manager"""
    print("🔄 Installing uv package manager...")
    
    # For macOS/Linux
    if os.name != 'nt':
        cmd = "curl -LsSf https://astral.sh/uv/install.sh | sh"
    else:
        # For Windows
        cmd = "powershell -c \"irm https://astral.sh/uv/install.ps1 | iex\""
    
    return run_command(cmd, "Installing uv")

def setup_uv_project():
    """Setup the project with uv"""
    print("\n🚀 Setting up Property Analytics project with uv...")
    
    # Check if uv is installed
    if not check_uv_installed():
        print("❌ uv is not installed. Installing now...")
        if not install_uv():
            print("❌ Failed to install uv. Please install manually from https://github.com/astral-sh/uv")
            return False
        
        # Add uv to PATH for current session
        if os.name != 'nt':
            os.environ['PATH'] = f"{os.path.expanduser('~/.cargo/bin')}:{os.environ['PATH']}"
    
    print("✅ uv is installed")
    
    # Setup commands
    commands = [
        ("uv cache clean", "Clearing uv cache"),
        ("uv venv --python 3.11", "Creating virtual environment with Python 3.11"),
        ("uv pip install -r requirements.txt", "Installing all dependencies"),
        ("uv pip install -e .", "Installing project in development mode"),
    ]
    
    for cmd, description in commands:
        if not run_command(cmd, description):
            return False
    
    return True

def cleanup_poetry_remnants():
    """Remove any remaining Poetry files"""
    print("\n🧹 Cleaning up Poetry remnants...")
    
    # Files to remove
    files_to_remove = [
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
    ]
    
    for file_path in files_to_remove:
        if os.path.exists(file_path):
            if os.path.isdir(file_path):
                run_command(f"rm -rf {file_path}", f"Removing directory {file_path}")
            else:
                run_command(f"rm {file_path}", f"Removing file {file_path}")

def show_usage_instructions():
    """Show instructions for using uv"""
    print("""
🎉 Setup Complete! Your project is now configured to use uv.

📋 Common uv Commands:

1. 📦 Install dependencies:
   uv pip install -r requirements.txt

2. 🔧 Install development dependencies:
   uv pip install -e ".[dev]"

3. 🐍 Run Python scripts:
   uv run python script.py

4. 📓 Start Jupyter Lab:
   uv run jupyter lab

5. 🕷️ Run scrapers:
   uv run scrapy crawl property_finder

6. 🧪 Run tests:
   uv run pytest

7. 🎨 Format code:
   uv run black .
   uv run isort .

8. 🔍 Type checking:
   uv run mypy src/

🌟 Key Benefits of uv:
- ⚡ 10-100x faster than pip
- 🔒 Reliable dependency resolution
- 🐍 Works with existing Python ecosystem
- 📦 Single requirements.txt file

💡 Pro Tips:
- Use 'uv add package-name' to add new dependencies
- Use 'uv remove package-name' to remove dependencies
- Use 'uv run' prefix for all Python commands

🔄 To activate the virtual environment manually:
source .venv/bin/activate  # On Unix/macOS
.venv\\Scripts\\activate   # On Windows

📚 Documentation: https://docs.astral.sh/uv/
""")

def main():
    """Main setup function"""
    print("🏗️  Property Analytics Project - UV Setup")
    print("=" * 50)
    
    # Change to project directory
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    # Clean up Poetry remnants
    cleanup_poetry_remnants()
    
    # Setup uv project
    if setup_uv_project():
        show_usage_instructions()
        print("\n✅ Project successfully migrated to uv!")
        print("🔥 Single requirements.txt file with all dependencies!")
    else:
        print("\n❌ Setup failed. Check the errors above and try again.")
        sys.exit(1)

if __name__ == "__main__":
    main() 