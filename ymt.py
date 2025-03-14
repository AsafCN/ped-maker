import xml.etree.ElementTree as ET
import subprocess
import logging
import json
import sys
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

# Function to create XML root and global flags
def create_root():
    root = ET.Element("CPedVariationInfo")
    logging.info("Root XML element created.")

    # Add global flags
    ET.SubElement(root, "bHasTexVariations", value="true")
    ET.SubElement(root, "bHasDrawblVariations", value="true")
    ET.SubElement(root, "bHasLowLODs", value="false")
    ET.SubElement(root, "bIsSuperLOD", value="false")
    logging.info("Global flags added to XML.")

    return root

# Function to generate availComp dynamically
def generate_avail_comp(root, ped_data):
    avail_comp = ET.SubElement(root, "availComp")
    avail_comp_list = []
    current_id = 0  # Start from 0

    for slot in COMPONENT_SLOTS:
        category = next((k for k, v in CATEGORY_PREFIXES.items() if v == slot), None)
        if category and category in ped_data:
            avail_comp_list.append(str(current_id))
            current_id += 1
            logging.info(f"Component '{slot}' (category: {category}) found. Assigned ID: {current_id - 1}")
        else:
            avail_comp_list.append("255")
            logging.info(f"Component '{slot}' not found. Assigned ID: 255")

    avail_comp.text = " ".join(avail_comp_list)
    logging.info(f"Generated availComp: {avail_comp.text}")

# Function to add component items
def add_component_item(comp_data, component_id, textures):
    item = ET.SubElement(comp_data, "Item")
    total_textures = sum(len(textures_list) for textures_list in textures.values())
    ET.SubElement(item, "numAvailTex", value=str(total_textures))
    drawbl_data = ET.SubElement(item, "aDrawblData3", itemType="CPVDrawblData")

    for texture_id, textures_list in textures.items():
        drawbl_item = ET.SubElement(drawbl_data, "Item")
        
        # Check if any texture name in the list contains "_uni"
        has_uni = any("_uni" in texture_name for texture_name in textures_list)
        prop_mask_value = "1" if has_uni else "17"
        
        ET.SubElement(drawbl_item, "propMask", value=prop_mask_value)
        ET.SubElement(drawbl_item, "numAlternatives", value="0")
        tex_data = ET.SubElement(drawbl_item, "aTexData", itemType="CPVTextureData")

        for texture_index, texture in enumerate(textures_list):
            tex_item = ET.SubElement(tex_data, "Item")
            ET.SubElement(tex_item, "texId", value="0" if "_uni" in texture else "1")
            ET.SubElement(tex_item, "distribution", value="255")

        cloth_data = ET.SubElement(drawbl_item, "clothData")
        ET.SubElement(cloth_data, "ownsCloth", value="false")

    logging.info(f"Added component item with ID: {component_id} and {total_textures} textures.")

# Function to add component data
def add_component_data(root, ped_data):
    comp_data = ET.SubElement(root, "aComponentData3", itemType="CPVComponentData")
    logging.info("Component data section added to XML.")

    for slot in COMPONENT_SLOTS:
        category = next((k for k, v in CATEGORY_PREFIXES.items() if v == slot), None)
        if category and f"{category}_textures" in ped_data:
            textures = ped_data[f"{category}_textures"]
            add_component_item(comp_data, slot, textures)

