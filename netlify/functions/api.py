import json
import sys
import os

# Add the parent directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from main import app
from mangum import Mangum

handler = Mangum(app, lifespan="off")