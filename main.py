import customtkinter as ctk
from gui import PedCreatorGUI

# main.py
def main():
    app = PedCreatorGUI()
    try:
        app.mainloop()
    finally:
        app.destroy()

if __name__ == "__main__":
    main()