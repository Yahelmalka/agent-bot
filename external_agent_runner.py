import subprocess

def run_external_agent(task_text):
    try:
        result = subprocess.run(
            ["docker", "run", "--rm", "--network=none", "fake-external-agent", task_text],
            capture_output=True,
            text=True,
            encoding="utf-8",   # השורה החדשה
            timeout=60
        )
        if result.returncode == 0:
            return result.stdout
        else:
            return f"שגיאה בהרצת הכלי החיצוני: {result.stderr}"
    except subprocess.TimeoutExpired:
        return "הכלי החיצוני לקח יותר מדי זמן ונעצר."