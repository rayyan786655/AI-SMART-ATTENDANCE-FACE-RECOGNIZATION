import tkinter as tk
from PIL import Image

# Load your already-working camera image
image = Image.open("gui_debug.jpg")

# Resize
image = image.resize((850, 500))

# Convert to GIF
image.save("gui_test.gif", "GIF")

# Create Tkinter window
root = tk.Tk()

root.title("Camera Image Test")
root.geometry("900x600")

# IMPORTANT:
# Let Tkinter itself load the GIF.
photo = tk.PhotoImage(file="gui_test.gif")

label = tk.Label(
    root,
    image=photo,
    bg="black"
)

label.pack(
    padx=20,
    pady=20
)

# Keep reference alive
label.image = photo

root.mainloop()