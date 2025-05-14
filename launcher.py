import flet as ft
import os
import shutil
import requests
import zipfile
import asyncio
import io
from concurrent.futures import ThreadPoolExecutor

# Constants
VERSION = '1_11_2931_2'
VERSION_PTR = '1_11_2931_10'
RELEASE_URI = 'https://github.com/CutesyThrower12/Nuphillion/releases/download/vInDev/nuphillion.zip'
OG_FILES_URL = 'https://github.com/CutesyThrower12/HW2-Original-Files/releases/download/1.0/hw2ogfiles.zip'
HW2_HOGAN_PATH = "Packages\\Microsoft.HoganThreshold_8wekyb3d8bbwe\\LocalState"

appData = os.environ.get('LOCALAPPDATA')
if not appData:
    raise RuntimeError("Unable to find LOCALAPPDATA.")


class ModManager:
    def __init__(self, appData):
        self.localStateDir = os.path.join(appData, HW2_HOGAN_PATH)
        self.version = VERSION
        if os.path.isdir(self.localPkgDir(VERSION_PTR)):
            self.version = VERSION_PTR
        self._executor = ThreadPoolExecutor(max_workers=1)

    def localPkgDir(self, version=None):
        return os.path.join(self.localStateDir, f"GTS\\{version or self.version}_active")

    def localPkgPath(self):
        return os.path.join(self.localPkgDir(), 'NuphillionMod.pkg')

    def localManifestPath(self):
        return os.path.join(self.localPkgDir(), f"{self.version}_file_manifest.xml")

    def local_mod_exists(self):
        return os.path.isfile(self.localPkgPath()) and os.path.isfile(self.localManifestPath())

    def ensure_directories(self):
        """Ensure all required directories exist"""
        os.makedirs(self.localStateDir, exist_ok=True)
        gts_path = os.path.join(self.localStateDir, "GTS")
        os.makedirs(gts_path, exist_ok=True)
        os.makedirs(self.localPkgDir(), exist_ok=True)

    def mod_cleanup(self):
        """Clean up and prepare directories for mod installation"""
        try:
            self.ensure_directories()
            target_dir = self.localPkgDir()
            if os.path.isdir(target_dir):
                shutil.rmtree(target_dir)
            os.makedirs(target_dir, exist_ok=True)
        except Exception as e:
            print(f"Directory creation error: {e}")
            raise

    async def _download_file(self, url):
        try:
            response = await asyncio.get_running_loop().run_in_executor(
                self._executor,
                lambda: requests.get(url, timeout=10, stream=True)
            )
            response.raise_for_status()
            return response.content
        except Exception as e:
            print(f"Download error: {e}")
            return None

    async def install_mod(self, progress_callback):
        try:
            self.ensure_directories()
            progress_callback(0)
            content = await self._download_file(RELEASE_URI)
            if not content:
                return "Failed to download mod."

            progress_callback(20)
            
            self.mod_cleanup()
            with zipfile.ZipFile(io.BytesIO(content)) as mod_zip:
                # Get only .pkg and .xml files
                files_to_extract = [f for f in mod_zip.namelist() 
                                  if f.endswith('.pkg') or f.endswith('.xml')]
                
                if not files_to_extract:
                    return "Invalid mod package: No valid files found"

                total_files = len(files_to_extract)
                for i, name in enumerate(files_to_extract):
                    # Map files to correct names
                    if name.endswith('.pkg'):
                        target_path = self.localPkgPath()
                    else:
                        target_path = self.localManifestPath()

                    # Extract file
                    with mod_zip.open(name) as source, open(target_path, 'wb') as target:
                        shutil.copyfileobj(source, target)
                    
                    progress = 20 + int((i + 1) / total_files * 80)
                    progress_callback(progress)

            if not self.local_mod_exists():
                return "Installation failed: Files not properly installed"

            return "Mod installation complete!"
        except Exception as e:
            print(f"Installation error: {e}")
            return f"Installation failed: {str(e)}"

    async def restore_original_files(self, progress_callback):
        try:
            progress_callback(0)
            content = await self._download_file(OG_FILES_URL)
            if not content:
                return "Failed to download original files."

            progress_callback(20)
            
            self.mod_cleanup()
            with zipfile.ZipFile(io.BytesIO(content)) as og_zip:
                total_files = len(og_zip.namelist())
                for i, member in enumerate(og_zip.infolist()):
                    if member.is_dir():
                        continue
                    target_path = os.path.join(self.localPkgDir(), os.path.basename(member.filename))
                    with og_zip.open(member) as source, open(target_path, 'wb') as target:
                        target.write(source.read())
                    progress = 20 + int((i + 1) / total_files * 80)
                    progress_callback(progress)

            return "Original files restored successfully!"
        except Exception as e:
            print(f"Restore error: {e}")
            return f"Restore failed: {str(e)}"


mod_manager = ModManager(appData)


def main(page: ft.Page):
    page.title = "Nuphillion Mod Manager"
    page.window_title = "Nuphillion Mod Manager"
    page.bgcolor = "#006064"
    page.window_width = 900
    page.window_height = 800
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.padding = 0

    # Background image
    ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
    bg_path = os.path.join(ASSETS_DIR, "holo_table.jpg")
    icon_path = os.path.join(ASSETS_DIR, "The_Vanquished.png")

    # Prepare icon if exists
    icon = None
    if os.path.exists(icon_path):
        icon = ft.Container(
            content=ft.Image(src=icon_path, width=64, height=64),
            alignment=ft.alignment.top_right,
            padding=20,
        )

    # Main content column
    status_text = ft.Text("Welcome to Nuphillion Mod Manager!", color="white", size=16)
    progress_bar = ft.ProgressBar(width=500, value=0)

    def update_progress_sync(value):
        progress_bar.value = value / 100
        page.update()

    async def install_mod_click(e):
        status_text.value = "Installing mod..."
        progress_bar.value = 0
        page.update()
        def progress_callback(value):
            progress_bar.value = value / 100
            page.update()
        result = await mod_manager.install_mod(progress_callback)
        status_text.value = result
        page.update()

    async def uninstall_mod_click(e):
        status_text.value = "Restoring original files..."
        progress_bar.value = 0
        page.update()
        def progress_callback(value):
            progress_bar.value = value / 100
            page.update()
        result = await mod_manager.restore_original_files(progress_callback)
        status_text.value = result
        page.update()

    def check_status_click(e):
        if mod_manager.local_mod_exists():
            status_text.value = "Mod is installed and up-to-date!" if mod_manager.version == VERSION else "Mod is outdated. Update available."
        else:
            status_text.value = "Mod is not installed."
        page.update()

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

    content = ft.Column([
        ft.Text("Nuphillion Mod Manager", size=24, weight="bold", color="white"),
        status_text,
        progress_bar,
        buttons,
        ft.Text("Developed by CutesyThrower12", size=12, color="white")
    ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)

    # Stack background, content, and icon
    stack_children = []
    if os.path.exists(bg_path):
        stack_children.append(
            ft.Image(
                src=bg_path,
                width=page.window_width,
                height=page.window_height,
                fit=ft.ImageFit.COVER,
                opacity=0.7
            )
        )
    stack_children.append(content)
    if icon:
        stack_children.append(icon)

    page.add(
        ft.Stack(stack_children)
    )

ft.app(target=main)
