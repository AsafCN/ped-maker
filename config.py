# config.py
import os
import logging
from logging import handlers


# deleteting last log when starting
with open ("logs/ped_creator.log", "w") as f:
    f.write("")

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Set the logging level to DEBUG
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/ped_creator.log"),
        logging.StreamHandler()
    ]
)

# Silence PIL's noisy debug logs
logging.getLogger('concurrent.futures').setLevel(logging.WARNING)
logging.getLogger('PIL').setLevel(logging.WARNING)
logging.getLogger('customtkinter').setLevel(logging.WARNING)

# Create your application logger
logger = logging.getLogger(__name__)

PURPLE = "#5d11c3"
HOVER_PURPLE = "#5057eb"

MALE_PATH = r"C:\Users\spkhn\Desktop\peds shop\new clothes\male"
FEMALE_PATH = r"C:\Users\spkhn\Desktop\peds shop\new clothes\female"
# TARGET_FOLDER = r"C:\Users\Assaf Cohen\Desktop\peds shop\output"

CATEGORY_PREFIXES = {
    "head": "head",
    "uppr": "uppr",
    "accs": "accs",
    "masks": "berd",
    "bags": "hand",
    "chains": "teef",
    "decals": "decl",
    "hairs": "hair",
    "pants": "lowr",
    "shirts": "jbib",
    "shoes": "feet",
    "under shirt": "accs",
    "vests": "task",
    "watches": "p_lwrist",
    "glasses": "p_eyes",  
    "hats": "p_head"  
}