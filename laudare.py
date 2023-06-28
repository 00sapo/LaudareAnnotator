#!/usr/bin/env python
import json
import logging
import platform
from logging import debug, error, info, warn
from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
import inkex
from gi.repository import Gdk, Gtk


def _json_file_chooser(title, action, window):
    dialog = Gtk.FileChooserNative(title=title, action=action, transient_for=window)
    filter_json = Gtk.FileFilter()
    filter_json.set_name("JSON files")
    filter_json.add_mime_type("application/json")
    dialog.add_filter(filter_json)
    response = dialog.run()
    file_path = dialog.get_filename()
    dialog.destroy()
    return response, file_path


def _check_association_labels(associations):
    labels = set()
    for label, _, _ in associations.values():
        value = label.get_buffer().get_text()
        if value in labels:
            raise RuntimeError(f"Duplicate label: {value}")
        else:
            labels.add(value)


def _get_cache_dir():
    """Compute the cache directory according to the OS and returns it"""

    if platform.system() == "Windows":
        cache_directory = Path.home() / "AppData" / "Local" / "cache"
    elif platform.system() == "Darwin":
        cache_directory = Path.home() / "Library" / "Caches"
    else:
        cache_directory = Path.home() / ".cache"
    # Create the directory if it doesn't exist
    cache_path = cache_directory / "inkscape" / "laudare_annotator_cache"
    cache_path.mkdir(parents=True, exist_ok=True)
    return cache_path


def _get_svg_colors(svg):
    """Returns all colors from an SVG object as a set of Gdk.RGBA objects"""
    colors = {"rgb(0, 0, 0)"}
    for node in svg.descendants():
        style_str = node.attrib.get("style", None)
        if style_str is None:
            continue
        style = inkex.Style(style_str)
        stroke = style.get_color("stroke")
        if stroke not in colors:
            colors.add(str(stroke))

        fill = style.get_color("fill")
        if fill not in colors:
            colors.add(str(fill))

    ret = []
    for color in colors:
        gdk_color = Gdk.RGBA()
        gdk_color.parse(color)
        ret.append(gdk_color)
    return ret


log_file_path = _get_cache_dir() / f"laudare_annotator.log"
logging.basicConfig(
    filename=log_file_path,
    level=logging.DEBUG,
    filemode="a",
    format="%(asctime)s - %(levelname)s - %(message)s",
)


