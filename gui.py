import customtkinter as ctk
from config import *
from PIL import Image
import os
import sys
from typing import Dict, List, Optional
import tkinter as tk
from tkinter import ttk, messagebox
import threading
from concurrent.futures import ThreadPoolExecutor
import queue
from functools import partial

class ImageDropdown(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        self.images_path = kwargs.pop('images_path', None)
        self.current_value = kwargs.pop('current_value', None)
        self.image_loader = kwargs.pop('image_loader', None)
        self.command = kwargs.pop('command', None)
        self.preview_label = kwargs.pop('preview_label', None)

        super().__init__(master, **kwargs)

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
        """Show the dropdown popup"""
        try:
            if self.popup:
                self.popup.destroy()
            self.create_popup()
            self.place_popup()
            self.popup.deiconify()
        except Exception as e:
            logger.error(f"Error showing popup: {e}")
        
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
        """Create the popup window for the dropdown"""
        # logger.debug("Creating popup for ImageDropdown")

        if self.popup:
            return
            
        self.popup = ctk.CTkToplevel(self)
        self.popup.withdraw()
        self.popup.overrideredirect(True)
        self.popup.attributes("-topmost", True)
        
        container = ctk.CTkFrame(self.popup)
        container.pack(expand=True, fill='both')
        
        scroll_frame = ctk.CTkScrollableFrame(
            container,
            width=150,
            height=200
        )
        scroll_frame.pack(expand=True, fill='both')
        
        try:
            # Get list of texture files
            textures = sorted([t for t in os.listdir(self.images_path) if t.endswith('.png')])
            
            # Load textures in batches for better performance
            self.load_textures_batch(scroll_frame, textures[:10])
            
            if len(textures) > 10:
                self.remaining_textures = textures[10:]
                scroll_frame.bind('<Configure>', self.load_more_textures)
                
        except Exception as e:
            # logger.error("Error loading textures: %s", e)
            PedCreatorGUI.create_message_box("Error", "Error loading textures: {str(e)}")
            error_label = ctk.CTkLabel(scroll_frame, text=f"Error loading textures: {str(e)}")
            error_label.pack(padx=5, pady=2)
        
        # Mouse tracking
        for widget in (self.popup, container, scroll_frame):
            widget.bind('<Enter>', self.cancel_close)
            widget.bind('<Leave>', lambda e: self.schedule_close())
            
    def set_button_image(self, texture):
        """Set the button image to the specified texture."""
        try:
            image_path = os.path.join(self.images_path, texture)
            if os.path.exists(image_path):
                image = Image.open(image_path)
                image.thumbnail((140, 35))
                photo = ctk.CTkImage(image, size=(140, 35))
                self.button.configure(image=photo, text="")
                
                if self.preview_label:
                    preview_photo = ctk.CTkImage(image, size=(100, 100))
                    self.preview_label.configure(image=preview_photo, text="")
            else:
                self.button.configure(text="No Image")
        except Exception as e:
            logger.error(f"Error loading image: {e}")
            self.button.configure(text="Error")    

    def load_textures_batch(self, parent, textures):
        """Load a batch of textures asynchronously."""
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
        # logger.info("Loading More textures")        
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
        if self.close_scheduled and self.popup:
            self.popup.destroy()
            self.popup = None
            
    def select_option(self, texture):
        """Handle texture selection."""
        # Maintain button text
        self.button.configure(text="Select Texture")
        
        if self.command:
            self.command(texture)
        if self.popup:
            self.popup.destroy()
            self.popup = None
            
    def update_preview(self, texture):
        """Update the preview label with the selected texture"""
        # logger.debug("Updating preview for texture: %s", texture)
        if self.preview_label and texture:
            image_path = os.path.join(self.images_path, texture)
            if os.path.exists(image_path):
                self.image_loader.load_image(
                    image_path,
                    (100, 100),  # Preview size
                    lambda photo: self.preview_label.configure(image=photo, text="") if photo else None
                )

class ImageCache:
    def __init__(self):
        self._cache = {}
        self._lock = threading.Lock()
        self._max_size = 50  # Reduced cache size since we're loading less at once
        
    def get(self, key: str) -> Optional[ctk.CTkImage]:
        with self._lock:
            return self._cache.get(key)
            
    def set(self, key: str, value: ctk.CTkImage):
        with self._lock:
            if len(self._cache) >= self._max_size:
                # Remove oldest item if cache is full
                self._cache.pop(next(iter(self._cache)))
            self._cache[key] = value
            
    def clear(self):
        with self._lock:
            self._cache.clear()
            
    def remove_category(self, category_prefix: str):
        """Remove all images from a specific category"""
        with self._lock:
            keys_to_remove = [k for k in self._cache if k.startswith(category_prefix)]
            for k in keys_to_remove:
                self._cache.pop(k)

class AsyncImageLoader:
    def __init__(self, max_workers=2):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.image_cache = ImageCache()
        self.load_queue = queue.Queue()
        self._running = True
        self.worker_thread = threading.Thread(target=self._process_queue)
        self.worker_thread.daemon = True
        self.worker_thread.start()
        
    def load_image(self, image_path: str, size: tuple, callback):
        self.load_queue.put((image_path, size, callback))
        
    def clear_category(self, category: str):
        """Clear cached images for a category"""
        self.image_cache.remove_category(category)
        
    def _process_queue(self):
        while self._running:
            try:
                image_path, size, callback = self.load_queue.get(timeout=1)
                self._load_single_image(image_path, size, callback)
                self.load_queue.task_done()
            except queue.Empty:
                continue
                
    def _load_single_image(self, image_path: str, size: tuple, callback):
        try:
            cached_image = self.image_cache.get(image_path)
            if cached_image:
                callback(cached_image)
                return
                
            image = Image.open(image_path)
            if size:
                image.thumbnail(size)
            photo = ctk.CTkImage(image, size=image.size)
            self.image_cache.set(image_path, photo)
            callback(photo)
        except Exception as e:
            print(f"Error loading image {image_path}: {e}")
            callback(None)
            
    def stop(self):
        self._running = False
        self.executor.shutdown()

class CategoryView(ctk.CTkFrame):
    def __init__(self, parent, category: str, base_path: str, image_loader: AsyncImageLoader, 
                 update_callback, get_preview_image, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.category = category
        self.base_path = base_path
        self.image_loader = image_loader
        self.update_callback = update_callback
        self.get_preview_image = get_preview_image
        self.items_loaded = False
        self.current_page = 0
        self.items_per_page = 10
        
        # Initialize dictionaries for textures
        self.texture_displays = {}
        self.item_textures = {}
        
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
        # Clear existing items
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
            
        start_idx = self.current_page * self.items_per_page
        end_idx = min(start_idx + self.items_per_page, len(self.all_items))
        
        for item in self.all_items[start_idx:end_idx]:
            self.create_item_widget(item)
            
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
            
            # Get current textures from state and display them
            texture_category = f"{self.category}_textures"
            current_textures = self.update_callback(texture_category, item_name, None)
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
                image_loader=self.image_loader,
                command=lambda t: self.add_texture(item_name, t)
            )
            dropdown.pack(side='left', padx=5)

    def update_preview_image(self, label, photo, item_name):
        """Update the preview image, considering current texture state"""
        if item_name in self.item_textures and self.item_textures[item_name]:
            # Don't update if there's a texture selected
            return
        if photo:
            label.configure(image=photo, text="")

    def add_texture(self, item_name: str, texture: str):
        """Add a new texture to the item"""
        texture_category = f"{self.category}_textures"
        
        if texture:
            # Initialize item_textures if needed
            if not hasattr(self, 'item_textures'):
                self.item_textures = {}
            if item_name not in self.item_textures:
                self.item_textures[item_name] = []
                
            # Add new texture if not already present
            if texture not in self.item_textures[item_name]:
                self.item_textures[item_name].append(texture)
                self.update_texture_display(item_name)
                
                # Update the selection state with all textures
                self.update_callback(texture_category, item_name, self.item_textures[item_name])

    def update_texture_display(self, item_name: str):
        """Update the display of selected textures"""
        if item_name in self.texture_displays:
            display_frame = self.texture_displays[item_name]
            
            # Clear existing textures
            for widget in display_frame.winfo_children():
                widget.destroy()
                
            # Show all selected textures
            if item_name in self.item_textures and self.item_textures[item_name]:
                # Calculate size based on number of textures
                size = min(35, 100 // len(self.item_textures[item_name]))
                
                for texture in self.item_textures[item_name]:
                    image_path = os.path.join(self.base_path, self.category, item_name, "textures", "pics", texture)
                    
                    # Create frame for each texture
                    texture_frame = ctk.CTkFrame(display_frame)
                    texture_frame.pack(side='left', padx=1)
                    
                    # Add texture image
                    texture_label = ctk.CTkLabel(texture_frame, width=size, height=size, text="")
                    texture_label.pack(padx=1, pady=1)
                    
                    # Add click handler to remove
                    texture_label.bind("<Button-1>", lambda e, t=texture, i=item_name: self.remove_texture(i, t))
                    
                    # Load the image
                    self.image_loader.load_image(
                        image_path,
                        (size, size),
                        lambda photo, label=texture_label: label.configure(image=photo) if photo else None
                    )

    def remove_texture(self, item_name: str, texture: str, event=None):
        """Remove a texture from an item"""
        if item_name in self.item_textures and texture in self.item_textures[item_name]:
            self.item_textures[item_name].remove(texture)
            self.update_texture_display(item_name)
            
            # Update the selection state
            if self.item_textures[item_name]:
                self.update_callback(f"{self.category}_textures", item_name, self.item_textures[item_name])
            else:
                self.update_callback(f"{self.category}_textures", item_name, None)

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
        """Load previous page and scroll to top"""
        if self.current_page > 0:
            self.current_page -= 1
            self.load_current_page()
            self.update_navigation()
            # Scroll to top
            self.scrollable_frame._parent_canvas.yview_moveto(0)
            
    def next_page(self):
        """Load next page and scroll to top"""
        total_pages = (len(self.all_items) + self.items_per_page - 1) // self.items_per_page
        if self.current_page < total_pages - 1:
            self.current_page += 1
            self.load_current_page()
            self.update_navigation()
            # Scroll to top
            self.scrollable_frame._parent_canvas.yview_moveto(0)
            
    def cleanup(self):
        """Clean up resources when view is closed"""
        self.image_loader.clear_category(self.category)

class ClothesSelectionWindow(ctk.CTkToplevel):
    def __init__(self, parent, categories: List[str], base_path: str, image_loader: AsyncImageLoader,
                 update_callback, get_preview_image, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.title("Select Items")
        self.geometry("800x600")
        
        self.categories = categories
        self.base_path = base_path
        self.image_loader = image_loader
        self.update_callback = update_callback
        self.get_preview_image = get_preview_image  # Store the method
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
            
        # Clean up current category view
        if self.category_view:
            self.category_view.cleanup()
            self.category_view.destroy()
            
        # Create new category view
        self.category_view = CategoryView(
            self.content_frame,
            category,
            self.base_path,
            self.image_loader,
            self.update_callback,
            self.get_preview_image  # Pass the method
        )
        self.category_view.pack(expand=True, fill='both')
        self.current_category = category

class PedCreatorGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Basic window setup
        self.image_loader = AsyncImageLoader()
        self.title(f"FiveM Ped Creator - Running on v{sys.version.split()[0]}")
        self.iconbitmap("icon.ico")
        self.geometry("1000x700")
        self.resizable(False, False)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        ctk.set_appearance_mode("dark")

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
            "face": [],
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
            "face_textures": {},
            "body_textures": {}
        }
        
        self.clothes_path = MALE_PATH
        self.font = "Supernova"
        self.iconpath = "icon.png"
        
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

    def open_clothes_selection(self, option_name: str, categories: List[str]):
        """Open a new window for clothes selection with dynamic loading"""
        if option_name in self.selection_windows:
            self.selection_windows[option_name].lift()
            return
            
        window = ClothesSelectionWindow(
            self,
            categories,
            self.clothes_path,
            self.image_loader,
            self.update_selection,
            self.get_preview_image  # Pass the method
        )
        window.transient(self)
        window.grab_set()
        
        self.selection_windows[option_name] = window
        window.protocol("WM_DELETE_WINDOW", lambda: self.on_selection_window_close(option_name))

    def create_option_checkboxes(self):
        """Create checkboxes for all ped options with associated category mappings"""
        options = [
            ("Hands", 85, 150, ["hands"]),
            ("Face", 286, 150, ["face"]),
            ("Hair", 85, 195, ["hairs"]),
            ("Body", 286, 195, ["body"]),
            ("Accessories", 85, 240, ["accs", "bags", "chains", "glasses", "hats", "masks", "watches"]),
            ("Clothes", 286, 240, ["shirts", "pants", "shoes", "under_shirt", "vests", "decals"])
        ]

        self.checkboxes = {}
        for text, x, y, categories in options:
            frame = ctk.CTkFrame(self.builder_frame)
            frame.grid(row=1, column=0, sticky="nw", padx=x, pady=y)
            
            checkbox = ctk.CTkCheckBox(
                frame,
                text=text,
                font=ctk.CTkFont(size=17, family=self.font),
                fg_color=PURPLE,
                hover_color=HOVER_PURPLE,
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
                command=lambda t=text, cats=categories: self.edit_selections(t, cats)
            )
            edit_button.pack(side='left', padx=5)
            edit_button.configure(state='disabled')
            
            self.checkboxes[text] = {
                "checkbox": checkbox,
                "categories": categories,
                "edit_button": edit_button
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

    def edit_selections(self, option_name: str, categories: List[str]):
        """Handle edit button clicks by opening or focusing the clothes selection window"""
        self.open_clothes_selection(option_name, categories)

    def on_checkbox_click(self, option_name: str, categories: List[str]):
        """Handle checkbox clicks by opening the clothes selection window"""
        checkbox_info = self.checkboxes[option_name]
        if checkbox_info["checkbox"].get():
            checkbox_info["edit_button"].configure(state='normal')
            self.open_clothes_selection(option_name, categories)
        else:
            checkbox_info["edit_button"].configure(state='disabled')
            # Clear selections for these categories
            for category in categories:
                self.updated_dictionary[category] = []
            if option_name in self.selection_windows:
                self.selection_windows[option_name].destroy()
                del self.selection_windows[option_name]

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


    def update_selection(self, category: str, item_name: str, selected):
        """Update the selection in the dictionary"""
        if item_name is None and selected is None:
            # Return current selections for the category
            return self.updated_dictionary.get(category, [] if not category.endswith('_textures') else {})
            
        if category.endswith("_textures"):
            if selected is None:
                # Remove textures for this item
                if item_name in self.updated_dictionary[category]:
                    del self.updated_dictionary[category][item_name]
            else:
                # Initialize texture dictionary if needed
                if category not in self.updated_dictionary:
                    self.updated_dictionary[category] = {}
                # Update textures
                self.updated_dictionary[category][item_name] = selected.copy() if isinstance(selected, list) else selected
        else:
            # Handle regular categories (lists)
            if selected and item_name not in self.updated_dictionary[category]:
                self.updated_dictionary[category].append(item_name)
            elif not selected and item_name in self.updated_dictionary[category]:
                self.updated_dictionary[category].remove(item_name)
                
                # Also remove any associated textures
                texture_category = f"{category}_textures"
                if texture_category in self.updated_dictionary and item_name in self.updated_dictionary[texture_category]:
                    del self.updated_dictionary[texture_category][item_name]
        
        return self.updated_dictionary.get(category, [] if not category.endswith('_textures') else {})
    
    def on_selection_window_close(self, option_name: str):
        """Properly handle window close and maintain selections"""
        if option_name in self.selection_windows:
            selection_window = self.selection_windows[option_name]
            
            # Save state before closing
            if hasattr(selection_window.category_view, 'item_textures'):
                for category in self.checkboxes[option_name]["categories"]:
                    texture_category = f"{category}_textures"
                    
                    # Restore textures from the view's state
                    if texture_category in self.updated_dictionary:
                        for item_name, textures in selection_window.category_view.item_textures.items():
                            if textures:
                                self.updated_dictionary[texture_category][item_name] = textures.copy()
                            else:
                                if item_name in self.updated_dictionary[texture_category]:
                                    del self.updated_dictionary[texture_category][item_name]
            
            selection_window.destroy()
            del self.selection_windows[option_name]
            
        # Update checkbox states
        self._update_checkbox_states(option_name)

    def _update_checkbox_states(self, option_name: str):
        """Update checkbox states after window closure"""
        has_selections = False
        for category in self.checkboxes[option_name]["categories"]:
            if self.updated_dictionary.get(category) and len(self.updated_dictionary[category]) > 0:
                has_selections = True
                break
        
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

    def build_ped(self):
        """Handle the ped building process"""
        name = self.name_entry.get().strip()
        if not name:
            self.create_message_box("Error", "Please enter a ped name")
            return
            
        # Check if any items are selected
        any_selected = False
        selected_options = {}
        
        for category, items in self.updated_dictionary.items():
            # Skip non-list items and empty categories
            if not isinstance(items, list) or category == "name":
                continue
                
            if items:
                any_selected = True
                selected_options[category] = items
                
                # Add textures if they exist for this category
                if f"{category}_textures" in self.updated_dictionary:
                    selected_options[f"{category}_textures"] = self.updated_dictionary[f"{category}_textures"]
                    
        if not any_selected:
            self.create_message_box("Error", "Please select at least one item")
            return
            
        try:
            # Add name to the selected options
            selected_options["name"] = name
            
            # Initialize FileHandler and process the files
            from file_handler import FileHandler
            FileHandler.copy_files(selected_options, name)
            
            # Show success message
            self.create_message_box("success", f"Ped '{name}' has been successfully created!")

        except Exception as e:
            # Show detailed error message
            self.create_message_box("error", f"An error occurred while building the ped:\n{str(e)}")

    def create_message_box(self, message_type, message):
        """Create a custom message box"""
        message_box = tk.Toplevel()
        message_box.overrideredirect(True)
        message_box.geometry("300x150")
        
        # Set the background color based on the message type
        bg_color = "#d4edda" if message_type == "success" else "#f8d7da"
        fg_color = "#155724" if message_type == "success" else "#721c24"
        
        # Use Canvas for rounded edges
        canvas = tk.Canvas(message_box, width=300, height=150, bg="white", highlightthickness=0)
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
        
        # Add close button
        close_button = ttk.Button(message_box, text="OK", command=message_box.destroy)
        close_window_id = canvas.create_window(150, 120, window=close_button)
        
        # Center the message box
        message_box.update_idletasks()
        screen_width = message_box.winfo_screenwidth()
        screen_height = message_box.winfo_screenheight()
        x = (screen_width - message_box.winfo_width()) // 2
        y = (screen_height - message_box.winfo_height()) // 2
        message_box.geometry(f"+{x}+{y}")

    def destroy(self):
        """Clean up resources"""
        self.image_loader.stop()
        super().destroy()        