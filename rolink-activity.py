import ssl
import tkinter as tk
from tkinter import font as tkFont  # For font customization
import websocket
import json
import threading
from datetime import datetime
import webbrowser
import certifi
import csv
import os
import sys


def load_call_signs(filename):
    call_signs = {}
    with open(filename, newline='') as csvfile:
        reader = csv.reader(csvfile, delimiter=';')
        for row in reader:
            if len(row) == 2:
                call_sign, name = row
                call_signs[call_sign] = name
    return call_signs


def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


class TalkerGUI:
    def __init__(self, root):
        self.root = root
        self.talkers = []  # List to keep track of the latest 100 talkers
        callbook_path = resource_path('callbook.csv')  # Adjusted to use the resource_path function
        self.call_signs = load_call_signs(callbook_path)  # Load call signs from file
        # https://www.ancom.ro/radioamatori_2899
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
        self.copyright_label = tk.Label(self.footer_frame, text="© 2024 Silviu - Brainic.io", fg="darkgray",
                                        cursor="hand2",
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

    @staticmethod
    def format_name(full_name):
        """
        Formats the name by extracting the first given name and handling special cases.

        If the name is "DATE PERSONALE", it's considered private, and an empty string is returned.
        For names with compound family names (separated by a hyphen) followed by given names,
        or names in the format "Family Name Given Name(s)", this method attempts to return
        only the first given name, handling compound names appropriately.

        :param full_name: The full name to format.
        :return: The formatted name or an empty string for private names.
        """
        if full_name == "DATE PERSONALE":
            return "🕵🏻"  # Private name
        else:
            name_parts = full_name.split()

            # Early return for names that do not follow the expected format
            if not name_parts:
                return "📡"  # Probably a repeater or a gateway

            # Find the index for the first given name
            first_name_index = 1 if len(name_parts) > 1 else 0

            # Adjust for compound family names
            if '-' in name_parts[0] and len(name_parts) > 2:
                first_name_index = 2

            # Select the first given name based on the determined index
            first_name = name_parts[first_name_index]

            # Check if the first name is compound and split it if necessary
            if '-' in first_name:
                first_name_parts = first_name.split('-')
                first_name = first_name_parts[0]  # Take the first part of the compound first name

            return first_name

    def update_talkers(self, talker_data):
        talker_call_sign = talker_data.get('c')
        is_current = talker_data.get('t') == 1
        timestamp_ms = talker_data.get('s', 0)
        timestamp = datetime.fromtimestamp(timestamp_ms / 1000).strftime('%H:%M:%S')

        # Extract the base call sign without any suffix
        base_call_sign = talker_call_sign.split('-')[0]

        # Lookup the name using the base call sign
        full_name = self.call_signs.get(base_call_sign, "")
        talker_name = self.format_name(full_name)

        if is_current:
            # Mark the current talker with a red emoji
            talker_call_sign = "🔴 " + talker_call_sign

            if "Așteptând vorbăreți 🎙️" in self.talkers:
                self.talkers.remove("Așteptând vorbăreți 🎙️")

        # Remove the red emoji from all existing talkers in the list
        self.talkers = [call_sign.replace("🔴 ", "") for call_sign in self.talkers]

        # Insert the talker only if they are the current talker, including their active time as a talker
        if is_current:
            # Include the name in the display
            display_text = f"{talker_call_sign} ({talker_name}) ({timestamp})"
            self.talkers.insert(0, display_text)

        # Keep only the latest 100 talkers
        self.talkers = self.talkers[:100]

        self.listbox.delete(0, tk.END)
        for talker in self.talkers:
            self.listbox.insert(tk.END, talker)
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


    def start_websocket():
        ws_app.run_forever(sslopt={"cert_reqs": ssl.CERT_REQUIRED, "ca_certs": certifi.where()})


    ws_thread = threading.Thread(target=start_websocket)
    ws_thread.daemon = True
    ws_thread.start()

    root.mainloop()
