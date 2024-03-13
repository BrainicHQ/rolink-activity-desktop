import ssl
import tkinter as tk
from tkinter import font as tkFont  # For font customization
from tkinter import messagebox
import websocket
import json
import threading
from datetime import datetime
import webbrowser
import certifi
import csv
import os
import sys
import requests
import re
import time

current_version = "0.0.9"  # Update this with each new release


def version_greater_than(v1, v2):
    """
    Compare two version strings, considering the format 'v.x.x.x', and determine if v1 is greater than v2.

    :param v1: str, the first version string (e.g., "v.0.0.1").
    :param v2: str, the second version string (e.g., "v.0.0.2").
    :return: bool, True if v1 is greater than v2, False otherwise.
    """
    # Strip the leading 'v.' and split the version strings into components
    v1_numbers = [int(num) for num in v1.lstrip('v.').split('.')]
    v2_numbers = [int(num) for num in v2.lstrip('v.').split('.')]

    # Zip the version components for pairwise comparison
    for v1_part, v2_part in zip(v1_numbers, v2_numbers):
        if v1_part > v2_part:
            return True
        elif v1_part < v2_part:
            return False

    # In case all compared components are equal, check if v1 has more numerical components than v2
    return len(v1_numbers) > len(v2_numbers)


def check_for_updates(current_version, root):
    """
    Check GitHub for the latest release version of the app, considering the specific versioning format 'v.x.x.x'.
    Uses the root Tkinter object to safely interact with the GUI from a background thread.
    :param current_version: str, The current version of the app.
    :param root: Tk root window, used for scheduling GUI updates.
    """
    try:
        api_url = "https://api.github.com/repos/BrainicHQ/rolink-activity-desktop/releases/latest"
        response = requests.get(api_url)
        response.raise_for_status()  # Raises stored HTTPError, if one occurred.

        latest_version = response.json()['tag_name']
        if version_greater_than(latest_version, current_version):
            # Schedule the prompt to run in the main thread
            root.after(0, prompt_for_update, latest_version, response.json()['html_url'])
    except Exception as e:
        print(f"Failed to check for updates: {e}")


def get_name_by_api(callsign):
    """
    Get the name of the user by callsign by API.

    :param callsign: The callsign to look up.
    :return: The name of the user or an empty string if not found.
    """
    # Define the regex pattern for HAM call signs
    call_sign_pattern = re.compile(r'^[A-Za-z]{1,2}\d[A-Za-z]{1,3}$')

    # Check if the callsign matches the HAM call sign pattern
    if not call_sign_pattern.match(callsign):
        return ""

    # If the callsign is valid, proceed with the API request
    try:
        response = requests.get(f"https://rolink-qrz-cs.silviu.workers.dev/?callsign={callsign}")
        response_json = response.json()
        if response_json.get("fname"):
            talker_name = response_json.get("fname")
            return talker_name.capitalize()
        else:
            return ""  # Return an empty string if 'fname' is not in the response
    except Exception as e:
        print(f"Error getting name by API: {e}")
        return ""  # Return an empty string if any error occurs


def prompt_for_update(latest_version, download_url):
    """
    Prompt the user to download the latest version of the app.
    :param latest_version: str, The latest version available for download.
    :param download_url: str, The URL to download the new version.
    """
    update_message = (f"Versiunea {latest_version} este disponibilă. Tu ai {current_version}. Vrei să descarci noua "
                      f"versiune?")
    if tk.messagebox.askyesno("Versiune nouă", update_message):
        webbrowser.open_new(download_url)


def load_call_signs(filename):
    call_signs = {}
    with open(filename, newline='', encoding='utf-8') as csvfile:
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
        self.root.title(f"RoLink Activity - v{current_version}")

        # Font customization
        self.customFont = tkFont.Font(family="Helvetica", size=14)

        # Create a Listbox to display talkers
        self.listbox = tk.Listbox(root, height=10, width=40, font=self.customFont)
        self.listbox.pack(padx=5, pady=5, fill=tk.BOTH, expand=True)

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
    def format_name(full_name, call_sign):
        """
        Formats the name by extracting the first given name and handling special cases.

        If the name is "DATE PERSONALE", it's considered private, and an empty string is returned.
        For names with compound family names (separated by a hyphen) followed by given names,
        or names in the format "Family Name Given Name(s)", this method attempts to return
        only the first given name, handling compound names appropriately.

        :param call_sign: The call sign to use for the API lookup.
        :param full_name: The full name to format.
        :return: The formatted name or an empty string for private names.
        """
        if full_name == "DATE PERSONALE":
            return get_name_by_api(call_sign) or "🕵🏻"  # Return the name from the API or a detective emoji (private)
        else:
            name_parts = full_name.split()

            # Early return for names that do not follow the expected format
            if not name_parts:
                return get_name_by_api(
                    call_sign) or "📡"  # Return the name from the API or a satellite emoji (probably a repeater or a
                # gateway)

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

            return first_name.capitalize()

    def update_talkers(self, talker_data):
        talker_call_sign = talker_data.get('c')
        is_current = talker_data.get('t') == 1
        timestamp_ms = talker_data.get('s', 0)
        timestamp = datetime.fromtimestamp(timestamp_ms / 1000).strftime('%H:%M:%S')

        # Extract the base call sign without any suffix
        base_call_sign = talker_call_sign.split('-')[0]

        # Lookup the name using the base call sign
        full_name = self.call_signs.get(base_call_sign, "")
        talker_name = self.format_name(full_name, base_call_sign)

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
    try:
        # Attempt to reconnect after a delay
        time.sleep(10)
        start_websocket()
    except Exception as e:
        print(f"Reconnection attempt failed: {e}")


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
        ws_app.run_forever(sslopt={"cert_reqs": ssl.CERT_REQUIRED, "ca_certs": certifi.where()},
                           ping_interval=10,
                           ping_timeout=2,
                           reconnect=5)


    ws_thread = threading.Thread(target=start_websocket)
    ws_thread.daemon = True
    ws_thread.start()

    check_for_updates(current_version, root)
    root.mainloop()
