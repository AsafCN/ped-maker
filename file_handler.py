import os
import shutil
from config import *
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

TARGET_FOLDER = "output"

class FileHandler:
    @staticmethod
    def _process_head_asset(asset_data):
        """Process assets for the head category."""
        category, item, textures, final_target, ped_name, base_path, model_counts, texture_variants = asset_data
        logger.debug(f"START PROCESSING - Category: {category}, Item: {item}")

        temp_prefix = f"__temp_{ped_name}__"
        temp_files = []

        try:
            # Special path for head textures
            texture_dir = Path(base_path) / "textures" / str(textures[0]) if textures else None  # Use the selected texture ID
            # Special path for head model
            model_dir = Path(base_path) / "model" / str(item)  # Use the selected model ID

            success = False

            # Handle textures (only copy selected textures)
            if texture_dir and texture_dir.exists():
                logger.debug(f"FOUND TEXTURE DIR: {texture_dir}")
                for texture in textures:  # Only process textures from the selected list
                    texture_file = texture.replace(".png", ".ytd")  # Convert .png to .ytd
                    texture_path = texture_dir / texture_file

                    if texture_path.exists():
                        # Determine the texture variant (a, b, c, etc.)
                        variant = chr(ord('a') + texture_variants.get((category, model_counts[category]), 0))
                        texture_variants[(category, model_counts[category])] = texture_variants.get((category, model_counts[category]), 0) + 1

                        # Texture final name for head
                        texture_final_name = f"{ped_name}^{CATEGORY_PREFIXES[category]}_diff_{model_counts[category]:03d}_{variant}_uni.ytd"

                        texture_temp = Path(final_target) / f"{temp_prefix}{texture_final_name}"
                        texture_final = Path(final_target) / texture_final_name

                        logger.debug(f"COPYING: {texture_path} -> {texture_final}")
                        shutil.copy(str(texture_path), str(texture_temp))
                        os.rename(str(texture_temp), str(texture_final))
                        temp_files.append(texture_temp)
                        success = True
                    else:
                        logger.debug(f"TEXTURE NOT FOUND: {texture_path}")
            else:
                logger.debug(f"NO TEXTURE DIR AT: {texture_dir}")

            # Handle model (rename to match ped_name and category prefix)
            category_prefix = CATEGORY_PREFIXES.get(category, category)  # Get prefix from CATEGORY_PREFIXES
            model_file = f"{ped_name}^{category_prefix}_{model_counts[category]:03d}_r.ydd"  # Example: ig_test^head_000_u.ydd
            model_path = model_dir / f"head_{int(item):03d}_r.ydd"  # Original model file path for head

            if model_path.exists():
                model_temp = Path(final_target) / f"{temp_prefix}{model_file}"
                model_final = Path(final_target) / model_file

                logger.debug(f"COPYING: {model_path} -> {model_final}")
                shutil.copy(str(model_path), str(model_temp))
                os.rename(str(model_temp), str(model_final))
                temp_files.append(model_temp)
                success = True
            else:
                logger.debug(f"NO MODEL AT: {model_path}")

            # Increment the model count for this category
            model_counts[category] += 1

            return success

        except Exception as e:
            logger.error(f"ERROR in {category}/{item}: {str(e)}")
            for f in temp_files:
                try:
                    if os.path.exists(f):
                        os.remove(f)
                except Exception as cleanup_error:
                    logger.error(f"Cleanup failed for {f}: {cleanup_error}")
            return False

    @staticmethod
    def _process_body_asset(asset_data):
        """Process assets for the body category."""
        category, item, textures, final_target, ped_name, base_path, model_counts, texture_variants = asset_data
        logger.debug(f"START PROCESSING - Category: {category}, Item: {item}")

        temp_prefix = f"__temp_{ped_name}__"
        temp_files = []

        try:
            # Special path for body textures
            texture_dir = Path(base_path) / "textures" / str(textures[0]) if textures else None  # Use the selected texture ID
            # Special path for body model
            model_dir = Path(base_path) / "model" / str(item)  # Use the selected model ID

            success = False

            # Handle textures (only copy selected textures)
            if texture_dir and texture_dir.exists():
                logger.debug(f"FOUND TEXTURE DIR: {texture_dir}")
                for texture in textures:  # Only process textures from the selected list
                    texture_file = texture.replace(".png", ".ytd")  # Convert .png to .ytd
                    texture_path = texture_dir / texture_file

                    if texture_path.exists():
                        # Determine the texture variant (a, b, c, etc.)
                        variant = chr(ord('a') + texture_variants.get((category, model_counts[category]), 0))
                        texture_variants[(category, model_counts[category])] = texture_variants.get((category, model_counts[category]), 0) + 1

                        # Texture final name for body
                        texture_final_name = f"{ped_name}^{CATEGORY_PREFIXES[category]}_diff_{model_counts[category]:03d}_{variant}_whi.ytd"

                        texture_temp = Path(final_target) / f"{temp_prefix}{texture_final_name}"
                        texture_final = Path(final_target) / texture_final_name

                        logger.debug(f"COPYING: {texture_path} -> {texture_final}")
                        shutil.copy(str(texture_path), str(texture_temp))
                        os.rename(str(texture_temp), str(texture_final))
                        temp_files.append(texture_temp)
                        success = True
                    else:
                        logger.debug(f"TEXTURE NOT FOUND: {texture_path}")
            else:
                logger.debug(f"NO TEXTURE DIR AT: {texture_dir}")

            # Handle model (rename to match ped_name and category prefix)
            category_prefix = CATEGORY_PREFIXES.get(category, category)  # Get prefix from CATEGORY_PREFIXES
            model_file = f"{ped_name}^{category_prefix}_{model_counts[category]:03d}_r.ydd"  # Example: ig_test^body_001_u.ydd
            model_path = model_dir / f"body_{int(item):03d}_r.ydd"  # Original model file path for body

            if model_path.exists():
                model_temp = Path(final_target) / f"{temp_prefix}{model_file}"
                model_final = Path(final_target) / model_file

                logger.debug(f"COPYING: {model_path} -> {model_final}")
                shutil.copy(str(model_path), str(model_temp))
                os.rename(str(model_temp), str(model_final))
                temp_files.append(model_temp)
                success = True
            else:
                logger.debug(f"NO MODEL AT: {model_path}")

            # Increment the model count for this category
            model_counts[category] += 1

            return success

        except Exception as e:
            logger.error(f"ERROR in {category}/{item}: {str(e)}")
            for f in temp_files:
                try:
                    if os.path.exists(f):
                        os.remove(f)
                except Exception as cleanup_error:
                    logger.error(f"Cleanup failed for {f}: {cleanup_error}")
            return False
        
    @staticmethod
    def _process_single_asset(asset_data):
        category, item, textures, final_target, ped_name, base_path, model_counts, texture_variants = asset_data
        logger.debug(f"START PROCESSING - Category: {category}, Item: {item}")
        
        temp_prefix = f"__temp_{ped_name}__"
        temp_files = []
        if category == "head":
            return FileHandler._process_head_asset(asset_data)
        elif category == "body":
            return FileHandler._process_body_asset(asset_data)
        else:

            try:
                texture_dir = Path(base_path) / category / str(item) / "textures" / "files"
                model_dir = Path(base_path) / category / str(item)
                
                success = False
                
                # Handle textures (only copy selected textures)
                if texture_dir.exists():
                    logger.debug(f"FOUND TEXTURE DIR: {texture_dir}")
                    for texture in textures:  # Only process textures from the selected list
                        texture_file = texture.replace(".png", ".ytd")  # Convert .png to .ytd
                        texture_path = texture_dir / texture_file
                        
                        if texture_path.exists():
                            # Determine the texture variant (a, b, c, etc.)
                            variant = chr(ord('a') + texture_variants.get((category, model_counts[category]), 0))
                            texture_variants[(category, model_counts[category])] = texture_variants.get((category, model_counts[category]), 0) + 1
                            
                            # Special handling for prop categories
                            if category in ["watches", "glasses", "hats"]:
                                texture_final_name = f"{ped_name}_p^{CATEGORY_PREFIXES[category]}_diff_{model_counts[category]:03d}_{variant}.ytd"
                            else:
                                texture_final_name = f"{ped_name}^{CATEGORY_PREFIXES[category]}_diff_{model_counts[category]:03d}_{variant}_uni.ytd"
                            
                            texture_temp = Path(final_target) / f"{temp_prefix}{texture_final_name}"
                            texture_final = Path(final_target) / texture_final_name
                            
                            logger.debug(f"COPYING: {texture_path} -> {texture_final}")
                            shutil.copy(str(texture_path), str(texture_temp))
                            os.rename(str(texture_temp), str(texture_final))
                            temp_files.append(texture_temp)
                            success = True
                        else:
                            logger.debug(f"TEXTURE NOT FOUND: {texture_path}")
                else:
                    logger.debug(f"NO TEXTURE DIR AT: {texture_dir}")
                
                # Handle model (rename to match ped_name and category prefix)
                category_prefix = CATEGORY_PREFIXES.get(category, category)  # Get prefix from CATEGORY_PREFIXES
                if category in ["watches", "glasses", "hats"]:
                    model_file = f"{ped_name}_p^{category_prefix}_{model_counts[category]:03d}.ydd"  # Example: ig_test_p^p_head_001.ydd
                    model_path = model_dir / f"{category_prefix}_{int(item):03d}.ydd"  # Original model file path
                else:
                    model_file = f"{ped_name}^{category_prefix}_{model_counts[category]:03d}_u.ydd"  # Example: ig_test^accs_001_u.ydd
                    model_path = model_dir / f"{category_prefix}_{int(item):03d}_u.ydd"  # Original model file path

                if model_path.exists():
                    model_temp = Path(final_target) / f"{temp_prefix}{model_file}"
                    model_final = Path(final_target) / model_file
                    
                    logger.debug(f"COPYING: {model_path} -> {model_final}")
                    shutil.copy(str(model_path), str(model_temp))
                    os.rename(str(model_temp), str(model_final))
                    temp_files.append(model_temp)
                    success = True
                else:
                    logger.debug(f"NO MODEL AT: {model_path}")
                
                # Increment the model count for this category
                model_counts[category] += 1
                
                return success

            except Exception as e:
                logger.error(f"ERROR in {category}/{item}: {str(e)}")
                for f in temp_files:
                    try:
                        if os.path.exists(f):
                            os.remove(f)
                    except Exception as cleanup_error:
                        logger.error(f"Cleanup failed for {f}: {cleanup_error}")
                return False

    @staticmethod
    def copy_files(selected_options, ped_name, base_path, progress_callback=None):
        logger.debug(f"STARTING PROCESS FOR: {ped_name}")
        logger.debug(f"FROM: {base_path}")
        
        final_target = Path("output") / ped_name / "stream"
        os.makedirs(final_target, exist_ok=True)
        final_target.mkdir(parents=True, exist_ok=True)
        logger.debug(f"TO: {final_target}")
        
        try:
            success_count = 0
            total_items = sum(len(items) for category, items in selected_options.items() 
                            if not category.endswith('_textures') and category != 'name')

            # Track model counts and texture variants for each category
            model_counts = defaultdict(lambda: 0)
            texture_variants = defaultdict(int)

            # Sort categories and items for consistent processing
            sorted_categories = sorted(selected_options.keys())
            for category in sorted_categories:
                if category.endswith('_textures') or category == 'name':
                    continue

                logger.debug(f"PROCESSING CATEGORY: {category}")
                texture_category = f"{category}_textures"
                textures = selected_options.get(texture_category, {})

                # Sort items for consistent processing
                sorted_items = sorted(selected_options[category], key=lambda x: int(x))  # Sort items as integers
                for item in sorted_items:
                    task_data = (
                        category,
                        item,
                        textures.get(str(item), []),
                        str(final_target),
                        ped_name,
                        base_path,
                        model_counts,  # Pass model_counts to _process_single_asset
                        texture_variants  # Pass texture_variants to _process_single_asset
                    )
                    
                    if FileHandler._process_single_asset(task_data):
                        success_count += 1
                        logger.debug(f"SUCCESS - {category}/{item}")
                    else:
                        logger.debug(f"FAILED - {category}/{item}")

            if success_count == 0:
                raise RuntimeError("No valid items processed")

            # Call the method to copy meta files
            FileHandler._copy_meta_files(ped_name)

            logger.info(f"COMPLETED: {success_count} items processed")
            return True

        except Exception as e:
            logger.critical(f"CRITICAL ERROR: {str(e)}")
            if final_target.exists():
                shutil.rmtree(str(final_target))
            raise

    @staticmethod
    def _copy_meta_files(ped_name):
        """Copy required meta files to target directory"""
        meta_files = {
            "peds.meta": os.path.join(TARGET_FOLDER, ped_name),
            "fxmanifest.lua": os.path.join(TARGET_FOLDER, ped_name),
            "ped.yft": os.path.join(TARGET_FOLDER, ped_name, "stream")
        }
        
        for meta_file, target_dir in meta_files.items():
            src = os.path.join(os.path.dirname(__file__),"needed" ,meta_file)
            logger.debug(f"Checking source path: {src}")
            
            if os.path.exists(src):
                os.makedirs(target_dir, exist_ok=True)
                logger.debug(f"Directory created: {target_dir}")
                
                if meta_file == "peds.meta":
                    # Handle peds.meta template
                    with open(src, 'r') as file:
                        content = file.read()
                    modified_content = content.replace('ig_ped_name', ped_name)
                    target_path = os.path.join(target_dir, meta_file)
                    with open(target_path, 'w') as file:
                        file.write(modified_content)
                    logger.info(f"Copied and modified meta file: {meta_file}")
                    
                elif meta_file == "ped.yft":
                    # Rename YFT file to match ped name
                    target_path = os.path.join(target_dir, f"{ped_name}.yft")
                    shutil.copy(src, target_path)
                    logger.info(f"Copied and renamed YFT file to: {ped_name}.yft")
                    
                else:
                    # Regular file copy for other files
                    shutil.copy(src, os.path.join(target_dir, meta_file))
                    logger.info(f"Copied meta file: {meta_file}")
            else:
                logger.error(f"Source file not found: {src}")