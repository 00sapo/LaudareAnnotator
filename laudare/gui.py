import json
import threading
import time

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from . import utils
from gi.repository import Gdk, Gtk


def _colors_to_gdk(colors):
    """Takes in a CSS color string iterable and returns a gdk.RGBA color list"""

    ret = []
    for color in colors:
        gdk_color = Gdk.RGBA()
        gdk_color.parse(color)
        ret.append(gdk_color)
    return ret


def _json_file_chooser(title, action, window=None, buttons=None, multiple_files=False):
    """
    Displays a file chooser dialog for selecting JSON files.

    Args:
        title (str): The title of the file chooser dialog.
        action (Gtk.FileChooserAction): The action to be performed by the file
            chooser dialog.
        window (Gtk.Window): The parent window for the file chooser dialog.
            Defaults to None.
        buttons (list): A list of button labels to be displayed in the file
            chooser dialog. Defaults to None.
        multiple_files (bool): Whether to allow multiple file selection.
            Defaults to False.

    Returns:
        tuple: A tuple containing the response code and the selected file path(s).
            - response (Gtk.ResponseType): The response code indicating the
              user's action.
            - file_path (str or list): The path(s) of the selected file(s).

    Example usage:
        response, file_path = _json_file_chooser("Select JSON File",
                                                 Gtk.FileChooserAction.OPEN)
        if response == Gtk.ResponseType.OK:
            # Process the selected file(s)
            if isinstance(file_path, list):
                for path in file_path:
                    process_file(path)
            else:
                process_file(file_path)
        else:
            # User cancelled the selection
            handle_cancel()

    """
    dialog = Gtk.FileChooserNative(
        title=title, action=action, transient_for=window, buttons=buttons
    )
    if multiple_files:
        dialog.set_select_multiple(True)
    filter_json = Gtk.FileFilter()
    filter_json.set_name("JSON files")
    filter_json.add_mime_type("application/json")
    dialog.add_filter(filter_json)
    response = dialog.run()
    if multiple_files:
        file_path = dialog.get_filenames()
    else:
        file_path = dialog.get_filename()
    dialog.destroy()
    return response, file_path


