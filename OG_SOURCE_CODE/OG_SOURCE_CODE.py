import flet as ft
import os
import shutil
import requests
import zipfile
import asyncio
import io

# Define global constants
VERSION = '1_11_2931_2'
VERSION_PTR = '1_11_2931_10'
RELEASE_URI = 'https://github.com/CutesyThrower12/Nuphillion/releases/download/vInDev/nuphillion.zip'
OG_FILES_URL = 'https://github.com/CutesyThrower12/HW2-Original-Files/releases/download/1.0/hw2ogfiles.zip'
HW2_HOGAN_PATH = "Packages\\Microsoft.HoganThreshold_8wekyb3d8bbwe\\LocalState"

# Get the local AppData path
appData = os.environ.get('LOCALAPPDATA')
if not appData:
    raise RuntimeError("Unable to find LOCALAPPDATA.")

# Define ModManager class
class ModManager:
    def __init__(self, appData):
        self.localStateDir = os.path.join(appData, HW2_HOGAN_PATH)
        self.version = VERSION
        self.mod_package = self.get_latest_mod()
        if os.path.isdir(self.localPkgDir(VERSION_PTR)):
            self.version = VERSION_PTR

    def localPkgDir(self, version=None):
        """Returns the directory path for the given or current version."""
        if version:
            return os.path.join(self.localStateDir, f"GTS\\{version}_active")
        return os.path.join(self.localStateDir, f"GTS\\{self.version}_active")

    def localPkgPath(self):
        """Path to the mod package file."""
        return os.path.join(self.localPkgDir(), 'NuphillionMod.pkg')

    def localManifestPath(self):
        """Path to the mod manifest file."""
        return os.path.join(self.localPkgDir(), f"{self.version}_file_manifest.xml")

    def local_mod_exists(self):
        """Check if the mod files exist locally."""
        return os.path.isfile(self.localPkgPath()) and os.path.isfile(self.localManifestPath())

    def get_latest_mod(self):
        """Download the mod ZIP file."""
        try:
            response = requests.get(RELEASE_URI, timeout=10)
            response.raise_for_status()
            return zipfile.ZipFile(io.BytesIO(response.content))
        except requests.exceptions.RequestException as err:
            print("Error downloading mod:", err)
            return None

    def mod_cleanup(self):
        """Remove the entire target directory and recreate it."""
        target_dir = self.localPkgDir()
        if os.path.isdir(target_dir):
            shutil.rmtree(target_dir)
        os.makedirs(target_dir, exist_ok=True)

    def install_mod(self, progress_callback):
        """Installs the mod and updates progress bar."""
        if self.mod_package is None:
            return "Failed to download mod."

        self.mod_cleanup()
        total_files = len(self.mod_package.namelist())

        for i, name in enumerate(self.mod_package.namelist()):
            mod_w_path = self.localPkgPath() if name.endswith('.pkg') else self.localManifestPath()
            with self.mod_package.open(name) as myfile:
                with open(mod_w_path, 'wb') as f:
                    f.write(myfile.read())

            progress_callback(int(((i + 1) / total_files) * 100))
            asyncio.sleep(0.05)  # Small delay for smoother updates

        return "Mod installation complete!"

    def restore_original_files(self, progress_callback):
        """Restores original game files."""
        self.mod_cleanup()
        try:
            response = requests.get(OG_FILES_URL, timeout=10)
            response.raise_for_status()
            with zipfile.ZipFile(io.BytesIO(response.content)) as og_zip:
                total_files = len(og_zip.namelist())
                for i, member in enumerate(og_zip.infolist()):
                    target_path = os.path.join(self.localPkgDir(), os.path.basename(member.filename))
                    os.makedirs(os.path.dirname(target_path), exist_ok=True)
                    if not member.is_dir():
                        with og_zip.open(member) as source, open(target_path, 'wb') as target:
                            target.write(source.read())

                    progress_callback(int(((i + 1) / total_files) * 100))
                    asyncio.sleep(0.05)

            return "Original files restored successfully!"
        except requests.exceptions.RequestException as err:
            print("Error restoring files:", err)
            return "Failed to restore original files."

# Initialize mod manager
mod_manager = ModManager(appData)

# Define Flet UI
def main(page: ft.Page):
    page.title = "Nuphillion Mod Manager"
    page.bgcolor = "#006064"
    page.window_width = 900
    page.window_height = 800
    page.vertical_alignment = ft.MainAxisAlignment.CENTER

    status_text = ft.Text("Welcome to Nuphillion Mod Manager!", color="white", size=16)
    progress_bar = ft.ProgressBar(width=500, value=0)

    async def update_progress(value):
        progress_bar.value = value / 100
        progress_bar.update()

    async def install_mod_click(e):
        status_text.value = "Installing mod..."
        status_text.update()
        progress_bar.value = 0
        progress_bar.update()

        def progress_callback(value):
            page.run_task(update_progress(value))

        result = await asyncio.to_thread(mod_manager.install_mod, progress_callback)
        status_text.value = result
        status_text.update()

    async def uninstall_mod_click(e):
        status_text.value = "Restoring original files..."
        status_text.update()
        progress_bar.value = 0
        progress_bar.update()

        def progress_callback(value):
            page.run_task(update_progress(value))

        result = await asyncio.to_thread(mod_manager.restore_original_files, progress_callback)
        status_text.value = result
        status_text.update()

    def check_status_click(e):
        if mod_manager.local_mod_exists():
            status_text.value = "Mod is installed and up-to-date!" if mod_manager.version == VERSION else "Mod is outdated. Update available."
        else:
            status_text.value = "Mod is not installed."
        status_text.update()

    def open_discord(e):
        import webbrowser
        webbrowser.open("https://discord.gg/NeTyqrvbeY")

    def create_button(text, on_click, color):
        return ft.ElevatedButton(text, on_click=on_click, bgcolor=color, color="white", width=250, height=50)

    buttons = ft.Column([
        create_button("Install Mod", install_mod_click, "#00796B"),
        create_button("Uninstall Mod", uninstall_mod_click, "#D32F2F"),
        create_button("Check Status", check_status_click, "#1976D2"),
        create_button("Open Discord", open_discord, "#6200EE"),
    ], spacing=10, alignment=ft.MainAxisAlignment.CENTER)

    page.add(
        ft.Column([
            ft.Text("Nuphillion Mod Manager", size=24, weight="bold", color="white"),
            status_text,
            progress_bar,
            buttons,
            ft.Text("Developed by CutesyThrower12", size=12, color="white")
        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    )

ft.app(target=main)