def add_component_info(root, ped_data):
    comp_infos = ET.SubElement(root, "compInfos", itemType="CComponentInfo")
    logging.info("Component info section added to XML.")

    # Mapping of component categories to their respective IDs
    COMPONENT_IDS = {
        "head": 0,
        "berd": 1,
        "hair": 2,
        "uppr": 3,
        "lowr": 4,
        "hand": 5,
        "feet": 6,
        "teef": 7,
        "accs": 8,
        "task": 9,
        "decl": 10,
        "jbib": 11
    }

    # Create a list to store all component info items
    component_info_items = []

    for category, textures in ped_data.items():
        if "_textures" not in category and category != "name":
            # Get the component ID based on the category
            component_id = COMPONENT_IDS.get(CATEGORY_PREFIXES.get(category, ""), -1)
            if component_id == -1:
                logging.warning(f"Unknown category: {category}. Skipping component info.")
                continue

            # Get the drawable indices for this category
            drawable_indices = sorted(ped_data[f"{category}_textures"].keys(), key=lambda x: int(x))

            for drawable_index in drawable_indices:
                # Create a dictionary to store the component info
                component_info = {
                    "component_id": component_id,
                    "drawable_index": drawable_index
                }
                component_info_items.append(component_info)

    # Sort the component info items by component ID and drawable index
    component_info_items.sort(key=lambda x: (x["component_id"], int(x["drawable_index"])))

    # Add the sorted component info items to the XML
    for item in component_info_items:
        comp_info = ET.SubElement(comp_infos, "Item")
        ET.SubElement(comp_info, "hash_2FD08CEF").text = "none"
        ET.SubElement(comp_info, "hash_FC507D28").text = "none"
        ET.SubElement(comp_info, "hash_07AE529D").text = "0 0 0 0 0"
        ET.SubElement(comp_info, "flags", value="0")
        ET.SubElement(comp_info, "inclusions").text = "0"
        ET.SubElement(comp_info, "exclusions").text = "0"
        ET.SubElement(comp_info, "hash_6032815C").text = "PV_COMP_HEAD"
        ET.SubElement(comp_info, "hash_7E103C8B", value="0")

        # Set component ID (infoHash_D12F579D)
        ET.SubElement(comp_info, "hash_D12F579D", value=str(item["component_id"]))

        # Set drawable index (infoHash_FA1F27BF)
        ET.SubElement(comp_info, "hash_FA1F27BF", value=str(item["drawable_index"]))

        logging.info(f"Added component info for component ID: {item['component_id']}, drawable index: {item['drawable_index']}")

# Function to add props and anchors
def add_props_and_anchors(root, ped_data):
    # Create the propInfo section
    prop_info = ET.SubElement(root, "propInfo")
    
    # Add numAvailProps directly under propInfo
    total_props = 0
    ET.SubElement(prop_info, "numAvailProps", value=str(total_props))  # Placeholder, will be updated later

    # Create the prop metadata section
    prop_meta_data = ET.SubElement(prop_info, "aPropMetaData", itemType="CPedPropMetaData")
    
    # Create the anchors section
    anchors = ET.SubElement(prop_info, "aAnchors", itemType="CAnchorProps")

    # Define the mapping between JSON categories and prop prefixes
    PROP_CATEGORIES = {
        "hats": "p_head",       # p_head maps to "hats" in JSON
        "glasses": "p_eyes",    # p_eyes maps to "glasses" in JSON
        "ears": "p_ears",       # p_ears maps to "ears" in JSON
        "watches": "p_lwrist",  # p_lwrist maps to "watches" in JSON
    }

    # Add props for each category
    for json_category, prop_prefix in PROP_CATEGORIES.items():
        if json_category in ped_data and f"{json_category}_textures" in ped_data:
            textures = ped_data[f"{json_category}_textures"]
            for texture_id, textures_list in textures.items():
                # Ensure the correct prop_prefix is passed
                add_prop_item(prop_meta_data, texture_id, textures_list, prop_prefix)
                total_props += 1

    # Update the numAvailProps value
    prop_info.find("numAvailProps").set("value", str(total_props))

    # Add anchors for each prop category
    for json_category, prop_prefix in PROP_CATEGORIES.items():
        if json_category in ped_data and f"{json_category}_textures" in ped_data:
            anchor_item = ET.SubElement(anchors, "Item")
            # Generate the props text based on the number of textures for each drawable
            props_text = " ".join(str(len(textures_list)) for textures_list in ped_data[f"{json_category}_textures"].values())
            ET.SubElement(anchor_item, "props").text = props_text
            
            # Fix the anchor naming
            if prop_prefix == "p_lwrist":
                anchor_name = "ANCHOR_LEFT_WRIST"
            else:
                anchor_name = f"ANCHOR_{prop_prefix.upper()}".replace("_P", "")
            
            ET.SubElement(anchor_item, "anchor").text = anchor_name
            logging.info(f"Added anchor for {prop_prefix} with props: {props_text}")

