import os
import zipfile
import shutil
import tempfile
import io


class OfflinePackageGenerator:
    def __init__(self, cache_dir):
        self.cache_dir = cache_dir
        self.offline_suffix = "_offline"
    
    def get_offline_package_path(self, mod_name):
        """Get the path for the offline version of a package"""
        base_path = os.path.join(self.cache_dir, f"{mod_name}.zip")
        offline_path = os.path.join(self.cache_dir, f"{mod_name}{self.offline_suffix}.zip")
        return base_path, offline_path
    
    def modify_game_cfg(self, cfg_content):
        """Modify game.cfg to disable waypoint connections"""
        # Try different encodings
        encodings = ['utf-8', 'utf-16', 'latin-1', 'cp1252']
        text = None
        used_encoding = None

        for enc in encodings:
            try:
                text = cfg_content.decode(enc)
                used_encoding = enc
                break
            except UnicodeDecodeError:
                continue
        
        if text is None:
            print("  Warning: Could not decode game.cfg with standard encodings.")
            return cfg_content
        
        # Use splitlines(keepends=True) to preserve original line endings (CRLF/LF)
        lines = text.splitlines(keepends=True)
        modified_lines = []
        modifications_count = 0
        
        for line in lines:
            # Disable waypoint-related settings
            # Check for 'waypoint' and '=' and ensure it's not a comment
            clean_line = line.strip()
            if 'waypoint' in clean_line.lower() and '=' in clean_line and not clean_line.startswith('//') and not clean_line.startswith(';'):
                parts = line.split('=')
                key = parts[0].strip()
                # We reconstruct the line with = 0, preserving the original line ending if possible
                # or defaulting to \n if splitlines didn't keep it (though keepends=True should)
                ending = ""
                if line.endswith('\r\n'): ending = '\r\n'
                elif line.endswith('\n'): ending = '\n'
                else: ending = '\n'
                
                modified_lines.append(f"{key} = 0{ending}")
                modifications_count += 1
                print(f"  Modified: {clean_line} -> {key} = 0")
            else:
                modified_lines.append(line)
        
        if modifications_count > 0:
            return ''.join(modified_lines).encode(used_encoding)
        else:
            return cfg_content
    
    def create_offline_package(self, mod_name):
        """Create an offline version of a cached package"""
        base_path, offline_path = self.get_offline_package_path(mod_name)
        
        if not os.path.exists(base_path):
            raise FileNotFoundError(f"Base package not found: {base_path}")
        
        if not zipfile.is_zipfile(base_path):
            raise ValueError(f"Base package is not a valid zip file: {base_path}")
        
        print(f"Creating offline package for {mod_name}...")
        modified = False
        
        # Read the main zip and process all files
        with zipfile.ZipFile(base_path, 'r') as main_zip:
            with zipfile.ZipFile(offline_path, 'w', zipfile.ZIP_DEFLATED) as out_zip:
                for item in main_zip.infolist():
                    try:
                        data = main_zip.read(item.filename)
                        
                        # Check if this is a .pkg file (which might be a nested zip)
                        if item.filename.endswith('.pkg'):
                            print(f"Processing {item.filename}...")
                            
                            # Try to process as a nested zip
                            # We check magic bytes for PK zip header (50 4B 03 04) to avoid unnecessary exceptions
                            if len(data) > 4 and data.startswith(b'PK\x03\x04'):
                                try:
                                    modified_pkg, pkg_modified = self._modify_pkg_content(data, item.filename)
                                    if pkg_modified:
                                        data = modified_pkg
                                        modified = True
                                except Exception as e:
                                    print(f"  Failed to process nested pkg {item.filename}: {e}")
                            else:
                                print(f"  {item.filename} is not a zip file (magic bytes mismatch), keeping as-is")
                        
                        # Write the file (modified or original)
                        out_zip.writestr(item, data)
                    except Exception as e:
                        print(f"Error processing file {item.filename} in main zip: {e}")
                        # Try to continue with other files if one fails
        
        if modified:
            print(f"Successfully created offline package: {offline_path}")
        else:
            print(f"Warning: No game.cfg found to modify in {mod_name}")
        
        return offline_path
    
    def _modify_pkg_content(self, pkg_data, pkg_filename):
        """Modify the content of a .pkg file (nested zip)"""
        modified = False
        output = io.BytesIO()
        
        try:
            with zipfile.ZipFile(io.BytesIO(pkg_data), 'r') as pkg_in:
                with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as pkg_out:
                    for item in pkg_in.infolist():
                        data = pkg_in.read(item.filename)
                        
                        # Check if this is game.cfg
                        normalized_path = item.filename.replace('\\', '/').lower()
                        if normalized_path.endswith('data/startup/game.cfg'):
                            print(f"  Found game.cfg at: {item.filename}")
                            original_size = len(data)
                            data = self.modify_game_cfg(data)
                            modified = True
                            print(f"  Modified game.cfg (size: {original_size} -> {len(data)} bytes)")
                        
                        pkg_out.writestr(item, data)
            
            return output.getvalue(), modified
            
        except zipfile.BadZipFile as e:
            print(f"  Error: {pkg_filename} nested content is not a valid zip: {e}")
            return pkg_data, False
        except Exception as e:
            print(f"  Error processing {pkg_filename}: {e}")
            return pkg_data, False
    
    def offline_package_exists(self, mod_name):
        """Check if offline package exists"""
        _, offline_path = self.get_offline_package_path(mod_name)
        return os.path.exists(offline_path)
    
    def get_package_path(self, mod_name, offline=False):
        """Get the appropriate package path based on mode"""
        base_path, offline_path = self.get_offline_package_path(mod_name)
        return offline_path if offline else base_path
