# Hermes AGI/ASI Harness - Installation Script for Hermes Agent
# Run this to install the harness into the Hermes Agent environment

import os
import sys
from pathlib import Path

HARNESS_PATH = Path("/c/Users/PREM KUMAR/Downloads/HERMES-AGI-ASI-HARNESS-ULTIMATE-BUILD")
VENV_PATH = Path("C:/Users/PREM KUMAR/AppData/Local/hermes/hermes-agent/venv")

def install_harness():
    """Install the harness into the Hermes Agent environment."""
    
    # Step 1: Install dependencies
    print("Installing dependencies...")
    req_file = HARNESS_PATH / "requirements.txt"
    if req_file.exists():
        os.system(f"pip install -r {req_file}")
    
    # Step 2: Create .pth file for Python path
    print("Creating Python path configuration...")
    site_packages = VENV_PATH / "Lib" / "site-packages"
    
    pth_file = site_packages / "hermes_agi_asi_harness.pth"
    with open(pth_file, 'w') as f:
        f.write(str(HARNESS_PATH) + "\n")
        f.write(str(HARNESS_PATH / "core") + "\n")
    
    print(f"Created: {pth_file}")
    
    # Step 3: Verify installation
    print("\nVerifying installation...")
    sys.path.insert(0, str(HARNESS_PATH))
    
    try:
        from core.dynamic import DynamicScenarioAnalyzer
        print("✓ Dynamic Scenario Analyzer loaded")
    except ImportError as e:
        print(f"✗ Failed to load: {e}")
        return False
    
    try:
        from core.coding import RepositoryDigitalTwin
        print("✓ Repository Digital Twin loaded")
    except ImportError as e:
        print(f"✗ Failed to load: {e}")
        return False
    
    try:
        from core.runtime.kernel import HermesKernel
        print("✓ Hermes Kernel loaded")
    except ImportError as e:
        print(f"✗ Failed to load: {e}")
        return False
    
    print("\n✓ Harness installed successfully!")
    print(f"  Harness path: {HARNESS_PATH}")
    print(f"  Venv path: {VENV_PATH}")
    print("\nYou can now use the harness in Hermes Agent:")
    print("  from core.dynamic import DynamicScenarioAnalyzer")
    print("  from core.coding import RepositoryDigitalTwin")
    print("  from core.runtime.kernel import HermesKernel")
    
    return True


if __name__ == "__main__":
    install_harness()
