import flet as ft
import os
import shutil
import requests
import zipfile
import asyncio
import io
import sys
import time
import collections
from concurrent.futures import ThreadPoolExecutor
import subprocess  # <-- add this import

# Constants
VERSION = '1_11_2931_2'
VERSION_PTR = '1_11_2931_10'
RELEASE_URI = 'https://github.com/CutesyThrower12/Nuphillion/releases/download/vInDev/nuphillion.zip'
OG_FILES_URL = 'https://github.com/CutesyThrower12/HW2-Original-Files/releases/download/1.0/hw2ogfiles.zip'
HW2_HOGAN_PATH = "Packages\\Microsoft.HoganThreshold_8wekyb3d8bbwe\\LocalState"
UPDATER_RELEASE_URL = "https://github.com/TheDoctor200/NuphillionLauncher/releases/latest/download/NuphillionLauncher.exe"

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


def get_aumid(app_name_filter="Halo Wars 2"):
    # PowerShell command to list Start Menu apps
    ps_command = f'''
    Get-StartApps | Where-Object {{$_.Name -like "*{app_name_filter}*"}} | Select-Object -ExpandProperty AppID
    '''
    # Hide the PowerShell window by using creationflags
    CREATE_NO_WINDOW = 0x08000000
    result = subprocess.run(
        ["powershell", "-Command", ps_command],
        capture_output=True,
        text=True,
        creationflags=CREATE_NO_WINDOW
    )
    aumids = result.stdout.strip().splitlines()

    if not aumids:
        print(f"No app found with name containing '{app_name_filter}'")
        return None
    else:
        # Optionally choose the first match if there are several
        return aumids[0].strip()

def launch_app(aumid):
    try:
        subprocess.run(f'start explorer shell:appsfolder\\{aumid}', shell=True)
        print(f"Launched: {aumid}")
    except Exception as e:
        print(f"Failed to launch app: {e}")