class LaudareExtension(inkex.extensions.OutputExtension):
    def __init__(self) -> None:
        super().__init__()
        self.association_widgets = {}
        self.combovalues = ["Path", "Text", "Rectangle", "Circle"]

    def save(self, stream):
        """
        Methods run when the user clicks on "Save"
        """
        self.start()

    def _load_gui(self):
        """Load the main gui for defining the associations"""
        # Start a GTK window with written "Define your own associations" and a button '+'
        self.window = Gtk.Window(title="Define your own associations")
        self.window.set_border_width(10)
        self.window.set_position(Gtk.WindowPosition.CENTER)

        # Create a vertical box to hold the label, button and other widgets
        self.vbox = Gtk.VBox()
        self.window.add(self.vbox)

        # Create a label and add it to the vertical box
        label = Gtk.Label(label="Define your own associations")
        self.vbox.pack_start(label, True, True, 0)

        # Create a button and add it to the vertical box
        add_button = Gtk.Button(label="Add Association")
        self.vbox.pack_start(add_button, True, True, 0)
        # Connect the button to a function that adds a new HBox when pressed
        add_button.connect("clicked", self.add_association_widgets)

        # Add a button for exporting the associations
        export_button = Gtk.Button(label="Export Associations")
        self.vbox.pack_start(export_button, True, True, 0)
        export_button.connect("clicked", self.save_config)

        # Add a button for importing the associations
        export_button = Gtk.Button(label="Import Associations")
        self.vbox.pack_start(export_button, True, True, 0)
        export_button.connect("clicked", self.load_config)

        # Add a button for saving the annotation file
        save_button = Gtk.Button(label="Save")
        self.vbox.pack_start(save_button, True, True, 0)
        save_button.connect("clicked", self.save_laudare)

        # Show all widgets
        self.window.show_all()

        self.window.connect("destroy", self.stop)

    def add_association_widgets(self, button):
        """Adds widgets for defining a new association"""

        # Create a horizontal box to hold the text box, dropdown menu, color gui, and remove button
        hbox = Gtk.HBox()
        self.vbox.pack_start(hbox, True, True, 0)

        # Create a text box and add it to the horizontal box
        label_entry = Gtk.Entry()
        label_entry.set_text(f"Label {len(self.association_widgets)}")
        hbox.pack_start(label_entry, True, True, 0)

        # Create a dropdown menu and add it to the horizontal box
        type_combo = Gtk.ComboBoxText()
        for v in self.combovalues:
            type_combo.append_text(v)
        hbox.pack_start(type_combo, True, True, 0)

        # Create a color gui and add it to the horizontal box
        color_button = Gtk.ColorButton()
        svg_palette = _get_svg_colors(self.svg)
        color_button.add_palette(Gtk.Orientation.HORIZONTAL, 5, svg_palette)
        hbox.pack_start(color_button, True, True, 0)

        # Create a remove button and add it to the horizontal box
        id = len(self.association_widgets)
        remove_button = Gtk.Button(label="X")
        remove_button.connect(
            "clicked", self._remove_association, hbox, id
        )
        hbox.pack_start(remove_button, True, True, 0)

        self.association_widgets[id] = (label_entry, type_combo, color_button)
        self.vbox.show_all()

    def _remove_association(self, button, hbox, id):
        """Removes the specified association"""
        self.vbox.remove(hbox)
        del self.association_widgets[id]
        self.vbox.show_all()
        self.window.show_all()

    def _load_association_dict(self, associations):
        missing_widgets = len(associations) - len(self.association_widgets)
        if missing_widgets > 0:
            # add more widgets
            for _ in range(missing_widgets):
                self.add_association_widgets(None)

        for i, (label, values) in enumerate(associations.items()):
            widgets = self.association_widgets[i]
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

    def _get_association_dict(self):
        out = {}
        _check_association_labels(self.association_widgets)
        for entry, combotext, colorbutton in self.association_widgets.values():
            out[entry.get_buffer().get_text()] = [
                combotext.get_active_text(),
                colorbutton.get_rgba().to_string(),
            ]
        return out

    def load_config(self, button):
        """Load a config from a JSON file and puts the info in proper widgets"""
        response, file_path = _json_file_chooser(
            "Load JSON associations", Gtk.FileChooserAction.OPEN, self.window
        )
        if response == Gtk.ResponseType.ACCEPT:
            # Load associations `out` from a json file
            with open(file_path, "r") as f:
                associations = json.load(f)
        else:
            return
        self._load_association_dict(associations)

    def save_config(self, button):
        """Open a window to save the associations into a JSON file"""
        out = self._get_association_dict()

        # Let the user chose a filename using Gtk.FileChooserNative
        response, file_path = _json_file_chooser(
            "Save JSON associations", Gtk.FileChooserAction.SAVE, self.window
        )
        if response == Gtk.ResponseType.ACCEPT:
            # Save `out` to a json file
            with open(file_path, "w") as f:
                json.dump(out, f)

    def save_laudare(self, button):
        """Export the SVG file itself into the JSON file, using the associations defined
        by the widgets and destroy the window"""
        self.stop()

    def start(self):
        """Load the main window and the annotation from the cache"""
        debug("start")
        self._load_gui()
        debug("gui loaded")
        with open(_get_cache_dir() / "associations.json", "r") as f:
            associations = json.load(f)
        debug("loaded associations: " + str(associations))
        self._load_association_dict(associations)
        debug("associations loaded into the gui")
        # Run the GTK main loop
        Gtk.main()
        debug("starting gui")

    def stop(self, trigger=None):
        """
        Save the annotation config to cache and close the main window.
        """
        debug("stop")
        # Save the config to a file in the cache directory
        associations = self._get_association_dict()
        debug("got association dict")
        with open(_get_cache_dir() / "associations.json", "w") as f:
            json.dump(associations, f)
            debug("saved association dict: " + str(associations))

        # Close the main window
        if trigger is None:
            trigger = self.window
        debug("quitting now...")
        Gtk.main_quit(trigger)


if __name__ == "__main__":
    __import__("sys").argv.append("~/Laudare/Federico only/mytests/Cortona1.svg")
    LaudareExtension().run()
