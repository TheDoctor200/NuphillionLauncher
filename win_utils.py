import subprocess

def get_aumid(app_name_filter="Halo Wars 2"):
    ps_command = f'''
    Get-StartApps | Where-Object {{$_.Name -like "*{app_name_filter}*"}} | Select-Object -ExpandProperty AppID
    '''
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
        return aumids[0].strip()

def launch_app(aumid):
    try:
        subprocess.run(
            f'start explorer shell:appsfolder\\{aumid}',
            shell=True,
            creationflags=0x08000000  # Always hide window
        )
        print(f"Launched: {aumid}")
    except Exception as e:
        print(f"Failed to launch app: {e}")
