import os
import subprocess
import sys

os.environ['GEMINI_API_KEY'] = 'AQ.Ab8RN6L4GPRVHH_G7pJreLSx4bztMbYu8oTCZSZjMfqE0TAfvg'
result = subprocess.run(['graphify', 'cluster-only', '.'], shell=True, capture_output=True, text=True)
print("STDOUT:")
print(result.stdout)
print("STDERR:")
print(result.stderr)
sys.exit(result.returncode)
