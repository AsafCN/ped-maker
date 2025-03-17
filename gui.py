from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional
from tkinter import ttk, messagebox
from functools import partial
from ymt import generate_xml
import customtkinter as ctk
from PIL import Image
from config import *
import tkinter as tk
import threading
import queue
import time
import sys
import os

class ImageDropdown(ctk.CTkFrame):
    def __init__(self, master, images_path, current_value, image_loader, command, preview_label, selected_textures):
        self.images_path = images_path
        self.current_value = current_value
        self.command = command
        self.preview_label = preview_label
        self.selected_textures = selected_textures

        super().__init__(master)

        self.image_loader = AsyncImageLoader.get_instance(self)

        self.button = ctk.CTkButton(
            self,
            text="Select Texture",
            width=140,
            height=35,
            fg_color=PURPLE,
            hover_color=HOVER_PURPLE,
            command=self.show_popup
        )
        self.button.pack(padx=5, pady=2)

        self.popup = None
        self.close_scheduled = False

        if self.current_value:
            self.set_button_image(self.current_value)
                
    def show_popup(self):
        """Guaranteed functional popup creation"""
        try:
            # Completely destroy previous popup
            if self.popup and self.popup.winfo_exists():
                self.popup.destroy()
                self.popup = None

            # Create fresh popup structure
            self.popup = ctk.CTkToplevel(self)
            self.popup.withdraw()
            self.popup.overrideredirect(True)
            self.popup.attributes("-topmost", True)
            
            # Container with direct parent reference
            container = ctk.CTkFrame(self.popup)
            container.pack(expand=True, fill='both')
            
            # New scroll frame instance
            self.scroll_frame = ctk.CTkScrollableFrame(
                container,
                width=150,
                height=200
            )
            self.scroll_frame.pack(expand=True, fill='both')

            # Load textures with PROPER command binding
            textures = self._get_available_textures()[:10]
            for idx, texture in enumerate(textures):
                # Create button with explicit command capture
                btn = ctk.CTkButton(
                    self.scroll_frame,
                    text="",
                    width=140,
                    height=40,
                    fg_color=PURPLE,
                    hover_color=HOVER_PURPLE,
                    command=lambda t=texture: self._handle_texture_selection(t)  # Fixed binding
                )
                btn.pack(padx=5, pady=2)
                
                # Load image with safety checks
                image_path = os.path.join(self.images_path, texture)
                if os.path.exists(image_path):
                    self.image_loader.load_image(
                        image_path,
                        (100, 100),
                        lambda photo, b=btn: self._safe_update_button(b, photo)
                    )

            # Finalize popup
            self.place_popup()
            self.popup.deiconify()
            
        except Exception as e:
            logger.exception(f"Popup rebuild failed: {str(e)}")

    def _handle_texture_selection(self, texture):
        """Direct selection handling with UI update"""
        try:
            if texture not in self.selected_textures:
                self.selected_textures.append(texture)
                self.set_button_image(texture)
                if self.command:
                    self.command(texture)
            if self.popup:
                self.popup.destroy()
                self.popup = None
        except Exception as e:
            logger.exception(f"Selection failed: {str(e)}")

    def _safe_update_button(self, button, photo):
        """Thread-safe button update"""
        if button.winfo_exists():
            button.configure(image=photo, text="")

    def _get_available_textures(self):  # NEW METHOD
        """Get updated list of textures excluding selected ones"""
        all_textures = sorted([t for t in os.listdir(self.images_path) 
                            if t.endswith('.png')])
        return [t for t in all_textures 
            if t not in self.selected_textures]
        
    def place_popup(self):
        """Position the popup below the button"""
        if not self.popup:
            return
            
        # Get button position
        x = self.button.winfo_rootx()
        y = self.button.winfo_rooty() + self.button.winfo_height()
        
        # Set popup position
        self.popup.geometry(f"+{x}+{y}")
        
    def create_popup(self):
        """Recreate popup with proper initialization"""
        try:
            # Destroy existing popup completely
            if self.popup and self.popup.winfo_exists():
                self.popup.destroy()
            
            # Create fresh popup structure
            self.popup = ctk.CTkToplevel(self)
            self.popup.withdraw()
            self.popup.overrideredirect(True)
            self.popup.attributes("-topmost", True)
            
            # Container with proper parent reference
            container = ctk.CTkFrame(self.popup)
            container.pack(expand=True, fill='both')
            
            # Reinitialize scroll frame with correct parent
            self.scroll_frame = ctk.CTkScrollableFrame(
                container,
                width=150,
                height=200
            )
            self.scroll_frame.pack(expand=True, fill='both')
            
            # Load textures with current selection state
            available_textures = self._get_available_textures()
            self.load_textures_batch(self.scroll_frame, available_textures[:10])  # Initial load
            
            # Mouse tracking
            for widget in (self.popup, container, self.scroll_frame):
                widget.bind('<Enter>', self.cancel_close)
                widget.bind('<Leave>', lambda e: self.schedule_close())
                
        except Exception as e:
            logger.exception(f"Popup creation failed: {str(e)}")
            
    def set_button_image(self, texture):
        try:
            if texture:
                image_path = os.path.join(self.images_path, texture)
                image = Image.open(image_path)
                
                # Use high-quality resizing
                image = image.resize((140, 35), Image.Resampling.LANCZOS)  # Fixed size
                photo = ctk.CTkImage(image, size=(140, 35))
                
                # Show BOTH image and text
                self.button.configure(image=photo, text="Selected Texture")
                
                # Update preview label with high-quality image
                if self.preview_label:
                    preview_image = Image.open(image_path)
                    preview_image = preview_image.resize((100, 100), Image.Resampling.LANCZOS)  # Fixed size
                    preview_photo = ctk.CTkImage(preview_image, size=(100, 100))
                    self.preview_label.configure(image=preview_photo, text="")
            else:
                self.button.configure(image=None, text="Select Texture")
        except Exception as e:
            logger.exception(f"Image error: {e}")
            self.button.configure(image=None, text="Select Texture")

    def load_textures_batch(self, parent, textures):
        """Load a batch of textures asynchronously."""
        if not parent.winfo_exists():
            return
        
        for texture in textures:
            image_path = os.path.join(self.images_path, texture)
            btn = ctk.CTkButton(
                parent,
                text="",
                width=140,
                height=40,
                fg_color=PURPLE,
                hover_color=HOVER_PURPLE,
                command=lambda t=texture: self.select_option(t)
            )
            btn.pack(padx=5, pady=2)

            if os.path.exists(image_path):
                # Use image_loader to load image asynchronously
                self.image_loader.load_image(
                    image_path,
                    (100, 100),  # Thumbnail size
                    lambda photo, button=btn: button.configure(image=photo, text="") if photo else button.configure(text="Error")
                )
            
    def load_more_textures(self, event=None):
        """Load more textures as user scrolls"""
        if hasattr(self, 'remaining_textures') and self.remaining_textures:
            batch = self.remaining_textures[:5]  # Load 5 more
            self.remaining_textures = self.remaining_textures[5:]
            self.load_textures_batch(event.widget, batch)
            
    def cancel_close(self, event=None):
        """Cancel scheduled popup close"""
        self.close_scheduled = False
        
    def schedule_close(self):
        """Schedule popup close"""
        if not self.close_scheduled:
            self.close_scheduled = True
            self.after(200, self.check_close)
            
    def check_close(self):
        """Check if popup should be closed"""
        if self.close_scheduled:
            if self.popup and self.popup.winfo_exists():  # Check before destroying
                self.popup.destroy()
            self.popup = None
            
    def select_option(self, texture):
        """Handle selection with immediate UI refresh"""
        if texture in self.selected_textures:
            return  # Prevent duplicates
        
        # Ensure textures are only added to their respective category
        if self.category == "masks" and not texture.startswith("berd_diff_"):
            return  # Skip non-mask textures for the masks category
        
        self.selected_textures.append(texture)
        if self.command:
            self.command(texture)
        if self.popup:
            self.popup.destroy()
            self.popup = None
        self.set_button_image(texture)
        # Force parent to refresh dropdowns
        self.master.master.master.update_texture_display(self.current_item)
            
    def update_preview(self, texture):
        """Update the preview label with the selected texture"""
        if self.preview_label and texture:
            image_path = os.path.join(self.images_path, texture)
            if os.path.exists(image_path):
                self.image_loader.load_image(
                    image_path,
                    (100, 100),  # Preview size
                    lambda photo: self.preview_label.configure(image=photo, text="") if photo else None
                )

import threading
import queue
import logging
import uuid
import time
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
import customtkinter as ctk

logger = logging.getLogger(__name__)

class ImageCache:
    """Simple image cache implementation"""
    def __init__(self, max_size=100):
        self.cache = {}
        self.max_size = max_size
        self.lock = threading.Lock()
        self.categories = {}  # Map of category -> set of paths
        
    def get(self, image_path):
        with self.lock:
            return self.cache.get(image_path)
    
    def put(self, image_path, image, category=None):
        with self.lock:
            # Enforce size limit with simple LRU-like eviction
            if len(self.cache) >= self.max_size:
                # Remove oldest item (first added)
                if self.cache:
                    oldest = next(iter(self.cache))
                    del self.cache[oldest]
            
            self.cache[image_path] = image
            
            # Track by category if provided
            if category:
                if category not in self.categories:
                    self.categories[category] = set()
                self.categories[category].add(image_path)
    
    def remove_category(self, category):
        with self.lock:
            if category in self.categories:
                # Remove all images in this category
                for path in self.categories[category]:
                    if path in self.cache:
                        del self.cache[path]
                # Clear category tracking
                del self.categories[category]

