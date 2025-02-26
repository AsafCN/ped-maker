import customtkinter as ctk
from gui import PedCreatorGUI

# main.py
def main():
    app = PedCreatorGUI()
    app.mainloop()  # Let Tkinter handle destruction automatically

if __name__ == "__main__":
    main()