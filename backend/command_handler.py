import subprocess

def run_command(command):
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.stdout or result.stderr
    except Exception as e:
        return f"Error running command: {str(e)}"