class MainGui:
    def __init__(self, action_func, action_label, combovalues):
        self.rule_widgets = {}
        self.action_func = action_func
        self.action_label = action_label
        self.combovalues = combovalues

    def set_palette(self, palette):
        self.palette = _colors_to_gdk(palette)
        return self

    def _load_gui(self):
        """Load the main gui for defining the rules"""
        # Start a GTK window with written "Define your own rules" and a button '+'
        self.window = Gtk.Window(title="Define your own rules")
        self.window.set_border_width(10)
        self.window.set_position(Gtk.WindowPosition.CENTER)

        # Create a vertical box to hold the label, button and other widgets
        self.vbox = Gtk.VBox()
        self.window.add(self.vbox)

        # Create a label and add it to the vertical box
        label = Gtk.Label(label="Define your own rules")
        self.vbox.pack_start(label, True, True, 2)

        # Create a button and add it to the vertical box
        add_button = Gtk.Button(label="Add Rule")
        self.vbox.pack_start(add_button, True, True, 2)
        # Connect the button to a function that adds a new HBox when pressed
        add_button.connect("clicked", self._add_rule_widgets)

        # Add a button for exporting the rules
        export_button = Gtk.Button(label="Export Rules")
        self.vbox.pack_start(export_button, True, True, 2)
        export_button.connect("clicked", self.save_config)

        # Add a button for importing the rules
        export_button = Gtk.Button(label="Import Rules")
        self.vbox.pack_start(export_button, True, True, 2)
        export_button.connect("clicked", self.load_config)

        # Add a button for saving the annotation file
        save_button = Gtk.Button(label=self.action_label)
        self.vbox.pack_start(save_button, True, True, 2)
        save_button.connect("clicked", self._run_action_func)

        # Show all widgets
        self.window.show_all()

        self.window.connect("destroy", self.stop)

    def _run_action_func(self, button):
        # Add a progress bar with unknown duration
        spinner = Gtk.Spinner()
        button.set_label("Working...")
        button.spinner = spinner
        self.vbox.pack_start(spinner, True, True, 5)
        self.vbox.show_all()
        spinner.start()
        thread = threading.Thread(
            target=self.action_func,
            kwargs=dict(callback=self._stop_action_func, args=(button,)),
        )
        thread.start()

    def _stop_action_func(self, button):
        button.set_label(self.action_label)
        button.spinner.stop()
        self.window.show_all()

    def _add_rule_widgets(self, button):
        """Adds widgets for defining a new rule"""

        # Create a horizontal box to hold the text box, dropdown menu, color gui, remove
        # button, and checkbox
        hbox = Gtk.HBox()
        self.vbox.pack_start(hbox, True, True, 3)
        id = len(self.rule_widgets)
        hbox.id = id

        # Create a text box and add it to the horizontal box
        label_entry = Gtk.Entry()
        label_entry.set_text(f"Label {id}")
        hbox.pack_start(label_entry, True, True, 0)

        # Create a dropdown menu and add it to the horizontal box
        type_combo = Gtk.ComboBoxText()
        for v in self.combovalues:
            type_combo.append_text(v)
        hbox.pack_start(type_combo, True, True, 0)

        # Create a color gui and add it to the horizontal box
        color_button = Gtk.ColorButton()
        color_button.add_palette(Gtk.Orientation.HORIZONTAL, 5, self.palette)
        hbox.pack_start(color_button, True, True, 0)

        # Create a remove button and add it to the horizontal box
        remove_button = Gtk.Button(label="X")
        remove_button.connect("clicked", self._remove_rule, hbox, id)
        hbox.pack_start(remove_button, True, True, 0)

        # Create a checkbox for referring to groups of objects only
        checkbox = Gtk.CheckButton(label="Groups Label")
        hbox.pack_start(checkbox, True, True, 0)

        self.rule_widgets[id] = (label_entry, type_combo, color_button, checkbox)
        self.vbox.show_all()

    def _remove_rule(self, button, hbox, id):
        """Removes the specified rule"""
        self.vbox.remove(hbox)
        del self.rule_widgets[id]
        self.vbox.show_all()
        self.window.show_all()

    def _load_rule_dict(self, rules):
        missing_widgets = len(rules) - len(self.rule_widgets)
        if missing_widgets > 0:
            # add more widgets
            for _ in range(missing_widgets):
                self._add_rule_widgets(None)

        for i, (label, values) in enumerate(rules.items()):
            widgets = self.rule_widgets[i]
            widgets[0].get_buffer().set_text(label, len(label))  # the label
            if values[0] is None:
                widgets[1].set_active(-1)
            else:
                widgets[1].set_active(
                    self.combovalues.index(values[0])
                )  # the type of sign (rect, circle, path, text...)
            color = Gdk.RGBA()
            color.parse(values[1])  # the color
            widgets[2].set_rgba(color)
            widgets[3].set_active(values[2])  # if groups-only

    def get_rule_dict(self):
        out = {}
        utils.check_rule_labels(self.rule_widgets)
        for (
            entry,
            combotext,
            colorbutton,
            checkbox,
        ) in self.rule_widgets.values():
            out[entry.get_buffer().get_text()] = [
                combotext.get_active_text(),
                utils.color_string_to_rgb(colorbutton.get_rgba().to_string()),
                checkbox.get_active(),
            ]
        return out

    def load_config(self, button):
        """Load a config from a JSON file and puts the info in proper widgets"""
        response, file_path = _json_file_chooser(
            "Load JSON rules", Gtk.FileChooserAction.OPEN, window=self.window
        )
        if response == Gtk.ResponseType.ACCEPT:
            # Load rules `out` from a json file
            with open(file_path, "r") as f:
                rules = json.load(f)
        else:
            return
        self._load_rule_dict(rules)

    def save_config(self, button):
        """Open a window to save the rules into a JSON file"""
        out = self.get_rule_dict()

        # Let the user chose a filename using Gtk.FileChooserNative
        response, file_path = _json_file_chooser(
            "Save JSON rules", Gtk.FileChooserAction.SAVE, window=self.window
        )
        if response == Gtk.ResponseType.ACCEPT:
            # Save `out` to a json file
            with open(file_path, "w") as f:
                json.dump(out, f)

    def start(self):
        """Load the main window and the annotation from the cache"""
        self._load_gui()
        fpath = utils.get_cache_dir() / "rules.json"
        if fpath.exists():
            with open(fpath, "r") as f:
                rules = json.load(f)
                self._load_rule_dict(rules)
        # Run the GTK main loop
        Gtk.main()

    def stop(self, trigger=None):
        """
        Save the annotation config to cache and close the main window.
        """
        # Save the config to a file in the cache directory
        rules = self.get_rule_dict()
        with open(utils.get_cache_dir() / "rules.json", "w") as f:
            json.dump(rules, f)

        # Close the main window
        if trigger is None:
            trigger = self.window
        Gtk.main_quit(trigger)