def main(page: ft.Page):
    page.title = "Nuphillion Mod Manager"
    page.window_title = "Nuphillion Mod Manager"
    page.window_resizable = True
    page.window_center = True
    page.window_maximizable = True
    page.window_always_on_top = False
    page.bgcolor = "#006064"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.padding = 0

    ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
    bg_path = os.path.join(ASSETS_DIR, "holo_table.jpg")
    icon_path = os.path.join(ASSETS_DIR, "The_Vanquished.png")
    favicon_path = os.path.join(ASSETS_DIR, "favicon.ico")

    # Set window icon, app icon, and tray icon (if supported)
    if os.path.exists(favicon_path):
        page.window_icon = favicon_path
        page.icon = favicon_path
        try:
            page.tray_icon = favicon_path  # For Flet >=0.14.0, sets Windows tray/taskbar icon
        except Exception:
            pass

    # Get background image size
    # Dynamically determine background image size, fallback to 1920x1080 if not available
    bg_width, bg_height = 1500, 844  # fallback default
    if os.path.exists(bg_path):
        try:
            with Image.open(bg_path) as img:
                bg_width, bg_height = img.size
        except Exception:
            pass
    if os.path.exists(bg_path):
        try:
            from PIL import Image
            with Image.open(bg_path) as img:
                bg_width, bg_height = img.size
        except Exception:
            pass

    page.window_width = bg_width
    page.window_height = bg_height

    # Dynamic background image that always covers the full app background and resizes with window
    class DynamicBg(ft.Stack):
        def __init__(self):
            super().__init__()
            self.bg_img = ft.Image(
                src=bg_path,
                fit=ft.ImageFit.COVER,
                opacity=0.5,
                width=page.window_width,
                height=page.window_height
            )
            self.controls = [self.bg_img]

        def resize(self, width, height):
            self.bg_img.width = width
            self.bg_img.height = height
            self.update()  # Update the entire container, not just the image

    status_quote = ft.Text("Manage your Nuphillion mod install with ease", color="white", size=14, italic=True)
    status_label = ft.Text("Status:", color="white", size=18, weight="bold")
    progress_bar = ft.ProgressBar(width=500, value=0, color="#97E9E6")
    status_text = ft.Text("", color="white", size=16)

    # --- Bandwidth Graph State ---
    bandwidth_history = collections.deque(maxlen=60)  # last 60 samples (seconds)
    bandwidth_chart = ft.LineChart(
        data_series=[
            ft.LineChartData(
                data_points=[],
                stroke_width=3,
                color=ft.Colors.CYAN,  # Updated to Colors
                curved=True,
                stroke_cap_round=True,
            )
        ],
        min_y=0,
        max_y=10,
        width=300,
        height=80,
        left_axis=ft.ChartAxis(labels_size=30),
        bottom_axis=ft.ChartAxis(labels_size=20),
        tooltip_bgcolor=ft.Colors.BLUE_GREY_900,  # Updated to Colors
        expand=True,
        animate=True,
    )

    # --- Bandwidth State ---
    bandwidth_value = [0.0]  # Store last bandwidth in MB/s
    size_text = ft.Text("Downloaded: 0 MB", color="white", size=15)
    bandwidth_text = ft.Text("Speed: 0.00 MB/s", color="white", size=15)
    stats_label = ft.Text("Download Statistics:", color="white", size=16, weight="bold")

    VERSION_FILE = os.path.join(os.path.dirname(__file__), "version.txt")

    # --- Download/Install/Uninstall cancellation state ---
    install_task = {"task": None, "cancel_event": None}

    def quick_update():
        # Only update the UI, not the whole page (faster for small changes)
        status_text.update()
        progress_bar.update()
        size_text.update()
        bandwidth_text.update()

    async def install_mod_click(e):
        # Cancel any previous install if running
        if install_task["task"] and not install_task["task"].done():
            install_task["cancel_event"].set()
            await install_task["task"]

        cancel_event = asyncio.Event()
        install_task["cancel_event"] = cancel_event

        # Reset download statistics to zero
        size_text.value = "Downloaded: 0 MB"
        bandwidth_text.value = "Speed: 0.00 MB/s"
        quick_update()

        status_text.value = "Installing mod..."
        progress_bar.value = 0
        quick_update()

        last_time = [time.time()]
        last_bytes = [0]
        total_bytes = [0]

        async def download_file_with_bandwidth(url, callback):
            loop = asyncio.get_running_loop()
            with requests.get(url, stream=True, timeout=30) as r:
                r.raise_for_status()
                total = int(r.headers.get('content-length', 0))
                downloaded = 0
                chunk_size = 8192
                last_graph_update = time.time()
                with io.BytesIO() as f:
                    for chunk in r.iter_content(chunk_size=chunk_size):
                        if cancel_event.is_set():
                            return None  # Abort download
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            total_bytes[0] = downloaded
                            size_text.value = f"Downloaded: {downloaded / 1024 / 1024:.2f} MB"
                            now = time.time()
                            elapsed = now - last_time[0]
                            if elapsed > 0.5:
                                bandwidth = (downloaded - last_bytes[0]) / elapsed / 1024 / 1024
                                bandwidth_value[0] = bandwidth
                                bandwidth_text.value = f"Speed: {bandwidth:.2f} MB/s"
                                last_time[0] = now
                                last_bytes[0] = downloaded
                            quick_update()
                            await loop.run_in_executor(None, callback, chunk, total, downloaded)
                    size_text.value = f"Downloaded: {downloaded / 1024 / 1024:.2f} MB"
                    bandwidth_text.value = f"Speed: {bandwidth_value[0]:.2f} MB/s"
                    quick_update()
                    return f.getvalue()

        def progress_callback(value):
            progress_bar.value = value / 100
            quick_update()

        async def do_install():
            # Patch ModManager to use our custom downloader for bandwidth tracking
            async def patched_download_file(url):
                return await download_file_with_bandwidth(url, lambda *_: None)
            old_download_file = mod_manager._download_file
            mod_manager._download_file = patched_download_file

            result = await mod_manager.install_mod(progress_callback)
            if cancel_event.is_set():
                status_text.value = "Installation cancelled."
            else:
                status_text.value = result
            mod_manager._download_file = old_download_file  # Restore original
            quick_update()

        install_task["task"] = asyncio.create_task(do_install())
        await install_task["task"]

    async def uninstall_mod_click(e):
        # If install is running, cancel it and wait for it to finish before uninstalling
        if install_task["task"] and not install_task["task"].done():
            install_task["cancel_event"].set()
            await install_task["task"]

        # Reset download statistics to zero
        size_text.value = "Downloaded: 0 MB"
        bandwidth_text.value = "Speed: 0.00 MB/s"
        quick_update()

        status_text.value = "Restoring original files..."
        progress_bar.value = 0
        quick_update()
        def progress_callback(value):
            progress_bar.value = value / 100
            quick_update()
        result = await mod_manager.restore_original_files(progress_callback)
        status_text.value = result
        quick_update()

    async def update_app_click(e):
        # Ensure version.txt is always checked in the same directory as the running executable or script
        exe_dir = os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(__file__))
        VERSION_FILE = os.path.join(exe_dir, "version.txt")
        # Read local version
        local_version = None
        if os.path.exists(VERSION_FILE):
            with open(VERSION_FILE, "r", encoding="utf-8") as f:
                local_version = f.read().strip()
        else:
            local_version = "unknown"

        # Fetch latest version from GitHub releases
        import requests
        import webbrowser

        try:
            api_url = "https://api.github.com/repos/TheDoctor200/NuphillionLauncher/releases/latest"
            resp = requests.get(api_url, timeout=10)
            resp.raise_for_status()
            latest = resp.json()
            latest_version = latest.get("tag_name", "").lstrip("vV")
        except Exception as ex:
            status_text.value = f"Could not check latest version: {ex}"
            progress_bar.value = 0.0
            quick_update()
            return

        if local_version == latest_version:
            status_text.value = "You are currently on the latest launcher version"
            progress_bar.value = 1.0
            quick_update()
            return

        # Not latest, ask user
        status_text.value = f"New version available: {latest_version} (current: {local_version})"
        progress_bar.value = 0.5
        quick_update()

        # Show Yes/No selection
        def on_select(choice):
            page.dialog.open = False
            quick_update()
            if choice == "yes":
                status_text.value = "Downloading new version..."
                quick_update()
                webbrowser.open("https://github.com/TheDoctor200/NuphillionLauncher/releases/latest")
            else:
                status_text.value = "Update cancelled."
                quick_update()

        page.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Update Available"),
            content=ft.Text("Would you like to download the new version now?"),
            actions=[
                ft.TextButton("Yes", on_click=lambda e: on_select("yes")),
                ft.TextButton("No", on_click=lambda e: on_select("no")),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.dialog.open = True
        page.update()

    async def check_status_click(e):
        if mod_manager.local_mod_exists():
            status_text.value = "Mod is installed and up-to-date!" if mod_manager.version == VERSION else "Mod is outdated. Update available."
            progress_bar.value = 1.0
        else:
            status_text.value = "Mod is not installed."
            progress_bar.value = 0.0
        quick_update()

    def open_discord(e):
        import webbrowser
        webbrowser.open("https://discord.gg/NeTyqrvbeY")

    def create_button(text, on_click, color, icon=None):
        return ft.ElevatedButton(
            text,
            on_click=on_click,
            bgcolor=color,
            color="white",
            width=250,
            height=50,
            icon=icon,
            icon_color="white" if icon else None
        )

    async def launch_game_click(e):
        # Launch Halo Wars 2 (or other app) via AUMID
        try:
            app_name = "Halo Wars 2"
            aumid = get_aumid(app_name)
            if aumid:
                launch_app(aumid)
                status_text.value = f"Game launched! ({aumid})"
            else:
                status_text.value = f"Could not find app with name '{app_name}'"
        except Exception as ex:
            status_text.value = f"Failed to launch game: {ex}"
        page.update()

    buttons = ft.Column([
        create_button("Install Mod", install_mod_click, "#00796B", ft.Icons.DOWNLOAD),
        create_button("Uninstall Mod", uninstall_mod_click, "#D32F2F", ft.Icons.DELETE_FOREVER),
        create_button("Check Status", check_status_click, "#1976D2", ft.Icons.INFO),
        create_button("Update Launcher", update_app_click, "#FF9800", ft.Icons.UPGRADE),
        create_button("Open Discord", open_discord, "#6200EE", ft.Icons.CHAT),
    ], spacing=10, alignment=ft.MainAxisAlignment.CENTER)

    # Center UI elements vertically and horizontally
    content = ft.Container(
        content=ft.Column([
            ft.Text(
                "Nuphillion Mod Manager",
                size=24,
                weight="bold",
                color="white",
                text_align=ft.TextAlign.CENTER,
            ),
            status_quote,
            ft.Container(status_label, padding=ft.padding.only(top=24)),
            status_text,
            progress_bar,
            ft.Container(buttons, padding=ft.padding.only(top=8)),
            ft.Container(
                ft.Text("Developed by CutesyThrower12 and TheDoctor :)", size=12, color="white"),
                padding=ft.padding.only(top=10)
            ),
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER
        ),
        alignment=ft.alignment.center,
        padding=ft.padding.only(top=80),
    )

    stack_children = []
    if os.path.exists(bg_path):
        dynamic_bg = DynamicBg()
        stack_children.append(dynamic_bg)
        def on_resize(e):
            dynamic_bg.resize(page.window_width, page.window_height)
            page.update()  # Force the app to update on every resize
        page.on_resize = on_resize  # Ensures background resizes with window

    # Prepare icon if exists (ensure 'icon' is always defined)
    icon = None
    if os.path.exists(icon_path):
        icon = ft.Container(
            content=ft.Image(
                src=icon_path,
                width=80,
                height=80,
                fit=ft.ImageFit.CONTAIN,
            ),
            alignment=ft.alignment.top_left,
            padding=20,
        )

    stack_children.append(content)
    if icon:
        stack_children.append(icon)
        # Add bandwidth and size info under the icon (top left) with mica style
        stack_children.append(
            ft.Container(
                content=ft.Column([
                    stats_label,
                    size_text,
                    bandwidth_text,
                    ft.Container(
                        create_button("Launch Game", launch_game_click, "#43A047", ft.Icons.PLAY_ARROW),
                        padding=ft.padding.only(top=10)
                    ),
                    ft.Container(
                        ft.Image(
                            src=os.path.join(ASSETS_DIR, "HaloWars2Preview.gif"),
                            width=180,
                            height=120,
                            fit=ft.ImageFit.CONTAIN,
                            border_radius=18,
                        ),
                        padding=ft.padding.only(top=5, bottom=0),
                        alignment=ft.alignment.center,
                    )
                ], spacing=6),
                left=20,
                top=150,
                width=220,
                bgcolor=ft.Colors.with_opacity(0.35, ft.Colors.BLUE_GREY_900),
                border_radius=16,
                blur=20,
                shadow=ft.BoxShadow(
                    blur_radius=16,
                    color=ft.Colors.with_opacity(0.4, ft.Colors.BLACK),
                    spread_radius=2,
                    offset=ft.Offset(2, 4)
                ),
                padding=16,
            )
        )

    # Social links (below the stats/info box, separated by a divider)
    SOCIAL_LINKS = [
        ("ModDB", "https://www.moddb.com/", ft.Icons.LINK),
        ("YouTube", "https://youtube.com/", ft.Icons.YOUTUBE_SEARCHED_FOR),
        ("Discord", "https://discord.gg/NeTyqrvbeY", ft.Icons.CHAT),
        ("Twitter", "https://twitter.com/", ft.Icons.TRAVEL_EXPLORE),
    ]

    def open_social(url):
        import webbrowser
        webbrowser.open(url)

    # Add a divider and the social links row below the stats/info box
    stack_children.append(
        ft.Container(
            content=ft.Column([
                ft.Divider(height=24, thickness=2, color="#97E9E6"),  # Divider in dark color
                ft.Row(
                    [
                        ft.IconButton(
                            icon,
                            tooltip=name,
                            on_click=lambda e, url=url: open_social(url),
                            icon_size=32,
                            style=ft.ButtonStyle(
                                shape=ft.RoundedRectangleBorder(radius=12),
                                bgcolor={"": "#23272A"},
                                color={"": "#fff"},
                            ),
                        )
                        for name, url, icon in SOCIAL_LINKS
                    ],
                    alignment=ft.MainAxisAlignment.END,
                    spacing=8,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.END,
            ),
            left=20,
            top=470,  # Move both divider and social links further down
            width=220,
            bgcolor=None,
            padding=0,
        )
    )

    page.add(
        ft.Stack([
            *stack_children,
        ])
    )

ft.app(target=main)