class AsyncImageLoader:
    """Thread-safe image loader with lifecycle management"""
    _instances = {}  # Track instances by parent
    
    @classmethod
    def get_instance(cls, parent):
        """Get or create an instance for the given parent"""
        parent_id = str(id(parent))
        if parent_id not in cls._instances:
            cls._instances[parent_id] = AsyncImageLoader(parent)
        return cls._instances[parent_id]
    
    @classmethod
    def cleanup_instances(cls):
        """Clean up instances for destroyed parents"""
        to_remove = []
        for parent_id, instance in cls._instances.items():
            if not instance.parent.winfo_exists():
                instance.stop()
                to_remove.append(parent_id)
        
        for parent_id in to_remove:
            del cls._instances[parent_id]
    
    def __init__(self, parent):
        """Initialize the image loader"""
        self.parent = parent
        self.image_cache = ImageCache()
        self.load_queue = queue.Queue()
        self._running = False
        self._lock = threading.Lock()
        self.worker_thread = None
        self.executor = ThreadPoolExecutor(max_workers=2)
        self.active_tasks = set()
        self.max_concurrent_tasks = 10
        self.last_activity = time.time()
        
        # Setup automatic cleanup when parent is destroyed
        if hasattr(parent, "bind") and callable(parent.bind):
            try:
                parent.bind("<Destroy>", lambda e: self.stop(), add="+")
            except Exception as e:
                logger.warning(f"Could not bind destroy event: {e}")
        
        # Auto-start (controlled)
        self.start()
    
    def start(self):
        """Start the image loader thread if not already running"""
        with self._lock:
            if not self._running:
                # Check if thread exists and is alive
                if self.worker_thread and self.worker_thread.is_alive():
                    logger.warning("Thread already running, not starting a new one")
                    self._running = True
                    return
                    
                self._running = True
                
                # Initialize a new thread if needed
                self.worker_thread = threading.Thread(
                    target=self._process_queue, 
                    daemon=True,
                    name="AsyncImageLoader"
                )
                self.worker_thread.start()
                logger.debug("Image loader thread started")
    
    def stop(self):
        """Safely stop the image loader thread"""
        with self._lock:
            if self._running:
                logger.debug("Stopping image loader")
                self._running = False
                
                # Clear the queue first
                while not self.load_queue.empty():
                    try:
                        self.load_queue.get_nowait()
                        self.load_queue.task_done()
                    except queue.Empty:
                        break
                
                # Send termination signal
                self.load_queue.put(("TERMINATE", None, None, None))
                
                # Shutdown executor
                try:
                    self.executor.shutdown(wait=False, cancel_futures=True)
                    # Create a new executor for future use
                    self.executor = ThreadPoolExecutor(max_workers=2)
                except Exception as e:
                    logger.exception(f"Error shutting down executor: {str(e)}")
                
                # Wait for thread to terminate
                if self.worker_thread and self.worker_thread.is_alive():
                    try:
                        self.worker_thread.join(timeout=1.0)
                        if self.worker_thread.is_alive():
                            logger.warning("Thread still alive after timeout")
                    except RuntimeError as e:
                        logger.error(f"Error joining thread: {e}")
                
                # Clear active tasks
                self.active_tasks.clear()
                logger.debug("Image loader stopped")
    
    def _process_queue(self):
        """Process the image loading queue with auto-timeout"""
        idle_start = None
        max_idle_seconds = 10
        
        while self._running:
            try:
                # Use a short timeout to check for idle state
                task = self.load_queue.get(timeout=0.5)
                
                # Reset idle tracking when a task is found
                idle_start = None
                
                # Check for termination signal
                if task[0] == "TERMINATE":
                    break
                    
                # Process the task
                image_path, size, callback, task_id = task
                self._load_single_image(image_path, size, callback, task_id)
                self.load_queue.task_done()
                
            except queue.Empty:
                # Track idle time
                if idle_start is None:
                    idle_start = time.time()
                
                # Auto-stop if idle for too long with no active tasks
                if idle_start and (time.time() - idle_start > max_idle_seconds) and not self.active_tasks:
                    with self._lock:
                        logger.debug("Image loader idle timeout, pausing")
                        self._running = False
                    break
                
            except Exception as e:
                logger.exception(f"Queue error: {str(e)}")
        
        logger.debug("Image loader queue processor exited")
    
    def load_image(self, image_path, size, callback, category=None):
        """Add an image loading task to the queue"""
        # Check if parent widget still exists
        if not self.parent.winfo_exists():
            return None
        
        # Generate a unique task ID
        task_id = str(uuid.uuid4())
        
        # Wrap callback for task tracking
        def task_complete_callback(photo):
            try:
                # Ensure parent exists before callback
                if self.parent.winfo_exists():
                    callback(photo)
            except Exception as e:
                logger.exception(f"Callback error: {e}")
            finally:
                # Clean up task tracking
                with self._lock:
                    if task_id in self.active_tasks:
                        self.active_tasks.remove(task_id)
        
        # Add to active tasks
        with self._lock:
            if len(self.active_tasks) >= self.max_concurrent_tasks:
                logger.warning(f"Too many active tasks ({len(self.active_tasks)}), dropping: {image_path}")
                return None
            self.active_tasks.add(task_id)
        
        # Check for cached image
        cached_image = self.image_cache.get(image_path)
        if cached_image:
            # Use cached image and run callback directly
            self.parent.after(0, lambda: task_complete_callback(cached_image))
            return task_id
        
        # Add image loading task to queue
        if self.parent.winfo_exists():
            self.load_queue.put((image_path, size, task_complete_callback, task_id))
            
            # Ensure worker is running
            if not self._running:
                self.start()
        
        return task_id
    
    def cancel_task(self, task_id):
        """Cancel a pending task if possible"""
        with self._lock:
            if task_id in self.active_tasks:
                self.active_tasks.remove(task_id)
                return True
        return False
    
    def _load_single_image(self, image_path, size, callback, task_id):
        """Load a single image with error handling"""
        if task_id not in self.active_tasks:
            # Task was cancelled
            return
            
        try:
            # Attempt to load image
            image = Image.open(image_path)
            if size:
                image.thumbnail(size)
            
            # Convert to CTkImage
            photo = ctk.CTkImage(image, size=image.size)
            
            # Cache the image
            self.image_cache.put(image_path, photo)
            
            # Ensure parent widget still exists
            if not self.parent.winfo_exists():
                return
                
            # Execute callback on main thread
            self.parent.after(0, lambda: callback(photo))
            
        except Exception as e:
            logger.exception(f"Image load failed: {str(e)}")
            # Execute callback with None to indicate failure
            if self.parent.winfo_exists():
                self.parent.after(0, lambda: callback(None))
    
    def clear_category(self, category: str):
        """Clear cached images for a category"""
        self.image_cache.remove_category(category)
    
    def __del__(self):
        """Clean up resources when object is garbage collected"""
        try:
            self.stop()
        except Exception as e:
            logger.exception(f"Error in __del__: {e}")
        
        # Remove from class instances
        for parent_id, instance in list(self._instances.items()):
            if instance is self:
                del self._instances[parent_id]
                break

