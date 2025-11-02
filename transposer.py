import sys
from transposer_core import download_and_transpose

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python transposer.py <YouTube_URL> <semitones>")
        print("Example: python transposer.py https://youtu.be/xxxx -2")
        sys.exit(1)
    
    download_and_transpose(sys.argv[1], int(sys.argv[2]))
