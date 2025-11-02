from transposer_core import download_and_transpose
import sys

try:
    with open("urls.txt", "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip(): 
                continue
            
            parts = line.strip().split()
            if len(parts) < 2:
                print(f"Skipping invalid line: {line.strip()}")
                continue
            
            url, semi = parts[0], int(parts[1])
            print(f"\nProcessing: {url} ({semi:+} semitones)")
            download_and_transpose(url, semi)
except FileNotFoundError:
    print("Error: urls.txt not found")
    sys.exit(1)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)