# Function to add prop items
def add_prop_item(prop_meta_data, prop_id, textures, prop_prefix):
    prop_item = ET.SubElement(prop_meta_data, "Item")
    ET.SubElement(prop_item, "audioId").text = "none"
    ET.SubElement(prop_item, "expressionMods").text = "0 0 0 0 0"
    tex_data = ET.SubElement(prop_item, "texData", itemType="CPedPropTexData")

    for texture_index, texture in enumerate(textures):
        tex_item = ET.SubElement(tex_data, "Item")
        ET.SubElement(tex_item, "inclusions").text = "0"
        ET.SubElement(tex_item, "exclusions").text = "0"
        ET.SubElement(tex_item, "texId", value="0" if "_uni" in texture else "1") # Dynamic texId based on texture index
        ET.SubElement(tex_item, "inclusionId", value="0")
        ET.SubElement(tex_item, "exclusionId", value="0")
        ET.SubElement(tex_item, "distribution", value="255")

    ET.SubElement(prop_item, "renderFlags")
    ET.SubElement(prop_item, "propFlags", value="0")
    ET.SubElement(prop_item, "flags", value="0")
    
    # Set anchorId based on prop_prefix
    if prop_prefix == "p_eyes":
        anchor_id = "1"
    elif prop_prefix == "p_ears":
        anchor_id = "2"
    elif prop_prefix == "p_lwrist":
        anchor_id = "6" 
    else:
        anchor_id = "0" 
    
    ET.SubElement(prop_item, "anchorId", value=anchor_id)
    ET.SubElement(prop_item, "propId", value=str(prop_id))
    ET.SubElement(prop_item, "hash_AC887A91", value="0")

    logging.info(f"Added prop item with ID: {prop_id} and {len(textures)} textures for category: {prop_prefix}.")

# Function to convert XML to YMT using an external tool
def convert_xml_to_ymt(xml_file, ymt_file):
    try:
        # Replace 'XmlToYmtConverter.exe' with the actual path to your C# executable
        subprocess.run(["ymtexe/XmlToYmtConverter.exe", xml_file, ymt_file], check=True)
        logging.info(f"Successfully converted {xml_file} to {ymt_file}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to convert XML to YMT: {e}")

# Main function to generate the XML
def generate_xml(ped_data, ped_name):
    # Create XML root
    root = create_root()

    # Generate availComp
    generate_avail_comp(root, ped_data)

    # Add component data
    add_component_data(root, ped_data)

    # Add component info
    add_component_info(root, ped_data)

    # Add props and anchors
    add_props_and_anchors(root, ped_data)

    # Add DLC name
    dlc_name = ET.SubElement(root, "dlcName")
    dlc_name.text = ""  # Ensure it's empty 
    ET.tostring(root, encoding="unicode")
    logging.info("DLC name added to XML.")

    # Add indentation and line breaks to the XML
    indent(root)
    logging.info("XML indentation and line breaks added.")

    # Write XML to a temporary file
    temp_xml_file = f"{ped_name}.temp.xml"
    try:
        tree = ET.ElementTree(root)
        with open(temp_xml_file, "wb") as f:  # Open in binary mode
            f.write(b'\xef\xbb\xbf')  # Write the UTF-8 BOM
            tree.write(f, encoding="utf-8", xml_declaration=True)
        logging.info(f"Temporary XML file written successfully: {temp_xml_file}")
    except Exception as e:
        logging.error(f"Failed to write temporary XML file: {e}")
        return

    # Convert the temporary XML file to YMT
    ymt_file = f"{ped_name}.ymt"
    convert_xml_to_ymt(temp_xml_file, ymt_file)

    # Clean up the temporary XML file
    try:
        os.remove(temp_xml_file)
        logging.info(f"Temporary XML file removed: {temp_xml_file}")
    except Exception as e:
        logging.error(f"Failed to remove temporary XML file: {e}")

# Function to load JSON file for testing
def load_json_file(json_file):
    try:
        with open(json_file, "r") as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Failed to load JSON file: {e}")
        return None
    
# Run the script
if __name__ == "__main__":
    # Load JSON file for testing
    json_file = "ymt-saved_selections.json"
    ped_data = load_json_file(json_file)
    
    if ped_data:
        # Generate XML for each ped in the JSON file
        for ped_name, ped_info in ped_data.items():
            generate_xml(ped_info, ped_name)
    else:
        print("Failed to load JSON file. Exiting.")
        sys.exit()