class CategoryView(ctk.CTkFrame):
    def __init__(self, parent, category: str, base_path: str, update_callback, get_preview_image, main_app,**kwargs):
        super().__init__(parent, **kwargs)
        self.dropdowns = {}
        self.main_app = main_app

        self.category = category
        self.base_path = base_path
        self.image_loader = AsyncImageLoader.get_instance(self)
        self.update_callback = update_callback
        self.get_preview_image = get_preview_image
        self.items_loaded = False
        self.current_page = 0
        self.items_per_page = 10
        
        # Initialize dictionaries for textures
        self.texture_displays = {}
        self.item_textures = self._load_initial_state(category)

        
        # Create scrollable frame for items
        self.scrollable_frame = ctk.CTkScrollableFrame(self)
        self.scrollable_frame.pack(expand=True, fill='both', padx=10, pady=10)
        
        # Navigation buttons
        self.nav_frame = ctk.CTkFrame(self)
        self.nav_frame.pack(fill='x', padx=10, pady=5)
        
        self.prev_button = ctk.CTkButton(
            self.nav_frame,
            text="Previous",
            width=100,
            command=self.prev_page,
            fg_color=PURPLE,
            hover_color=HOVER_PURPLE
        )
        self.prev_button.pack(side='left', padx=5)
        
        self.next_button = ctk.CTkButton(
            self.nav_frame,
            text="Next",
            width=100,
            command=self.next_page,
            fg_color=PURPLE,
            hover_color=HOVER_PURPLE
        )
        self.next_button.pack(side='right', padx=5)
        
        self.page_label = ctk.CTkLabel(self.nav_frame, text="Page 1")
        self.page_label.pack(side='left', padx=5)
        
        # Store all items
        self.all_items = []
        self.load_item_list()

    def _load_initial_state(self, category):
        """Load existing selections from main app's state"""
        texture_category = f"{category}_textures"
        return {
            item: textures 
            for item, textures in self.main_app.updated_dictionary.get(texture_category, {}).items()
            if textures
        }

    def load_item_list(self):
        """Load the list of available items without loading images"""
        category_path = os.path.join(self.base_path, self.category)
        if os.path.exists(category_path):
            self.all_items = sorted(
                [item for item in os.listdir(category_path) if os.path.isdir(os.path.join(category_path, item))],
                key=lambda x: int(x) if x.isdigit() else float('inf')
            )
            self.update_navigation()
            self.load_current_page()
            
    def update_navigation(self):
        """Update navigation buttons and page label"""
        total_pages = (len(self.all_items) + self.items_per_page - 1) // self.items_per_page
        self.prev_button.configure(state='normal' if self.current_page > 0 else 'disabled')
        self.next_button.configure(state='normal' if self.current_page < total_pages - 1 else 'disabled')
        self.page_label.configure(text=f"Page {self.current_page + 1} of {total_pages}")
        
    def load_current_page(self):
        """Load items for current page"""
        self._save_current_state()  # Save before loading new page

        # Clear existing items
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        # Calculate start and end indices
        start_idx = self.current_page * self.items_per_page
        end_idx = min(start_idx + self.items_per_page, len(self.all_items))

        # Load items for the current page
        for item in self.all_items[start_idx:end_idx]:
            self.create_item_widget(item)

        # Update navigation buttons
        self.update_navigation()
            
    def create_item_widget(self, item_name: str):
        """Create widget for a single item"""
        item_path = os.path.join(self.base_path, self.category, item_name)
        frame = ctk.CTkFrame(self.scrollable_frame)
        frame.pack(fill='x', padx=5, pady=5)
        
        # Left side: Item checkbox and preview image
        left_frame = ctk.CTkFrame(frame)
        left_frame.pack(side='left', padx=5)
        
        var = ctk.BooleanVar()
        # Set initial checkbox state based on saved selection
        if item_name in self.update_callback(self.category, None, None):  # Get current selections
            var.set(True)
            
        checkbox = ctk.CTkCheckBox(
            left_frame,
            text=f"Item {item_name}",
            variable=var,
            fg_color=PURPLE,
            hover_color=HOVER_PURPLE,
            command=lambda: self.update_callback(self.category, item_name, var.get())
        )
        checkbox.pack(side='left', padx=5)
        
        # Preview image on the left
        preview_label = ctk.CTkLabel(left_frame, width=100, height=100, text="")
        preview_label.pack(side='left', padx=5)
        
        # Load preview image
        preview_image = self.get_preview_image(item_path)
        if preview_image:
            self.image_loader.load_image(
                preview_image,
                (100, 100),
                lambda photo: preview_label.configure(image=photo, text="")
            )

        # Right side: Texture selection
        right_frame = ctk.CTkFrame(frame,width=100, height=100)
        right_frame.pack(side='right', fill='x', expand=True, padx=5)
        
        textures_path = os.path.join(item_path, "textures", "pics")
        if os.path.exists(textures_path):
            # Create horizontal container for "Texture:" label, selected textures, and dropdown
            texture_container = ctk.CTkFrame(right_frame)
            texture_container.pack(side='left', fill='x', expand=True)
            
            texture_label = ctk.CTkLabel(texture_container, text="Texture:", font=ctk.CTkFont(family="Supernova", size=13))
            texture_label.pack(side='left', padx=5)
            
            # Container for selected textures
            selected_textures_frame = ctk.CTkFrame(texture_container,width=100, height=100)
            selected_textures_frame.pack(side='left', fill='x', expand=True, padx=5)
            self.texture_displays[item_name] = selected_textures_frame

            ctk.CTkLabel(selected_textures_frame, text="No textures selected",height=100).pack()
            
            # Get current textures from state and display them
            texture_category = f"{self.category}_textures"
            current_textures = self.main_app.updated_dictionary.get(texture_category, {})
            current_textures_for_item = current_textures.get(item_name, [])

            if current_textures and item_name in current_textures:
                if isinstance(current_textures[item_name], str):
                    # Convert single texture to list for backward compatibility
                    current_textures[item_name] = [current_textures[item_name]]
                self.item_textures[item_name] = current_textures[item_name]
                self.update_texture_display(item_name)
            
            # Add dropdown next to the texture label
            dropdown = ImageDropdown(
                texture_container,
                images_path=textures_path,
                current_value=current_textures_for_item[0] if current_textures_for_item else None,
                image_loader=self.image_loader,
                command=lambda t: self.add_texture(item_name, t),
                preview_label=preview_label,
                selected_textures=current_textures_for_item.copy()  # Use copy to avoid reference 
            )
            dropdown.pack(side='left', padx=5)
            self.dropdowns[item_name] = dropdown

    def update_preview_image(self, label, photo, item_name):
        """Update the preview image, considering current texture state"""
        if item_name in self.item_textures and self.item_textures[item_name]:
            # Don't update if there's a texture selected
            return
        if photo:
            label.configure(image=photo, text="")

    def add_texture(self, item_name: str, texture: str):
        valid_prefix = CATEGORY_PREFIXES.get(self.category)
        if not texture.startswith(valid_prefix):
            logger.exception(f"Invalid texture {texture} for category {self.category}")
            return        
        if item_name not in self.item_textures:
            self.item_textures[item_name] = []
        if texture not in self.item_textures[item_name]:
            logger.info(f"Adding texture {texture} to item {item_name} in category {self.category}")
            self.item_textures[item_name].append(texture)
            logger.info(f"Added texture. {texture} in {item_name}")
            self._save_current_state()
            self.update_texture_display(item_name)
            # Force immediate dropdown refresh
            for child in self.texture_displays[item_name].winfo_children():
                if isinstance(child, ImageDropdown):
                    child.selected_textures = self.item_textures[item_name].copy()
                    child.show_popup()                     

    def remove_texture(self, item_name: str, texture: str, event=None):
        if item_name in self.item_textures and texture in self.item_textures[item_name]:
            logger.info(f"Removed texture. {texture} in {item_name}")
            self.item_textures[item_name].remove(texture)
            self._save_current_state()
            self.update_texture_display(item_name)
            
            # Update the dropdown for this item
            if item_name in self.dropdowns:
                dropdown = self.dropdowns[item_name]
                dropdown.selected_textures = self.item_textures[item_name].copy()  # Update list
                \

    def _refresh_dropdowns(self, item_name: str):
        """Refresh all dropdowns for this item"""
        if item_name in self.texture_displays:
            display_frame = self.texture_displays[item_name]
            for widget in display_frame.winfo_children():
                if isinstance(widget, ImageDropdown):
                    widget.selected_textures = self.item_textures.get(item_name, [])
                    widget.create_popup()

    def update_texture_display(self, item_name: str):
        """Update texture display with exact sizes, wrapping, and state verification"""
        logger.info(f"Updating texture display for {item_name} in {self.category}")
        
        # Validate widget existence
        if item_name not in self.texture_displays or not self.texture_displays[item_name].winfo_exists():
            logger.error(f"Texture display for {item_name} does not exist")
            return
            
        display_frame = self.texture_displays[item_name]
        
        # Always use ground truth from main app
        texture_category = f"{self.category}_textures"
        current_textures = self.main_app.updated_dictionary.get(texture_category, {}).get(item_name, [])
        logger.info(f"Current verified textures for {item_name}: {current_textures}")

        # Nuclear clear of existing widgets
        for widget in display_frame.winfo_children():
            logger.info(f"Destroying widget: {type(widget).__name__}")
            widget.destroy()

        if not current_textures:
            logger.error("No textures - showing empty state")
            ctk.CTkLabel(display_frame, text="No textures selected",height=100).pack()
            return

        # Dynamic sizing logic
        num_textures = len(current_textures)
        size_map = {1: 100, 2: 100, 3: 75, 4: 65, 5: 65}
        size = size_map.get(num_textures, 65)
        items_per_row = min(num_textures, 4 if size == 65 else num_textures)
        
        logger.info(f"Rendering {num_textures} texture(s) at {size}px")

        # Grid layout rebuild
        row = col = 0
        for idx, texture in enumerate(current_textures):
            if idx % items_per_row == 0 and idx != 0:
                row += 1
                col = 0

            texture_frame = ctk.CTkFrame(
                display_frame, 
                width=size, 
                height=size,
                fg_color="transparent"
            )
            texture_frame.grid(row=row, column=col, padx=(0, 2), pady=(0, 2))

            texture_label = ctk.CTkLabel(texture_frame, text="", width=size, height=size)
            texture_label.pack()

            # Async image load with error handling
            image_path = os.path.join(
                self.base_path, self.category, item_name, 
                "textures", "pics", texture
            )
            self.image_loader.load_image(
                image_path,
                (size, size),
                lambda photo, lbl=texture_label: lbl.configure(image=photo) if photo else None
            )
            texture_label.bind("<Button-1>", lambda e, t=texture: self.remove_texture(item_name, t))
            
            col += 1

        logger.info(f"Texture display updated for {item_name}")

    def update_texture_with_preview(self, item_name: str, texture: str, preview_label: ctk.CTkLabel):
        """Update texture and show preview"""
        self.update_callback(f"{self.category}_textures", item_name, texture)
        
        if texture:
            image_path = os.path.join(self.base_path, self.category, item_name, "textures", "pics", texture)
            self.image_loader.load_image(
                image_path,
                (50, 50),
                lambda photo: preview_label.configure(image=photo, text="") if photo else None
            )
        else:
            preview_label.configure(image=None, text="") 
                
    def prev_page(self):
        """Save current page state before navigation"""
        self._save_current_state()  # Save selections before switching pages
        if self.current_page > 0:
            self.current_page -= 1
            self.load_current_page()
            self.update_navigation()
            # Scroll to the top of the page
            self.scrollable_frame._parent_canvas.yview_moveto(0.0)  # Reset scroll position to top

    def next_page(self):
        """Save current page state before navigation"""
        self._save_current_state()  # Save selections before switching pages
        total_pages = (len(self.all_items) + self.items_per_page - 1) // self.items_per_page
        if self.current_page < total_pages - 1:
            self.current_page += 1
            self.load_current_page()
            self.update_navigation()
            # Scroll to the top of the page
            self.scrollable_frame._parent_canvas.yview_moveto(0.0)  # Reset scroll position to top

    def _save_current_state(self):
        """Persist current selections to main app's state"""
        texture_category = f"{self.category}_textures"
        logger.info(f"Saving state for {texture_category}: {self.item_textures}")
        # Update main app's dictionary with deep copy
        self.main_app.updated_dictionary[texture_category] = {
            item: textures.copy() 
            for item, textures in self.item_textures.items()
            if textures
        }
        logger.info(f"Saved state for {texture_category}")


    def cleanup(self):
        """Nuclear cleanup for category view"""
        logger.info(f"Cleaning up {self.category} view")
        
        # 1. Stop image loader
        self.image_loader.stop()
        
        # 2. Destroy all widgets
        for widget in self.winfo_children():
            widget.destroy()
        
        # 3. Clear references
        self.master = None
        self.image_loader = None
        logger.info(f"{self.category} view resources released")

