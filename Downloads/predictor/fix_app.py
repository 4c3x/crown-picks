import subprocess
import sys

# Extract clean file from git
result = subprocess.run(
    ['git', 'show', 'f7b9685:Downloads/predictor/app.py'],
    capture_output=True,
    cwd='C:/Users/HP'
)

if result.returncode == 0:
    clean_data = result.stdout
    null_byte = b'\x00'
    print(f"Extracted - Size: {len(clean_data)}, Nulls: {clean_data.count(null_byte)}")
    
    # Write to file
    with open('C:/Users/HP/Downloads/predictor/app.py', 'wb') as f:
        f.write(clean_data)
    
    print("Wrote to app.py")
    
    # Verify
    with open('C:/Users/HP/Downloads/predictor/app.py', 'rb') as f:
        verify = f.read()
    print(f"Verified - Size: {len(verify)}, Nulls: {verify.count(null_byte)}")
else:
    print(f"Error: {result.stderr.decode()}")
    sys.exit(1)
