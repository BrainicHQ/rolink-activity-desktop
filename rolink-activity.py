import tkinter as tk
from tkinter import font as tkFont  # For font customization
import websocket
import json
import threading
from datetime import datetime
import webbrowser
import ssl

try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context


class TalkerGUI:
    def __init__(self, root):
        self.root = root
        self.talkers = []  # List to keep track of the latest 100 talkers
        # Set a placeholder while waiting for the first talker
        self.talkers.insert(0, "Așteptând vorbăreți 🎙️")
        self.root.title("RoLink Activity")

        # Font customization
        self.customFont = tkFont.Font(family="Helvetica", size=14)

        # Create a Listbox to display talkers
        self.listbox = tk.Listbox(root, height=10, width=40, font=self.customFont)
        self.listbox.pack(padx=5, pady=5)

        # Footer
        self.footer_frame = tk.Frame(root)
        self.footer_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=5)

        # Clickable copyright label
        self.copyright_label = tk.Label(self.footer_frame, text="© 2024 Brainic.io", fg="blue", cursor="hand2",
                                        anchor="center")

        def open_link(event):
            webbrowser.open_new("https://brainic.io/?utm_source=rolink-activity")

        # Binding the 'open_link' function to the label
        self.copyright_label.bind("<Button-1>", open_link)
        self.copyright_label.pack(expand=True, fill='both')

        self.root.lift()
        self.root.attributes('-topmost', True)
        self.set_window_size()
        self.position_window_top_right()

    def set_window_size(self):
        # Explicitly setting the window size; adjust as needed
        self.root.geometry('300x250')  # Adjust width and height as needed

    def position_window_top_right(self):
        # Position the window in the top right of the screen
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = self.root.winfo_screenwidth() - width
        y = 0
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def update_talkers(self, talker_data):
        talker_call_sign = talker_data.get('c')
        is_current = talker_data.get('t') == 1
        timestamp_ms = talker_data.get('s', 0)
        timestamp = datetime.fromtimestamp(timestamp_ms / 1000).strftime('%H:%M:%S')

        if is_current:
            # Mark the current talker with a red emoji
            talker_call_sign = "🔴 " + talker_call_sign

            if "Așteptând vorbăreți 🎙️" in self.talkers:
                self.talkers.remove("Așteptând vorbăreți 🎙️")

        # Remove the red emoji from all existing talkers in the list
        self.talkers = [call_sign.replace("🔴 ", "") for call_sign in self.talkers]

        # Insert the talker only if they are the current talker, including their active time as a talker
        if is_current:
            self.talkers.insert(0, talker_call_sign + f" ({timestamp})")

        # Keep only the latest 100 talkers
        self.talkers = self.talkers[:100]

        # Update the Listbox with the list of talkers
        self.listbox.delete(0, tk.END)  # Clear existing entries
        for talker in self.talkers:
            self.listbox.insert(tk.END, talker)  # Insert updated list of talkers
        self.root.update_idletasks()


def on_message(ws, message, gui):
    try:
        data = json.loads(message)
        if "talker" in data:
            gui.update_talkers(data['talker'])
    except Exception as e:
        print(f"Error processing message: {e}")


def on_error(ws, error):
    print(f"Error: {error}")


def on_close(ws, close_status_code, close_msg):
    print("### closed ###")


def on_open(ws, gui):
    def run(*args):
        print("WebSocket client is running and listening for messages...")

    thread = threading.Thread(target=run)
    thread.start()


if __name__ == "__main__":
    root = tk.Tk()
    gui = TalkerGUI(root)

    ws_app = websocket.WebSocketApp("wss://rolink.network/wssx/",
                                    on_message=lambda ws, msg: on_message(ws, msg, gui),
                                    on_error=on_error,
                                    on_close=on_close)
    ws_thread = threading.Thread(target=ws_app.run_forever)
    ws_thread.daemon = True
    ws_thread.start()

    root.mainloop()
