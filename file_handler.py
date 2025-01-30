import os
import shutil
import logging
from config import *

logger = logging.getLogger(__name__)

class FileHandler:
    @staticmethod
    def copy_files(selected_options, ped_name):
        """Main copy function with enhanced error handling"""
        try:
            if not ped_name:
                raise ValueError("Name not provided, cannot proceed with file copy.")
            
            final_target = os.path.join(TARGET_FOLDER, ped_name, "stream")
            os.makedirs(final_target, exist_ok=True)
            
            files_copied = False
            
            for category, items in selected_options.items():
                if category == "name":
                    continue
                    
                prefix = CATEGORY_PREFIXES.get(category)
                if prefix and items:
                    for item in items:
                        category_base = os.path.join(MALE_PATH, category, str(item))
                        texture_path = os.path.join(category_base, "textures", "files")
                        
                        if FileHandler._copy_ydd_file(category_base, final_target, prefix, str(item)):
                            files_copied = True
                        
                        if FileHandler._copy_ytd_files(texture_path, final_target, prefix, str(item)):
                            files_copied = True
            
            if not files_copied:
                raise FileNotFoundError("No files were found to copy. Please check the file paths and selected items.")
            
            FileHandler._rename_files(final_target)
            FileHandler._add_name_to_files(final_target, ped_name)
            FileHandler._add_data_to_ped(ped_name)
            logger.info("File copying process completed successfully.")
            
        except Exception as e:
            logger.error(f"Error during file copying: {e}")
            raise

    @staticmethod
    def _copy_ytd_files(texture_path, final_target, prefix, item):
        """Copy YTD files with dynamic filename generation"""
        try:
            if not os.path.exists(texture_path):
                logger.warning(f"Texture path does not exist: {texture_path}")
                return False
            
            is_numeric = item.isdigit()
            
            if is_numeric:
                item_num = int(item)
                if item_num <= 9:
                    ytd_name = f"{prefix}_00{item}_diff_a_uni.ytd"
                else:
                    ytd_name = f"{prefix}_0{item}_diff_a_uni.ytd"
            else:
                ytd_name = f"{prefix}_{item}_diff_a_uni.ytd"
                    
            src_ytd = os.path.join(texture_path, ytd_name)
            dst_ytd = os.path.join(final_target, ytd_name)
            
            if os.path.exists(src_ytd):
                shutil.copy(src_ytd, dst_ytd)
                logger.info(f"Copied YTD file: {src_ytd} to {dst_ytd}")
                return True
            else:
                logger.warning(f"YTD file not found: {src_ytd}")
                return False
                
        except Exception as e:
            logger.error(f"Error copying YTD file: {e}")
            return False

    @staticmethod
    def _copy_ytd_files(texture_path, final_target, prefix, item):
        """Copy YTD files with detailed logging and return status"""
        try:
            # Ensure texture_path exists
            if not os.path.exists(texture_path):
                print(f"Error: Texture path does not exist: {texture_path}")
                return False
            
            files_copied = False
            
            # Iterate through all files in the texture path
            for ytd_file in os.listdir(texture_path):
                if ytd_file.endswith('.ytd'):
                    src_ytd = os.path.join(texture_path, ytd_file)
                    dst_ytd = os.path.join(final_target, ytd_file)
                    
                    # Log source and destination paths
                    print(f"Copying YTD file from {src_ytd} to {dst_ytd}")
                    
                    if os.path.exists(src_ytd):
                        # Copy the file
                        shutil.copy(src_ytd, dst_ytd)
                        files_copied = True
                    else:
                        print(f"Warning: Source YTD file not found: {src_ytd}")
            
            # Check if any files were copied
            if not files_copied:
                print(f"No YTD files were found to copy in {texture_path}")
            
            return files_copied
        
        except Exception as e:
            print(f"Error copying YTD files: {e}")
            return False

    @staticmethod
    def _rename_files(directory):
        """Rename files with better error handling"""
        try:
            files = os.listdir(directory)
            
            for category, prefix in CATEGORY_PREFIXES.items():
                # Get all files for current prefix
                ydd_files = [f for f in files if f.startswith(prefix) and f.endswith(".ydd")]
                ytd_files = [f for f in files if f.startswith(prefix) and f.endswith(".ytd")]
                
                # Sort function for mixed numeric and text filenames
                def natural_sort_key(s):
                    import re
                    numbers = re.findall(r'\d+', s)
                    if numbers:
                        return int(numbers[0])
                    return float('inf')
                
                # Handle YDD files
                ydd_files.sort(key=natural_sort_key)
                for index, filename in enumerate(ydd_files, start=1):
                    old_path = os.path.join(directory, filename)
                    
                    if not os.path.exists(old_path):
                        print(f"Warning: File not found: {old_path}")
                        continue
                        
                    # Skip non-numeric files
                    if not any(c.isdigit() for c in filename):
                        continue
                        
                    new_filename = f"{prefix}_00{index}_u.ydd"
                    new_path = os.path.join(directory, new_filename)
                    
                    if old_path == new_path:
                        continue
                        
                    if os.path.exists(new_path):
                        print(f"Warning: Target file already exists: {new_path}")
                        continue
                    
                    try:
                        os.rename(old_path, new_path)
                    except OSError as e:
                        print(f"Warning: Could not rename {old_path} to {new_path}: {e}")
                
                # Handle YTD files
                ytd_files.sort(key=natural_sort_key)
                for index, filename in enumerate(ytd_files, start=1):
                    old_path = os.path.join(directory, filename)
                    
                    if not os.path.exists(old_path):
                        print(f"Warning: File not found: {old_path}")
                        continue
                        
                    # Skip non-numeric files
                    if not any(c.isdigit() for c in filename):
                        continue
                        
                    new_filename = f"{prefix}_diff_00{index}_a_uni.ytd"
                    new_path = os.path.join(directory, new_filename)
                    
                    if old_path == new_path:
                        continue
                        
                    if os.path.exists(new_path):
                        print(f"Warning: Target file already exists: {new_path}")
                        continue
                    
                    try:
                        os.rename(old_path, new_path)
                    except OSError as e:
                        print(f"Warning: Could not rename {old_path} to {new_path}: {e}")
                        
        except Exception as e:
            print(f"Error during file renaming: {e}")
            raise

    @staticmethod
    def _add_name_to_files(directory, prefix):
        """Add prefix to all files in directory"""
        try:
            for filename in os.listdir(directory):
                if filename.endswith((".ydd", ".ytd")):
                    old_path = os.path.join(directory, filename)

                    # Adjust the prefix based on file type
                    if filename.startswith("p_"):
                        new_prefix = f"{prefix}_p^"
                    else:
                        new_prefix = f"{prefix}^"

                    new_path = os.path.join(directory, f"{new_prefix}{filename}")

                    if not os.path.exists(old_path):
                        continue

                    if os.path.exists(new_path):
                        continue

                    try:
                        os.rename(old_path, new_path)
                    except OSError as e:
                        print(f"Warning: Could not rename {old_path} to {new_path}: {e}")
                        
        except Exception as e:
            print(f"Error adding name to files: {e}")
            raise

    @staticmethod
    def _add_data_to_ped(name):
        """Add additional ped data files"""
        try:
            current_location = os.path.dirname(os.path.abspath(__file__))
            
            # Handle peds.meta
            peds_meta_path = os.path.join(current_location, "peds.meta")
            if os.path.exists(peds_meta_path):
                new_path = shutil.copy(peds_meta_path, os.path.join(TARGET_FOLDER, name))
                with open(new_path, "r") as file:
                    content = file.read().replace("ig_ped_name", name)
                with open(new_path, "w") as file:
                    file.write(content)
            
            # Handle fxmanifest.lua
            fx_path = os.path.join(current_location, "fxmanifest.lua")
            if os.path.exists(fx_path):
                shutil.copy(fx_path, os.path.join(TARGET_FOLDER, name))
            
            # Handle .yft file
            yft_path = os.path.join(current_location, ".yft")
            if os.path.exists(yft_path):
                final_target = os.path.join(TARGET_FOLDER, name, "stream")
                dst_yft = os.path.join(final_target, f"{name}.yft")
                shutil.copy(yft_path, dst_yft)
                
        except Exception as e:
            print(f"Error adding data to ped: {e}")
            raise