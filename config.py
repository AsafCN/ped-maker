# config.py
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("ped_creator.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

PURPLE = "#5d11c3"
HOVER_PURPLE = "#5057eb"

MALE_PATH = r"C:\Users\Assaf Cohen\Desktop\peds shop\new clothes\male"
FEMALE_PATH = r"C:\Users\Assaf Cohen\Desktop\peds shop\new clothes\female"
TARGET_FOLDER = r"C:\Users\Assaf Cohen\Desktop\peds shop\output"

STEPS = [
    "name", "accs", "bags", "chains", "decals", "glasses", "hairs", "hats", "masks",
    "pants", "shirts", "shoes", "under shirt", "vests", "watches", "done"
]

CATEGORY_PREFIXES = {
    "bags": "hand",
    "accs": "accs",
    "chains": "teef",
    "decals": "decl",
    "glasses": "p_eyes",
    "hairs": "hair",
    "hats": "p_head",
    "masks": "berd",
    "pants": "lowr",
    "shirts": "jbib",
    "shoes": "feet",
    "under shirt": "accs",
    "vests": "task",
    "watches": "p_lwrist"
}