class SpecialSelectionWindow(ctk.CTkToplevel):
    def __init__(self, parent, categories: List[str], option_name: str, update_callback, get_preview_image, image_loader, checkboxes, updated_dictionary):
        super().__init__(parent)
        self.parent = parent  # Store the parent reference
        self.title(f"Select {option_name}")
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.geometry("800x600")
        self.option_name = option_name
        self.categories = categories
        self.update_callback = update_callback
        self.get_preview_image = get_preview_image
        self.image_loader = image_loader
        self.category_view = None
        self.checkboxes = checkboxes
        self.updated_dictionary = updated_dictionary  # Store the updated_dictionary

        # Determine the base path
        if option_name == "head":
            self.base_path = os.path.join(os.path.dirname(MALE_PATH), "face")  # Outside MALE_PATH/FEMALE_PATH
        else:
            self.base_path = os.path.join(MALE_PATH if parent.gender_var.get() == "male" else FEMALE_PATH, "body")

        # Log the base path
        logger.info(f"Base path for {option_name}: {self.base_path}")

        # Initialize state
        self.current_page = 0
        self.items_per_page = 10
        self.all_items = None
        self.selected_model = None
        self.selected_texture = None

        # Create UI components
        self.create_ui()

        # Load existing selections
        self.load_existing_selections()

    def create_ui(self):
        """Create the UI for selecting models and textures."""
        # Category buttons frame at the top
        self.buttons_frame = ctk.CTkFrame(self)
        self.buttons_frame.pack(fill="x", padx=10, pady=5)

        # Add buttons for model and texture selection
        self.model_button = ctk.CTkButton(
            self.buttons_frame,
            text="Model",
            command=lambda: self.show_category("model"),
            fg_color=PURPLE,
            hover_color=HOVER_PURPLE,
            width=100
        )
        self.model_button.pack(side="left", padx=5)

        self.texture_button = ctk.CTkButton(
            self.buttons_frame,
            text="Texture",
            command=lambda: self.show_category("texture"),
            fg_color=PURPLE,
            hover_color=HOVER_PURPLE,
            width=100
        )
        self.texture_button.pack(side="left", padx=5)

        # Scrollable frame for items
        self.scrollable_frame = ctk.CTkScrollableFrame(self)
        self.scrollable_frame.pack(expand=True, fill="both", padx=10, pady=10)

        # Navigation frame at the bottom
        self.nav_frame = ctk.CTkFrame(self)
        self.nav_frame.pack(fill="x", padx=10, pady=5)

        # Previous button
        self.prev_button = ctk.CTkButton(
            self.nav_frame,
            text="Previous",
            width=100,
            command=self.prev_page,
            fg_color=PURPLE,
            hover_color=HOVER_PURPLE
        )
        self.prev_button.pack(side="left", padx=5)

        # Next button
        self.next_button = ctk.CTkButton(
            self.nav_frame,
            text="Next",
            width=100,
            command=self.next_page,
            fg_color=PURPLE,
            hover_color=HOVER_PURPLE
        )
        self.next_button.pack(side="right", padx=5)

        # Page label
        self.page_label = ctk.CTkLabel(self.nav_frame, text="Page 1")
        self.page_label.pack(side="left", padx=5)

        # Load the first page (models by default)
        self.show_category("model")

    def get_models(self):
        """Get available models."""
        model_path = os.path.join(self.base_path, "model")
        
        # Check if the model path exists
        if not os.path.exists(model_path):
            create_message_box("error", "Models do not exist...", 5000)
            logger.error(f"There are no models in {model_path}")
            return []
        
        # Get all subdirectories in the model folder
        models = sorted(
            [item for item in os.listdir(model_path) if os.path.isdir(os.path.join(model_path, item))],
            key=lambda x: int(x) if x.isdigit() else float('inf')
        )
        
        return models

    def get_textures(self):
        """Get available textures."""
        texture_path = os.path.join(self.base_path, "textures")
        
        # Check if the texture path exists
        if not os.path.exists(texture_path):
            logger.error(f"Texture path does not exist: {texture_path}")
            return []
        
        # Get all PNG files in the texture folder
        textures = sorted(
            [item for item in os.listdir(texture_path) if os.path.isdir(os.path.join(texture_path, item))],
            key=lambda x: int(x) if x.isdigit() else float('inf')
        )
        
        return textures

    def show_category(self, category: str):
        """Switch between model and texture selection."""
        self.current_category = category
        self.current_page = 0

        if category == "model":
            # Load models
            self.all_items = self.get_models()
            self.load_current_page()
        elif category == "texture":
            # Check if at least one model is selected
            if self.option_name in self.updated_dictionary and self.updated_dictionary[self.option_name]:
                # Load textures
                self.all_items = self.get_textures()
                self.load_current_page()
            else:
                # Show error message if no model is selected
                create_message_box("Error", "Please Select At Least One Model First.", 4000)
        else:
            logger.error("Wrong category in show_category")      

    def load_existing_selections(self):
        """Load existing selections from the parent's state."""
        if self.option_name in self.parent.updated_dictionary:
            # Load the selected model
            self.selected_model = self.parent.updated_dictionary[self.option_name][0] if self.parent.updated_dictionary[self.option_name] else None

            # Load the selected texture and texture file name
            if f"{self.option_name}_textures" in self.parent.updated_dictionary:
                texture_data = self.parent.updated_dictionary[f"{self.option_name}_textures"]
                if texture_data:
                    # Extract the texture and texture file name
                    self.selected_texture = list(texture_data.keys())[0]  # The texture key (e.g., "head_diff_001_a_whi.png")
                    self.texture_file_name = texture_data[self.selected_texture][0]  # The texture file name (e.g., "head_diff_001_a_whi.png")
                else:
                    self.selected_texture = None
                    self.texture_file_name = None
            else:
                self.selected_texture = None
                self.texture_file_name = None

        # Update UI to reflect existing selections
        if self.selected_model:
            self.show_category("texture")
            if self.selected_texture and self.texture_file_name:
                self.update_callback(self.option_name, self.selected_model, self.selected_texture, self.texture_file_name, True)
                
    def load_current_page(self):
        """Load items for the current page."""
        # Clear existing items
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        # Calculate start and end indices
        start_idx = self.current_page * self.items_per_page
        end_idx = min(start_idx + self.items_per_page, len(self.all_items))

        # Load items for the current page
        for item in self.all_items[start_idx:end_idx]:
            self.create_item_widget(item)

        # Restore the selected state for models
        if self.current_category == "model":
            if self.option_name in self.updated_dictionary:
                selected_models = self.updated_dictionary[self.option_name]
                for widget in self.scrollable_frame.winfo_children():
                    if isinstance(widget, ctk.CTkFrame):
                        checkbox = widget.winfo_children()[0]  # First child is the checkbox
                        item_name = checkbox._text.split()[-1]  # Extract model name
                        if item_name in selected_models:
                            checkbox.select()  # Check the checkbox for selected models

        # Update navigation buttons
        self.update_navigation()

    def create_item_widget(self, item):
        """Create a widget for a single item."""
        frame = ctk.CTkFrame(self.scrollable_frame)
        frame.pack(fill="x", padx=10, pady=5)

        # Checkbox for selecting the item
        var = ctk.BooleanVar()
        checkbox = ctk.CTkCheckBox(
            frame,
            text=f"{self.current_category.capitalize()} {item}",
            variable=var,
            fg_color=PURPLE,
            hover_color=HOVER_PURPLE,
            command=lambda i=item: self.select_item(i, var.get())
        )
        checkbox.pack(side="left", padx=5)

        # Preview image
        preview_label = ctk.CTkLabel(frame, width=100, height=100, text="")
        preview_label.pack(side="left", padx=5)

        # Load preview image
        if self.option_name == "head":
            if self.current_category == "model":
                preview_path = os.path.join(self.base_path, "model", item, f"head_{int(item):03d}_r.png")
            else:
                # For textures, the item is the filename (e.g., head_diff_000_a_whi.png)
                preview_path = os.path.join(self.base_path, "textures", item, f"head_diff_{int(item):03d}_a_whi.png")
        else:
            if self.current_category == "model":
                preview_path = os.path.join(self.base_path, "model", item, f"uppr_{int(item):03d}_r.png")
            else:
                # For textures, the item is the filename (e.g., head_diff_000_a_whi.png)
                preview_path = os.path.join(self.base_path, "textures", item, f"uppr_diff_{int(item):03d}_a_whi.png") 

        if os.path.exists(preview_path):
            # Use the image loader to load the image asynchronously
            self.image_loader.load_image(
                preview_path,
                (100, 100),
                lambda photo: self.after(0, self._update_preview_label, preview_label, photo)
            )
        else:
            logger.warning(f"Preview image not found for {self.current_category} {item}")

    def select_item(self, item, selected):
        """Handle item selection."""
        if selected:
            if self.option_name == "head":
                if self.current_category == "model":
                    # Add the selected model to the list
                    if self.option_name not in self.updated_dictionary:
                        self.updated_dictionary[self.option_name] = []
                    if item not in self.updated_dictionary[self.option_name]:
                        self.updated_dictionary[self.option_name].append(item)
                        logger.info(f"Added model {item} to {self.option_name} in updated_dictionary")
                    self.update_callback(self.option_name, item, None, None, True)
                    self.show_category("texture")  # Automatically switch to texture selection
                elif self.current_category == "texture":
                    # Uncheck all other textures
                    self._uncheck_all_textures()
                    
                    # Update the selected texture
                    self.selected_texture = item
                    
                    # Check the checkbox for the newly selected texture
                    self._check_selected_texture(item)
                    
                    # Get the actual texture file name
                    texture_path = os.path.join(self.base_path, "textures", item)
                    texture_files = [f for f in os.listdir(texture_path) if f.endswith('.png')]
                    if texture_files:
                        texture_name = texture_files[0]  # Assuming the first texture file is the one we want
                        # Save the selection immediately using the parent's update_selection method
                        self.update_callback(self.option_name, self.selected_model, self.selected_texture, texture_name, True)
                        logger.info(f"Added texture {texture_name} to {self.option_name}_textures in updated_dictionary")
            elif self.option_name == "body":
                if self.current_category == "model":
                    # Add the selected model to the list
                    if self.option_name not in self.updated_dictionary:
                        self.updated_dictionary[self.option_name] = []
                    if item not in self.updated_dictionary[self.option_name]:
                        self.updated_dictionary[self.option_name].append(item)
                        logger.info(f"Added model {item} to {self.option_name} in updated_dictionary")
                    self.update_callback(self.option_name, item, None, None, True)
                elif self.current_category == "texture":
                    # Uncheck all other textures
                    self._uncheck_all_textures()
                    
                    # Update the selected texture
                    self.selected_texture = item
                    
                    # Check the checkbox for the newly selected texture
                    self._check_selected_texture(item)
                    
                    # Get the actual texture file name
                    texture_path = os.path.join(self.base_path, "textures", item)
                    texture_files = [f for f in os.listdir(texture_path) if f.endswith('.png')]
                    if texture_files:
                        texture_name = texture_files[0]  # Assuming the first texture file is the one we want
                        # Save the selection immediately using the parent's update_selection method
                        self.update_callback(self.option_name, self.selected_model, self.selected_texture, texture_name, True)
                        logger.info(f"Added texture {texture_name} to {self.option_name}_textures in updated_dictionary")
        else:
            # Handle deselection
            if self.current_category == "model":
                # Remove the deselected model from the list
                if self.option_name in self.updated_dictionary and item in self.updated_dictionary[self.option_name]:
                    self.updated_dictionary[self.option_name].remove(item)
                    logger.info(f"Removed model {item} from {self.option_name} in updated_dictionary")
                self.update_callback(self.option_name, item, None, None, False)  # Clear model selection
            elif self.current_category == "texture":
                self.selected_texture = None
                self.update_callback(self.option_name, self.selected_model, None, None, False)  # Clear texture selection
                logger.info(f"Removed texture from {self.option_name}_textures in updated_dictionary")

        # Save the current selections when an item is selected or deselected
        self._save_selections()

    def update_navigation(self):
        """Update navigation buttons and page label."""
        total_pages = (len(self.all_items) + self.items_per_page - 1) // self.items_per_page
        self.prev_button.configure(state="normal" if self.current_page > 0 else "disabled")
        self.next_button.configure(state="normal" if self.current_page < total_pages - 1 else "disabled")
        self.page_label.configure(text=f"Page {self.current_page + 1} of {total_pages}")

    def prev_page(self):
        """Go to the previous page."""
        if self.current_page > 0:
            # Save the current selections before switching pages
            self._save_selections()
            self.current_page -= 1
            self.load_current_page()
            # Scroll to the top of the page
            self.scrollable_frame._parent_canvas.yview_moveto(0.0)  # Reset scroll position to top

    def next_page(self):
        """Go to the next page."""
        total_pages = (len(self.all_items) + self.items_per_page - 1) // self.items_per_page
        if self.current_page < total_pages - 1:
            # Save the current selections before switching pages
            self._save_selections()
            self.current_page += 1
            self.load_current_page()
            # Scroll to the top of the page
            self.scrollable_frame._parent_canvas.yview_moveto(0.0)  # Reset scroll position to top

    def _update_preview_label(self, label, photo):
        """Update the preview label with the loaded image."""
        if label.winfo_exists():
            label.configure(image=photo, text="")

    def _check_selected_texture(self, texture):
        """Check the checkbox for the selected texture."""
        for widget in self.scrollable_frame.winfo_children():
            if isinstance(widget, ctk.CTkFrame):
                checkbox = widget.winfo_children()[0]  # First child is the checkbox
                if checkbox._text.split()[-1] == texture:  # Match the texture name
                    checkbox.select()  # Check the checkbox
                    break

    def _uncheck_all_textures(self):
        """Uncheck all texture checkboxes."""
        for widget in self.scrollable_frame.winfo_children():
            if isinstance(widget, ctk.CTkFrame):
                checkbox = widget.winfo_children()[0]  # First child is the checkbox
                checkbox.deselect()  # Uncheck the checkbox

    def _save_selections(self):
        """Save the currently selected models and textures."""
        if self.current_category == "model":
            # Save all selected models
            selected_models = []
            for widget in self.scrollable_frame.winfo_children():
                if isinstance(widget, ctk.CTkFrame):
                    checkbox = widget.winfo_children()[0]  # First child is the checkbox
                    if checkbox.get():
                        selected_models.append(checkbox._text.split()[-1])  # Extract model name
            
            # Append to the existing list of selected models
            if self.option_name not in self.updated_dictionary:
                self.updated_dictionary[self.option_name] = []
            self.updated_dictionary[self.option_name] = list(set(self.updated_dictionary[self.option_name] + selected_models))
            logger.info(f"Saved models for {self.option_name}: {self.updated_dictionary[self.option_name]}")
        elif self.current_category == "texture":
            # Save the selected texture
            for widget in self.scrollable_frame.winfo_children():
                if isinstance(widget, ctk.CTkFrame):
                    checkbox = widget.winfo_children()[0]  # First child is the checkbox
                    if checkbox.get():
                        self.selected_texture = checkbox._text.split()[-1]  # Extract texture name
                        break
            if self.selected_texture:
                texture_category = f"{self.option_name}_textures"
                if texture_category not in self.updated_dictionary:
                    self.updated_dictionary[texture_category] = {}
                texture_path = os.path.join(self.base_path, "textures", self.selected_texture)
                texture_files = [f for f in os.listdir(texture_path) if f.endswith('.png')]
                if texture_files:
                    texture_name = texture_files[0]  # Assuming the first texture file is the one we want
                    self.updated_dictionary[texture_category][self.selected_texture] = [texture_name]
                    logger.info(f"Saved texture for {self.option_name}: {texture_name}")

    def _restore_selections(self):
        """Restore the selected state for items that were previously selected."""
        if self.current_category == "model" and self.selected_model:
            # Restore the selected model
            for widget in self.scrollable_frame.winfo_children():
                if isinstance(widget, ctk.CTkFrame):
                    checkbox = widget.winfo_children()[0]  # First child is the checkbox
                    if checkbox._text.split()[-1] == self.selected_model:
                        checkbox.select()  # Select the checkbox
                        break
        elif self.current_category == "texture" and self.selected_texture:
            # Restore the selected texture
            for widget in self.scrollable_frame.winfo_children():
                if isinstance(widget, ctk.CTkFrame):
                    checkbox = widget.winfo_children()[0]  # First child is the checkbox
                    if checkbox._text.split()[-1] == self.selected_texture:
                        checkbox.select()  # Select the checkbox
                        break

    def _on_close(self):
        """Safe window closure with state saving."""
        logger.info(f"Closing {self.option_name} window")
        
        # Save the selected model and texture
        if self.selected_model and self.selected_texture:
            self.update_callback(self.option_name, self.selected_model, self.selected_texture, True)
        
        # 1. Stop all image loaders
        if hasattr(self, 'category_view'):
            if self.category_view:
                self.category_view.cleanup()
        
        # 2. Remove from window registry
        if self.option_name in self.parent.selection_windows:
            del self.parent.selection_windows[self.option_name]
        
        # 3. Delay destruction for thread cleanup
        self.after(100, self.destroy)
        logger.info("Window closure processed")
        

