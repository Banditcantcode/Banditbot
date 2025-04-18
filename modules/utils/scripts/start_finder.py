import os
import subprocess
import sys
import time


current_dir = os.path.dirname(os.path.abspath(__file__))
print(f"Current directory: {current_dir}")


finder_path = os.path.join(current_dir, "finder.py")
print(f"Finder path: {finder_path}")


if not os.path.exists(finder_path):
    print(f"Error: {finder_path} does not exist!")
    sys.exit(1)

print("Starting finder.py with full debug output...")


process = subprocess.Popen(
    ["python3", finder_path],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    universal_newlines=True,
    bufsize=1
)


try:
    for line in process.stdout:
        print(line, end='')
        sys.stdout.flush()
except KeyboardInterrupt:
    print("Process interrupted by user.")
    process.kill()

# Wait for process to complete
process.wait()
print(f"Process exited with code {process.returncode}") 