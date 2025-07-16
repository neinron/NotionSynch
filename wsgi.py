import os
import sys

# Add the parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the Flask app from the source file
from notion_to_ics import app

if __name__ == "__main__":
    try:
        app.run()
    except Exception as e:
        print(f"An error occurred: {e}")