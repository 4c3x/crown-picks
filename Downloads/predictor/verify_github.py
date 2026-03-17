import subprocess

# Check what's on GitHub now
result = subprocess.run(
    ['git', 'show', 'HEAD:Downloads/predictor/app.py'],
    capture_output=True,
    cwd='C:/Users/HP'
)

if result.returncode == 0:
    data = result.stdout
    null_byte = b'\x00'
    print(f"GitHub HEAD - Size: {len(data)}, Nulls: {data.count(null_byte)}")
    
    # Also check it starts correctly
    first_line = data.split(b'\n')[0].decode('utf-8', errors='ignore')
    print(f"First line: {first_line[:60]}")
else:
    print(f"Error: {result.stderr.decode()}")
