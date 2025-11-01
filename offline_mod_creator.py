import os
import zipfile
import tempfile
import shutil

class OfflineModCreator:
    def __init__(self, base_pkg_path=None):
        """
        Initialize the offline mod creator
        base_pkg_path: Path to reference mod package (e.g., C:\\Users\\m_web\\Downloads\\1_11_2931_2_active)
        """
        self.base_pkg_path = base_pkg_path
        
    def create_game_cfg_offline(self):
        """Create a modified game.cfg with Waypoint disabled"""
        cfg_content = """// Halo Wars 2 - Offline Mode Configuration
// Modified by Nuphillion Launcher to disable Waypoint connections

// Disable Waypoint/Xbox Live connections
setOption("WaypointEnabled", false)
setOption("XboxLiveEnabled", false)
setOption("OnlineEnabled", false)
setOption("TelemetryEnabled", false)
setOption("AnalyticsEnabled", false)

// Force offline mode
setOption("ForceOfflineMode", true)
setOption("SkipWaypointLogin", true)

// Disable cloud sync
setOption("CloudSaveEnabled", false)

// Keep game functionality
setOption("EnableSkirmish", true)
setOption("EnableCampaign", true)
setOption("EnableMultiplayer", false)

// Performance settings for offline play
setOption("NetworkTimeout", 0)
setOption("ConnectionRetries", 0)
"""
        return cfg_content
    
    def create_offline_mod_package(self, output_path, version="1_11_2931_2"):
        """
        Create a complete offline mod package
        output_path: Where to save the offline mod zip
        version: Game version for manifest
        """
        try:
            # Create temp directory for mod structure
            with tempfile.TemporaryDirectory() as temp_dir:
                # Create data/startup directory structure
                startup_dir = os.path.join(temp_dir, "data", "startup")
                os.makedirs(startup_dir, exist_ok=True)
                
                # Create modified game.cfg
                cfg_path = os.path.join(startup_dir, "game.cfg")
                with open(cfg_path, 'w', encoding='utf-8') as f:
                    f.write(self.create_game_cfg_offline())
                
                # Create manifest XML
                manifest_content = f"""<?xml version="1.0" encoding="utf-8"?>
<fileManifest>
  <version>{version}</version>
  <file>
    <path>data/startup/game.cfg</path>
    <size>{os.path.getsize(cfg_path)}</size>
  </file>
</fileManifest>
"""
                manifest_path = os.path.join(temp_dir, f"{version}_file_manifest.xml")
                with open(manifest_path, 'w', encoding='utf-8') as f:
                    f.write(manifest_content)
                
                # Create PKG file (zip the data directory)
                pkg_path = os.path.join(temp_dir, "OfflineMode.pkg")
                with zipfile.ZipFile(pkg_path, 'w', zipfile.ZIP_DEFLATED) as pkg_zip:
                    # Add all files with proper structure
                    for root, dirs, files in os.walk(os.path.join(temp_dir, "data")):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, temp_dir)
                            pkg_zip.write(file_path, arcname)
                
                # Create final mod package zip
                with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as mod_zip:
                    mod_zip.write(pkg_path, os.path.basename(pkg_path))
                    mod_zip.write(manifest_path, os.path.basename(manifest_path))
                
                return True, "Offline mod package created successfully"
                
        except Exception as e:
            return False, f"Failed to create offline mod: {str(e)}"
    
    def patch_existing_mod(self, mod_zip_path, output_path):
        """
        Patch an existing mod to add offline functionality
        mod_zip_path: Path to existing mod zip
        output_path: Where to save patched mod
        """
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                # Extract existing mod
                with zipfile.ZipFile(mod_zip_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                
                # Find and extract PKG if it exists
                pkg_files = [f for f in os.listdir(temp_dir) if f.endswith('.pkg')]
                if not pkg_files:
                    return False, "No PKG file found in mod"
                
                pkg_path = os.path.join(temp_dir, pkg_files[0])
                pkg_extract_dir = os.path.join(temp_dir, "pkg_extracted")
                
                with zipfile.ZipFile(pkg_path, 'r') as pkg_zip:
                    pkg_zip.extractall(pkg_extract_dir)
                
                # Create or modify game.cfg
                cfg_dir = os.path.join(pkg_extract_dir, "data", "startup")
                os.makedirs(cfg_dir, exist_ok=True)
                
                cfg_path = os.path.join(cfg_dir, "game.cfg")
                with open(cfg_path, 'w', encoding='utf-8') as f:
                    f.write(self.create_game_cfg_offline())
                
                # Repack PKG
                os.remove(pkg_path)
                with zipfile.ZipFile(pkg_path, 'w', zipfile.ZIP_DEFLATED) as new_pkg:
                    for root, dirs, files in os.walk(pkg_extract_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, pkg_extract_dir)
                            new_pkg.write(file_path, arcname)
                
                # Create patched mod zip
                shutil.make_archive(output_path.replace('.zip', ''), 'zip', temp_dir)
                
                return True, "Mod patched successfully with offline mode"
                
        except Exception as e:
            return False, f"Failed to patch mod: {str(e)}"


def create_standalone_offline_mod(output_dir):
    """
    Create a standalone offline mod package
    output_dir: Directory to save the mod
    """
    creator = OfflineModCreator()
    output_path = os.path.join(output_dir, "HW2_OfflineMode.zip")
    success, message = creator.create_offline_mod_package(output_path)
    return success, message, output_path if success else None
