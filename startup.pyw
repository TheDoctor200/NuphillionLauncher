import subprocess

def get_aumid(app_name_filter="Halo Wars 2"):
    # PowerShell command to list Start Menu apps
    ps_command = f'''
    Get-StartApps | Where-Object {{$_.Name -like "*{app_name_filter}*"}} | Select-Object -ExpandProperty AppID
    '''
    result = subprocess.run(["powershell", "-Command", ps_command], capture_output=True, text=True)
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

# Main flow
if __name__ == "__main__":
    app_name = "Halo Wars 2"
    aumid = get_aumid(app_name)
    if aumid:
        launch_app(aumid)