class ClothesSelectionWindow(ctk.CTkToplevel):
    def __init__(self, parent, categories: List[str], base_path: str,
                 update_callback, get_preview_image, option_name ,image_loader,**kwargs):
        super().__init__(parent)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        # Add these new properties
        self.remaining_textures = {}  # Track textures across closure
        self.category_views = {}  # Track active category views
        self.image_loader = parent.image_loader
        self.main_app = parent
        
        self.title("Select Items")
        self.geometry("800x600")
        
        self.categories = categories
        self.base_path = base_path
        self.update_callback = update_callback
        self.get_preview_image = get_preview_image  # Store the method
        self.option_name = option_name
        self.current_category = None
        self.category_view = None
        
        # Create category buttons frame
        self.buttons_frame = ctk.CTkFrame(self)
        self.buttons_frame.pack(fill='x', padx=10, pady=5)
        
        # Create horizontal scrollable frame
        self.category_buttons_scroll = ctk.CTkScrollableFrame(
            self.buttons_frame, 
            orientation="horizontal", 
            width=600,
            height=50
        )
        self.category_buttons_scroll.pack(fill='x', padx=5, pady=5)
        
        # Add category buttons to the scrollable frame
        for category in categories:
            btn = ctk.CTkButton(
                self.category_buttons_scroll,
                text=category.capitalize(),
                command=lambda cat=category: self.show_category(cat),
                fg_color=PURPLE,
                hover_color=HOVER_PURPLE,
                width=100  # Set a consistent width
            )
            btn.pack(side='left', padx=5)
            
        # Frame for category content
        self.content_frame = ctk.CTkFrame(self)
        self.content_frame.pack(expand=True, fill='both', padx=10, pady=5)
        
        # Show first category by default
        if categories:
            self.show_category(categories[0])
            
    def show_category(self, category: str):
        """Switch to showing a different category"""
        if self.current_category == category:
            return

        # Destroy existing category view completely
        if self.category_view:
            self.category_view.destroy() 
            self.category_view = None

        # Clear the content frame to prevent widget stacking
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        # Create new category view
        self.category_view = CategoryView(
            self.content_frame,
            category,
            self.base_path,
            self.update_callback,
            self.get_preview_image,
            self.main_app
        )
        self.category_view.pack(expand=True, fill='both')
        self.current_category = category

    def _on_close(self):
        """Safe window closure"""
        logger.info(f"Closing {self.option_name} window")
        
        # 1. Stop all image loaders
        if hasattr(self, 'category_view'):
            self.category_view.cleanup()
        
        # 2. Remove from window registry
        if self.option_name in self.master.selection_windows:
            del self.master.selection_windows[self.option_name]
        
        # 3. Delay destruction for thread cleanup
        self.after(100, self.destroy)
        logger.info("Window closure processed")

class PedCreatorGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self._is_destroyed = False
        self.image_loader = AsyncImageLoader.get_instance(self)
        self.protocol("WM_DELETE_WINDOW", self._safe_destroy)

        # Basic window setup
        self.title(f"FiveM Ped Creator - Made By Fucking ! Lucas.exe™")
        self.iconbitmap("images\icon.png") #TODO: fix the icon
        self.geometry("1000x700")
        self.resizable(False, False)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        ctk.set_appearance_mode("dark")

        # Explicitly set the logging level for your logger
        logger.setLevel(logging.DEBUG)


        # Initialize state dictionary with all categories
        self.updated_dictionary = {
            "name": None,
            "accs": [],
            "bags": [],
            "chains": [],
            "decals": [],
            "glasses": [],
            "hairs": [],
            "hats": [],
            "masks": [],
            "pants": [],
            "shirts": [],
            "shoes": [],
            "under_shirt": [],
            "vests": [],
            "watches": [],
            "hands": [],
            "head": [],
            "body": [],
            # Initialize texture categories
            "accs_textures": {},
            "bags_textures": {},
            "chains_textures": {},
            "decals_textures": {},
            "glasses_textures": {},
            "hairs_textures": {},
            "hats_textures": {},
            "masks_textures": {},
            "pants_textures": {},
            "shirts_textures": {},
            "shoes_textures": {},
            "under_shirt_textures": {},
            "vests_textures": {},
            "watches_textures": {},
            "hands_textures": {},
            "head_textures": {},
            "body_textures": {}
        }
        
        # Log the initial state of the dictionary
        logging.debug(f"Initial updated_dictionary: {self.updated_dictionary}")
        
        self.clothes_path = MALE_PATH
        self.font = "Supernova"
        self.iconpath = "images/icon.png"
        
        # Dictionary to store selection windows
        self.selection_windows = {}
        
        # Create and setup main UI components
        self.setup_navigation_frame()
        self.setup_builder_frame()
        
        # Configure initial state
        self.show_builder()

    def get_preview_image(self, item_path: str):
        """Get the first PNG file in the textures/pics folder to use as preview"""
        preview_path = os.path.join(item_path, "textures", "pics")
        if os.path.exists(preview_path):
            files = sorted([f for f in os.listdir(preview_path) if f.endswith('.png')])
            if files:
                return os.path.join(preview_path, files[0])
        return None

    def open_special_selection(self, option_name: str, categories: List[str]):
        """Open a special selection window for Head and Body categories."""
        logger.info(f"Opening special selection window for {option_name}")
        
        if option_name in self.selection_windows:
            self.selection_windows[option_name].lift()
            return

        window = SpecialSelectionWindow(
            self,  # Pass the parent reference (PedCreatorGUI instance)
            categories,  # Categories (e.g., ["model", "texture"])
            option_name,  # Option name (e.g., "Head" or "Body")
            self.update_special_selection,  # Update callback method
            self.get_preview_image,  # Method to get preview images
            self.image_loader,  # Async image loader
            self.checkboxes,  # Checkboxes dictionary
            self.updated_dictionary  # Pass the updated_dictionary
        )
        window.transient(self)
        window.grab_set()
        self.selection_windows[option_name] = window

        window.protocol("WM_DELETE_WINDOW", lambda: self.on_special_selection_window_close(option_name)) 

    def open_clothes_selection(self, option_name: str, categories: List[str]):
        """Open a new window for clothes selection with dynamic loading"""
        if option_name in self.selection_windows:
            self.selection_windows[option_name].lift()
            return
            
        window = ClothesSelectionWindow(
            self, 
            categories,
            self.clothes_path,
            self.update_selection,
            self.get_preview_image,
            option_name,
            self.image_loader
        )
        window.transient(self)
        window.grab_set()
        
        self.selection_windows[option_name] = window
        window.protocol("WM_DELETE_WINDOW", lambda: self.on_selection_window_close(option_name))

    def create_option_checkboxes(self):
        """Create checkboxes for all ped options with associated category mappings."""
        options = [
            ("head", 85, 150, ["model", "texture"], True),  # True indicates special handling
            ("hair", 286, 150, ["hairs"], False),  # False indicates not special handling
            ("body", 85, 195, ["model", "texture"], True),  # True indicates special handling
            ("accessories", 286, 195, ["accs", "bags", "chains", "glasses", "hats", "masks", "watches"], False),  # False indicates not special handling
            ("clothes", 85, 240, ["shirts", "pants", "shoes", "under_shirt", "vests", "decals"], False)  # False indicates not special handling
        ]

        self.checkboxes = {}
        for text, x, y, categories, special in options:
            frame = ctk.CTkFrame(self.builder_frame)
            frame.grid(row=1, column=0, sticky="nw", padx=x, pady=y)

            # Create a BooleanVar to track the checkbox state
            var = ctk.BooleanVar()

            checkbox = ctk.CTkCheckBox(
                frame,
                text=text.capitalize(),
                font=ctk.CTkFont(size=17, family=self.font),
                fg_color=PURPLE,
                hover_color=HOVER_PURPLE,
                variable=var,  # Link the checkbox to the BooleanVar
                command=lambda t=text, cats=categories: self.on_checkbox_click(t, cats)
            )
            checkbox.pack(side='left', padx=5)

            edit_button = ctk.CTkButton(
                frame,
                text="Edit",
                font=ctk.CTkFont(family=self.font, size=13),
                width=60,
                fg_color=PURPLE,
                hover_color=HOVER_PURPLE,
                command=lambda t=text, cats=categories, special=special: self.edit_selections(t, cats, special)
            )
            edit_button.pack(side='left', padx=5)
            edit_button.configure(state='disabled')

            self.checkboxes[text] = {
                "checkbox": checkbox,
                "categories": categories,
                "edit_button": edit_button,
                "var": var  # Store the BooleanVar for later use
            }

    def create_clothes_item_widget(self, parent, category: str, item_name: str, item_path: str):
        """Create a widget for each clothes item with texture selection"""
        frame = ctk.CTkFrame(parent)
        frame.pack(fill='x', padx=5, pady=5)
        
        # Left side: Item checkbox and image
        left_frame = ctk.CTkFrame(frame)
        left_frame.pack(side='left', padx=5)
        
        var = ctk.BooleanVar()
        checkbox = ctk.CTkCheckBox( 
            left_frame,
            text=f"Item {item_name}",
            variable=var,
            fg_color=PURPLE,
            hover_color=HOVER_PURPLE,
            command=lambda: self.update_selection(category, item_name, var.get())
        )
        
        if item_name in self.updated_dictionary.get(category, []):
            var.set(True)
            
        checkbox.pack(side='left', padx=5)
        
        # Item preview image
        image_label = ctk.CTkLabel(left_frame, width=100, height=100, text="Loading...")
        image_label.pack(side='left', padx=5)

        # Load preview image using AsyncImageLoader
        preview_image = self.get_preview_image(item_path)
        if preview_image:
            self.image_loader.load_image(
                preview_image,
                (100, 100),
                lambda photo: image_label.configure(image=photo, text="") if photo else None
            )

        # Right side: Texture selection with images
        right_frame = ctk.CTkFrame(frame)
        right_frame.pack(side='right', padx=5)
        
        textures_path = os.path.join(item_path, "textures", "pics")
        if os.path.exists(textures_path):
            texture_label = ctk.CTkLabel(right_frame, text="Texture:")
            texture_label.pack(side='left', padx=5)
            
            # Get current texture if any
            current_texture = self.updated_dictionary.get(f"{category}_textures", {}).get(item_name)
            
            # Create image dropdown with proper image_loader
            dropdown = ImageDropdown(
                right_frame,
                images_path=textures_path,
                current_value=current_texture,
                image_loader=self.image_loader,  # Added this line
                command=lambda t: self.update_texture(category, item_name, t)
            )
            dropdown.pack(side='left', padx=5)

    def edit_selections(self, option_name: str, categories: List[str], is_special: bool = False):
        if is_special:
            # Handle Head and Body categories
            self.open_special_selection(option_name, categories)
        else:
            # Handle normal categories
            self.open_clothes_selection(option_name, categories)
            
    def on_checkbox_click(self, option_name: str, categories: List[str]):
        """Handle checkbox clicks for options."""
        checkbox_info = self.checkboxes[option_name]
        is_checked = checkbox_info["checkbox"].get()
        logger.info(f"Checkbox clicked: {option_name} | Checked: {is_checked}")

        if is_checked:
            # Enable the edit button
            checkbox_info["edit_button"].configure(state="normal")
            
            # Open the selection window
            if option_name in ["head", "body"]:
                # Handle special categories (head, body)
                self.open_special_selection(option_name, categories)
            else:
                # Handle normal categories
                self.open_clothes_selection(option_name, categories)
        else:
            # Disable the edit button
            checkbox_info["edit_button"].configure(state="disabled")
            
            # Clear data and textures for the categories
            for category in categories:
                logger.info(f"Resetting {category} and {category}_textures")
                self.updated_dictionary[category] = []
                self.updated_dictionary[f"{category}_textures"] = {}

            # Log the updated dictionary state
            logging.debug(f"Updated dictionary after clearing data: {self.updated_dictionary}")

            # Destroy the selection window if it exists
            if option_name in self.selection_windows:
                logger.info(f"Destroying window for {option_name}")
                window = self.selection_windows[option_name]
                window.destroy()
                del self.selection_windows[option_name]

        # Sync checkbox states
        self._sync_checkbox_states()
        
    def _actually_clear_data(self, option_name, categories):
        """Thread-safe data clearance"""
        logger.info("Executing safe data clearance")

    def refresh_all_textures(self):
        """Force refresh all texture displays"""
        logger.info("Global texture refresh initiated")
        for window in self.selection_windows.values():
            if hasattr(window, 'category_view') and window.category_view:
                window.category_view.load_current_page()

    def _refresh_builder_frame(self):
        """Refresh visible components without full recreation"""
        logger.info("Refreshing builder frame")
        # Update existing widgets
        for child in self.builder_frame.winfo_children():
            if isinstance(child, ctk.CTkFrame):
                for subchild in child.winfo_children():
                    if isinstance(subchild, ctk.CTkCheckBox):
                        subchild.configure(text=f"{subchild._text.split()[-1]}")
        # Force GUI update
        self.update_idletasks()

    def update_texture(self, category: str, item_name: str, texture: str):
        """Update the texture selection for an item"""
        texture_category = f"{category}_textures"
        
        if texture_category not in self.updated_dictionary:
            self.updated_dictionary[texture_category] = {}
            
        if texture:
            if category not in self.updated_dictionary:
                self.updated_dictionary[category] = []
            if item_name not in self.updated_dictionary[category]:
                self.updated_dictionary[category].append(item_name)
            self.updated_dictionary[texture_category][item_name] = texture
        else:
            if item_name in self.updated_dictionary[texture_category]:
                del self.updated_dictionary[texture_category][item_name]

        # Log the updated dictionary state
        logging.debug(f"Updated dictionary after texture change: {self.updated_dictionary}")

    def update_special_selection(self, category: str, model: str, texture: str | None, texture_name: str | None, selected: bool):
        """Update selection for special categories (e.g., head, body)."""
        if selected:
            # Add the model/texture to the list
            if category not in self.updated_dictionary:
                self.updated_dictionary[category] = []
            if model and model not in self.updated_dictionary[category]:
                self.updated_dictionary[category].append(model)
            
            # Save the texture if provided
            if texture and texture_name:
                texture_category = f"{category}_textures"
                if texture_category not in self.updated_dictionary:
                    self.updated_dictionary[texture_category] = {}
                self.updated_dictionary[texture_category][texture] = [texture_name]
        else:
            # Remove the model/texture from the list
            if category in self.updated_dictionary and model in self.updated_dictionary[category]:
                self.updated_dictionary[category].remove(model)
            
            # Remove the texture if provided
            if texture:
                texture_category = f"{category}_textures"
                if texture_category in self.updated_dictionary and texture in self.updated_dictionary[texture_category]:
                    del self.updated_dictionary[texture_category][texture]

        # Log the updated dictionary state
        logging.debug(f"Updated dictionary after selection change: {self.updated_dictionary}")

        # Sync checkbox states
        self._sync_checkbox_states()

    def update_selection(self, category, item_name, selected):
        """Central state update with texture awareness."""
        logger.debug(f"Updating selection: category={category}, item_name={item_name}, selected={selected}")
        
        if selected and item_name not in self.updated_dictionary[category]:
            logger.info(f"Adding item: {item_name} to {category}")
            self.updated_dictionary[category].append(item_name)
        elif not selected and item_name in self.updated_dictionary[category]:
            logger.info(f"Removing item: {item_name} from {category}")
            self.updated_dictionary[category].remove(item_name)
     
        # Log the updated dictionary state
        logging.debug(f"Updated dictionary after selection change: {self.updated_dictionary}")
        
        return self.updated_dictionary.get(category, [] if not category.endswith('_textures') else {})
        
    def on_selection_window_close(self, option_name: str):
        """Properly handle window close and maintain selections"""
        if option_name in self.selection_windows:
            selection_window = self.selection_windows[option_name]
            
            # Save state before closing
            if hasattr(selection_window.category_view, 'item_textures'):
                # Get the specific texture category for the current option_name
                texture_category = f"{option_name}_textures"
                
                # Ensure the texture category exists in the updated dictionary
                if texture_category not in self.updated_dictionary:
                    self.updated_dictionary[texture_category] = {}
                
                # Only update textures for the specific category being closed
                for item_name, textures in selection_window.category_view.item_textures.items():
                    # Only update textures for items that belong to the current category
                    if item_name in self.updated_dictionary.get(option_name, []):
                        if textures:
                            self.updated_dictionary[texture_category][item_name] = textures.copy()
                        else:
                            # Remove the item if it has no textures
                            if item_name in self.updated_dictionary[texture_category]:
                                del self.updated_dictionary[texture_category][item_name]
            
            # Destroy the window and remove it from the selection_windows dictionary
            selection_window.destroy()
            del self.selection_windows[option_name]
            
        # Log the updated dictionary state
        logging.debug(f"Updated dictionary after window close: {self.updated_dictionary}")

        # Update checkbox states
        self._update_checkbox_states(option_name)

    def on_special_selection_window_close(self, option_name: str):
        """Handle window close for special selections (e.g., head, body)."""
        if option_name in self.selection_windows:
            selection_window = self.selection_windows[option_name]
            
            # Save state before closing
            if hasattr(selection_window, 'selected_model') and hasattr(selection_window, 'selected_texture'):
                # Save the selected model and texture
                if selection_window.selected_model and selection_window.selected_texture:
                    self.updated_dictionary[option_name] = [selection_window.selected_model]
                    self.updated_dictionary[f"{option_name}_textures"] = {selection_window.selected_texture: [selection_window.selected_texture]}
                else:
                    # Clear the selection if no model or texture is selected
                    self.updated_dictionary[option_name] = []
                    self.updated_dictionary[f"{option_name}_textures"] = {}

            # Destroy the window and remove it from the selection_windows dictionary
            selection_window.destroy()
            del self.selection_windows[option_name]
            
        # Log the updated dictionary state
        logging.debug(f"Updated dictionary after window close: {self.updated_dictionary}")

        # Update checkbox states
        self._update_checkbox_states(option_name)

    def _update_checkbox_states(self, option_name: str):
        """Update checkbox states after window closure."""
        has_selections = False

        # Check if this is a special selection (e.g., head, body)
        if option_name in ["head", "body"]:
            # Special handling: both model and texture must be selected
            if (self.updated_dictionary.get(option_name) and
                self.updated_dictionary.get(f"{option_name}_textures")):
                has_selections = True
        else:
            # Normal handling: check if any category has selections
            for category in self.checkboxes[option_name]["categories"]:
                if (self.updated_dictionary.get(category) and
                    len(self.updated_dictionary[category]) > 0):
                    has_selections = True
                    break

        # Update checkbox and edit button states
        if not has_selections:
            self.checkboxes[option_name]["checkbox"].deselect()
            self.checkboxes[option_name]["edit_button"].configure(state='disabled')
        else:
            self.checkboxes[option_name]["checkbox"].select()
            self.checkboxes[option_name]["edit_button"].configure(state='normal')

    def setup_navigation_frame(self):
        """Setup the navigation sidebar"""
        self.navigation_frame = ctk.CTkFrame(self, corner_radius=0)
        self.navigation_frame.grid(row=0, column=0, sticky="nsew")
        self.navigation_frame.grid_rowconfigure(4, weight=1)

        logo = Image.open(self.iconpath)            
        image = ctk.CTkImage(logo, size=(50,50))

        self.navigation_frame_label = ctk.CTkLabel(
            self.navigation_frame,
            text="   FiveM Ped Creator",
            image=image,
            compound="left",
            font=ctk.CTkFont(size=15, weight="bold", family=self.font)
        )
        self.navigation_frame_label.grid(row=0, column=0, padx=20, pady=20)

        self.dashboard_button = ctk.CTkButton(
            self.navigation_frame,
            corner_radius=0,
            height=40,
            border_spacing=10,
            text="Builder",
            font=ctk.CTkFont(family=self.font, size=13),
            fg_color="transparent",
            text_color=("gray10", "gray90"),
            hover_color=("gray70", "gray30"),
            anchor="w",
            command=self.show_builder
        )
        self.dashboard_button.grid(row=1, column=0, sticky="ew")

    def _sync_checkbox_states(self):
        """Synchronize checkboxes with the updated_dictionary."""
        logger.info("Synchronizing checkbox states")
        for option_name, checkbox_info in self.checkboxes.items():
            has_selections = False

            # Special handling for head and body
            if option_name in ["head", "body"]:
                # Check if both model and texture are selected
                if (self.updated_dictionary.get(option_name) and
                    self.updated_dictionary.get(f"{option_name}_textures")):
                    has_selections = True
            else:
                # Normal handling for other categories
                for category in checkbox_info["categories"]:
                    if (self.updated_dictionary.get(category) and
                        len(self.updated_dictionary[category]) > 0):
                        has_selections = True
                        break

            # Update checkbox and edit button states
            checkbox = checkbox_info["checkbox"]
            edit_button = checkbox_info["edit_button"]
            var = checkbox_info["var"]  # Get the BooleanVar linked to the checkbox

            if has_selections:
                var.set(True)  # Set the BooleanVar to True
                edit_button.configure(state="normal")  # Enable the edit button
                logger.debug(f"Checkbox for {option_name} is checked, edit button enabled")
            else:
                var.set(False)  # Set the BooleanVar to False
                edit_button.configure(state="disabled")  # Disable the edit button
                logger.debug(f"Checkbox for {option_name} is unchecked, edit button disabled")

        # Force UI refresh
        self.update_idletasks()

    def setup_builder_frame(self):
        """Setup the main builder frame"""
        self.builder_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.builder_frame.grid_columnconfigure(0, weight=1)
        
        self.name_entry = ctk.CTkEntry(
            self.builder_frame,
            width=570,
            height=35,
            font=ctk.CTkFont(size=15, family=self.font),
            placeholder_text="Enter Ped Name"
        )
        self.name_entry.grid(row=0, column=0, sticky="nw", padx=15, pady=20)

        self.options_label = ctk.CTkLabel(
            self.builder_frame,
            text="Ped Options",
            font=ctk.CTkFont(size=35, weight="bold", family=self.font)
        )
        self.options_label.grid(row=1, column=0, sticky="n", padx=15, pady=0)

        self.create_option_checkboxes()

        self.build_button = ctk.CTkButton(
            self.builder_frame,
            width=250,
            text="Build",
            font=ctk.CTkFont(size=35, family=self.font),
            fg_color=PURPLE,
            hover_color=HOVER_PURPLE,
            command=self.build_ped
        )
        self.build_button.grid(row=1, column=0, sticky="ne", padx=85, pady=475)

        # Add gender selection dropdown
        self.gender_var = ctk.StringVar(value="male")  # Default to male

        # Create a frame to hold the gender label and menu together
        self.gender_frame = ctk.CTkFrame(self.builder_frame)
        self.gender_frame.grid(row=1, column=0, sticky="nw", padx=85, pady=475)

        # Add label to the frame
        self.gender_label = ctk.CTkLabel(
            self.gender_frame, 
            text="Gender:", 
            font=ctk.CTkFont(size=35, family=self.font)
        )
        self.gender_label.grid(row=0, column=0, padx=(0, 10), pady=0)  # Add padding between label and menu

        # Add dropdown menu to the frame
        self.gender_menu = ctk.CTkOptionMenu(
            self.gender_frame,
            values=["male", "female"],
            font=ctk.CTkFont(size=35, family=self.font),
            variable=self.gender_var,
            fg_color=PURPLE,
            button_color=PURPLE,
            dropdown_fg_color=PURPLE,
            button_hover_color=HOVER_PURPLE,
            dropdown_hover_color=HOVER_PURPLE,
            
            corner_radius=5,
            command=self.update_gender
        )
        self.gender_menu.grid(row=0, column=1, pady=0)

        # Update clothes path based on gender
        self.clothes_path = MALE_PATH if self.gender_var.get() == "male" else FEMALE_PATH
        logger.info(f"Initial clothes path: {self.clothes_path}")   


    def update_gender(self, *args):
        """Update the clothes path when gender changes"""
        self.clothes_path = MALE_PATH if self.gender_var.get() == "male" else FEMALE_PATH
        logger.info(f"Updated clothes path to: {self.clothes_path}")

    def show_builder(self):
        """Show the builder frame"""
        self.builder_frame.grid(row=0, column=1, sticky="nsew")

    def create_progress_window(self):
        """Create a modern progress window"""
        progress_window = ctk.CTkToplevel(self)
        progress_window.title("Building Ped")
        progress_window.geometry("400x150")
        
        # Center the window
        screen_width = progress_window.winfo_screenwidth()
        screen_height = progress_window.winfo_screenheight()
        x = (screen_width - 400) // 2
        y = (screen_height - 150) // 2
        progress_window.geometry(f"+{x}+{y}")
        
        # Make window non-resizable and always on top
        progress_window.resizable(False, False)
        progress_window.transient(self)
        progress_window.grab_set()
        
        # Status label
        self.status_label = ctk.CTkLabel(
            progress_window,
            text="Processing files...",
            font=ctk.CTkFont(size=15, family=self.font)
        )
        self.status_label.pack(pady=(20, 0))
        
        # Progress frame with purple accent
        progress_frame = ctk.CTkFrame(progress_window, fg_color="transparent")
        progress_frame.pack(fill="x", padx=20, pady=10)
        
        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(
            progress_frame,
            width=300,
            height=15,
            corner_radius=10,
            fg_color=("#F0F0F0", "#2A2A2A"),  # Light/dark mode colors
            progress_color=PURPLE,
            border_width=0
        )
        self.progress_bar.pack(pady=10)
        self.progress_bar.set(0)
        
        # Percentage label
        self.percentage_label = ctk.CTkLabel(
            progress_frame,
            text="0%",
            font=ctk.CTkFont(size=13, family=self.font)
        )
        self.percentage_label.pack()
        
        return progress_window

    def update_progress(self, progress_window, progress, status=None):
        """Update progress bar and status"""
        self.progress_bar.set(progress)
        self.percentage_label.configure(text=f"{int(progress * 100)}%")
        if status:
            self.status_label.configure(text=status)
        progress_window.update()

    def build_ped(self):
        name = self.name_entry.get().strip()
        if not name:
            create_message_box("Error", "Please enter a ped name", 3000)
            return
            
        # Check if any items are selected
        any_selected = False
        selected_options = {}
        
        for category, items in self.updated_dictionary.items():
            if not isinstance(items, list) or category == "name":
                continue
                
            if items:
                any_selected = True
                selected_options[category] = items
                
                # Only add textures if they exist and are relevant to the category
                texture_category = f"{category}_textures"
                if texture_category in self.updated_dictionary and self.updated_dictionary[texture_category]:
                    selected_options[texture_category] = self.updated_dictionary[texture_category]
                        
        if not any_selected:
            create_message_box("Error", "Please select at least one item", 5000)
            return
                    
        try:
            # Show progress window
            progress_window = self.create_progress_window()
            
            def progress_callback(progress, status=None):
                self.update_progress(progress_window, progress, status)
            
            # Initialize FileHandler and process the files
            from file_handler import FileHandler
            # Determine base path based on gender
            base_path = MALE_PATH if self.gender_var.get() == "male" else FEMALE_PATH
            
            # Handle Head and Body separately
            if "head" in selected_options:
                # Head is outside MALE_PATH/FEMALE_PATH
                head_base_path = os.path.join(os.path.dirname(MALE_PATH), "face")
                FileHandler.copy_files(selected_options, name, head_base_path, progress_callback)
            if "body" in selected_options:
                # Body is inside MALE_PATH/FEMALE_PATH
                body_base_path = os.path.join(base_path, "body")
                FileHandler.copy_files(selected_options, name, body_base_path, progress_callback)
            
            # Pass base_path to FileHandler
            FileHandler.copy_files(selected_options, name, base_path, progress_callback)

            # Generate the YMT XML file
            selected_options["name"] = name
            generate_xml(selected_options, name,)  # Pass the selected options and ped name to generate_xml
            
            # Complete the progress bar
            self.update_progress(progress_window, 1.0, "Complete!")
            self.after(1000, progress_window.destroy)
            
            # Show success message
            create_message_box("success", f"Ped '{name}' has been successfully created!",5000)

        except Exception as e:
            if 'progress_window' in locals():
                progress_window.destroy()
            create_message_box("error", f"An error occurred while building the ped:\n{str(e)}", 10000)

    def _safe_destroy(self):
        """Proper cleanup sequence"""
        
        if not self._is_destroyed:
            # Stop all image loading first
            self.image_loader.stop()
            
            # Close all selection windows
            for window in list(self.selection_windows.values()):
                window.destroy()
            
            # Then destroy main window
            super().destroy()
            self._is_destroyed = True
            logger.info("Application shutdown complete")

    def destroy(self):
        self._safe_destroy()

