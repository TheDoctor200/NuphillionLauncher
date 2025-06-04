import subprocess
import sys
import os

def open_social_link(url):
    # Always open browser window hidden (no console)
    if sys.platform == "win32":
        CREATE_NO_WINDOW = 0x08000000
        subprocess.Popen(
            f'start "" "{url}"',
            shell=True,
            creationflags=CREATE_NO_WINDOW
        )
    else:
        import webbrowser
        webbrowser.open(url)
