import json
import xml.etree.ElementTree as ET
import logging
import os

# Clear the log file before starting
if os.path.exists("logs/ymt_generator.log"):
    with open("logs/ymt_generator.log", "w") as f:
        f.write("")

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Set logging level to INFO
    format="%(asctime)s - %(levelname)s - %(message)s",  # Log format
    handlers=[
        logging.FileHandler("logs/ymt_generator.log"),  # Log to a file
        logging.StreamHandler()  # Log to the console
    ]
)

# Category prefixes mapping
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
    "glasses": "p_eyes",  # Fixed mapping for glasses
    "hats": "p_head"  # Fixed mapping for hats
}

# Fixed component slot order
COMPONENT_SLOTS = [
    "head",  # Slot 1
    "berd",  # Slot 2
    "hair",  # Slot 3
    "uppr",  # Slot 4
    "lowr",  # Slot 5
    "hand",  # Slot 6
    "feet",  # Slot 7
    "teef",  # Slot 8
    "accs",  # Slot 9
    "task",  # Slot 10
    "decl",  # Slot 11
    "jbib"   # Slot 12
]

# Function to add indentation and line breaks to the XML
def indent(elem, level=0):
    indent_str = "  "  # Two spaces per level
    i = "\n" + level * indent_str
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + indent_str
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent(elem, level + 1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

# Load the JSON data
try:
    with open("ymt-saved_selections.json", "r") as file:
        data = json.load(file)
    logging.info("JSON file loaded successfully.")
except Exception as e:
    logging.error(f"Failed to load JSON file: {e}")
    exit(1)

# Extract the ped data
ped_data = data["ig_test"]
logging.info("Ped data extracted from JSON.")

# Create the root element
root = ET.Element("CPedVariationInfo")
logging.info("Root XML element created.")

# Add global flags
ET.SubElement(root, "bHasTexVariations", value="true")
ET.SubElement(root, "bHasDrawblVariations", value="true")
ET.SubElement(root, "bHasLowLODs", value="false")
ET.SubElement(root, "bIsSuperLOD", value="false")
logging.info("Global flags added to XML.")

# Generate availComp dynamically
avail_comp = ET.SubElement(root, "availComp")
avail_comp_list = []

# Track the current ID
current_id = 0  # Start from 0

# Iterate through the fixed component slots
for slot in COMPONENT_SLOTS:
    # Find the corresponding category in the JSON data
    category = next((k for k, v in CATEGORY_PREFIXES.items() if v == slot), None)
    if category and category in ped_data:
        # If the component is present, add its ID
        avail_comp_list.append(str(current_id))
        current_id += 1
        logging.info(f"Component '{slot}' (category: {category}) found. Assigned ID: {current_id - 1}")
    else:
        # If the component is not present, add 255
        avail_comp_list.append("255")
        logging.info(f"Component '{slot}' not found. Assigned ID: 255")

# Join the list into a space-separated string
avail_comp.text = " ".join(avail_comp_list)
logging.info(f"Generated availComp: {avail_comp.text}")

# Add component data
comp_data = ET.SubElement(root, "aComponentData3", itemType="CPVComponentData")
logging.info("Component data section added to XML.")

# Function to add component items
def add_component_item(component_id, textures):
    item = ET.SubElement(comp_data, "Item")
    # Calculate total number of textures for the category
    total_textures = sum(len(textures_list) for textures_list in textures.values())
    ET.SubElement(item, "numAvailTex", value=str(total_textures))  # Total textures for the category
    drawbl_data = ET.SubElement(item, "aDrawblData3", itemType="CPVDrawblData")
    
    for texture_id, textures_list in textures.items():
        drawbl_item = ET.SubElement(drawbl_data, "Item")
        ET.SubElement(drawbl_item, "propMask", value="1")
        ET.SubElement(drawbl_item, "numAlternatives", value="0")
        tex_data = ET.SubElement(drawbl_item, "aTexData", itemType="CPVTextureData")
        
        for texture in textures_list:
            tex_item = ET.SubElement(tex_data, "Item")
            ET.SubElement(tex_item, "texId", value="0")
            ET.SubElement(tex_item, "distribution", value="255")
        
        cloth_data = ET.SubElement(drawbl_item, "clothData")
        ET.SubElement(cloth_data, "ownsCloth", value="false")
    
    logging.info(f"Added component item with ID: {component_id} and {total_textures} textures.")

# Add components from JSON in the order of COMPONENT_SLOTS
for slot in COMPONENT_SLOTS:
    # Find the corresponding category in the JSON data
    category = next((k for k, v in CATEGORY_PREFIXES.items() if v == slot), None)
    if category and f"{category}_textures" in ped_data:
        textures = ped_data[f"{category}_textures"]
        add_component_item(slot, textures)

# Add component information
comp_infos = ET.SubElement(root, "compInfos", itemType="CComponentInfo")
logging.info("Component info section added to XML.")

for category, textures in ped_data.items():
    if "_textures" not in category and category != "name":
        for component_id in ped_data[category]:
            comp_info = ET.SubElement(comp_infos, "Item")
            ET.SubElement(comp_info, "hash_2FD08CEF").text = "none"
            ET.SubElement(comp_info, "hash_FC507D28").text = "none"
            ET.SubElement(comp_info, "hash_07AE529D").text = "0 0 0 0 0"
            ET.SubElement(comp_info, "flags", value="0")
            ET.SubElement(comp_info, "inclusions").text = "0"
            ET.SubElement(comp_info, "exclusions").text = "0"
            ET.SubElement(comp_info, "hash_6032815C").text = "PV_COMP_HEAD"
            ET.SubElement(comp_info, "hash_7E103C8B", value="0")
            ET.SubElement(comp_info, "hash_D12F579D", value=str(component_id))
            ET.SubElement(comp_info, "hash_FA1F27BF", value="0")
            logging.info(f"Added component info for ID: {component_id} in category: {category}")

# Add prop information
prop_info = ET.SubElement(root, "propInfo")
ET.SubElement(prop_info, "numAvailProps", value=str(len(ped_data.get("glasses", [])) + len(ped_data.get("hats", [])) + len(ped_data.get("masks", []))))

# Function to add prop items
def add_prop_item(prop_id, textures, category_prefix):
    prop_item = ET.SubElement(prop_meta_data, "Item")
    ET.SubElement(prop_item, "audioId").text = "none"
    ET.SubElement(prop_item, "expressionMods").text = "0 0 0 0 0"
    tex_data = ET.SubElement(prop_item, "texData", itemType="CPedPropTexData")
    
    for texture in textures:
        tex_item = ET.SubElement(tex_data, "Item")
        ET.SubElement(tex_item, "inclusions").text = "0"
        ET.SubElement(tex_item, "exclusions").text = "0"
        ET.SubElement(tex_item, "texId", value="0")
        ET.SubElement(tex_item, "inclusionId", value="0")
        ET.SubElement(tex_item, "exclusionId", value="0")
        ET.SubElement(tex_item, "distribution", value="255")
    
    ET.SubElement(prop_item, "renderFlags")
    ET.SubElement(prop_item, "propFlags", value="0")
    ET.SubElement(prop_item, "flags", value="0")
    ET.SubElement(prop_item, "anchorId", value="0")
    ET.SubElement(prop_item, "propId", value=str(prop_id))
    ET.SubElement(prop_item, "hash_AC887A91", value="0")
    
    logging.info(f"Added prop item with ID: {prop_id} and {len(textures)} textures for category: {category_prefix}.")

# Add props from JSON
prop_meta_data = ET.SubElement(prop_info, "aPropMetaData", itemType="CPedPropMetaData")
for category, textures in ped_data.items():
    if "_textures" in category:
        category_prefix = CATEGORY_PREFIXES.get(category.replace("_textures", ""), "unknown")
        for texture_id, textures_list in textures.items():
            add_prop_item(texture_id, textures_list, category_prefix)

# Add anchors
anchors = ET.SubElement(prop_info, "aAnchors", itemType="CAnchorProps")
anchor_item = ET.SubElement(anchors, "Item")
ET.SubElement(anchor_item, "props").text = "1 4 6"  # Dynamic props text (to be fixed)
ET.SubElement(anchor_item, "anchor").text = "ANCHOR_HEAD"
logging.info("Anchors added to XML.")

# Add DLC name
ET.SubElement(root, "dlcName")
logging.info("DLC name added to XML.")

# Add indentation and line breaks to the XML
indent(root)
logging.info("XML indentation and line breaks added.")

# Create the XML tree and write to file
try:
    tree = ET.ElementTree(root)
    tree.write("output.ymt.xml", encoding="utf-8", xml_declaration=True)
    logging.info("XML file written successfully: output.ymt.xml")
except Exception as e:
    logging.error(f"Failed to write XML file: {e}")