def create_message_box(message_type, message, time):
    """Create a custom message box that disappears after 5 seconds"""
    message_box = tk.Toplevel()
    message_box.overrideredirect(True)
    message_box.geometry("300x150")
    
    # Make the window stay on top of all other windows
    message_box.attributes("-topmost", True)
    
    # Set the background color based on the message type
    bg_color = "#d4edda" if message_type == "success" else "#f8d7da"
    fg_color = "#155724" if message_type == "success" else "#721c24"
    
    # Use Canvas for rounded edges
    canvas = tk.Canvas(message_box, width=300, height=150, bg=bg_color, highlightthickness=0)
    canvas.pack(fill="both", expand=True)
    
    # Draw rounded rectangle
    radius = 20
    canvas.create_arc((0, 0, radius*2, radius*2), start=90, extent=90, fill=bg_color, outline=bg_color)
    canvas.create_arc((300-radius*2, 0, 300, radius*2), start=0, extent=90, fill=bg_color, outline=bg_color)
    canvas.create_arc((0, 150-radius*2, radius*2, 150), start=180, extent=90, fill=bg_color, outline=bg_color)
    canvas.create_arc((300-radius*2, 150-radius*2, 300, 150), start=270, extent=90, fill=bg_color, outline=bg_color)
    canvas.create_rectangle((radius, 0, 300-radius, 150), fill=bg_color, outline=bg_color)
    canvas.create_rectangle((0, radius, 300, 150-radius), fill=bg_color, outline=bg_color)
    
    # Add the content
    icon = "✔" if message_type == "success" else "✖"
    canvas.create_text(150, 50, text=icon, font=("Arial", 24), fill=fg_color)
    canvas.create_text(150, 90, text=message, font=("Arial", 12), fill=fg_color, width=260)
    
    # Center the message box
    message_box.update_idletasks()
    screen_width = message_box.winfo_screenwidth()
    screen_height = message_box.winfo_screenheight()
    x = (screen_width - message_box.winfo_width()) // 2
    y = (screen_height - message_box.winfo_height()) // 2
    message_box.geometry(f"+{x}+{y}")
    
    # Ensure the message box is focused
    message_box.focus_force()
    
    # Schedule the message box to close after 5 seconds (5000 milliseconds)
    message_box.after(time, message_box.destroy)

if __name__ == "__main__":
    os.system("python main.py")