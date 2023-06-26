#!/usr/bin/env python
import json

import gi

gi.require_version("Gtk", "3.0")
import inkex
from gi.repository import Gtk
from gi.repository import Gdk
from inkex.utils import debug


class LaudareExtension(inkex.extensions.OutputExtension):
    def __init__(self) -> None:
        super().__init__()
        self.association_widgets = []
        self.combovalues = ["Path", "Text", "Rectangle", "Circle"]

    def save(self, stream):
        """
        Methods run when the user clicks on "Save"
        """
        # self.svg = self.load(stream)

        # Start a GTK window with written "Define your own associations" and a button '+'
        self.window = Gtk.Window(title="Define your own associations")
        self.window.set_border_width(10)
        self.window.set_position(Gtk.WindowPosition.CENTER)

        # Create a vertical box to hold the label, button and other widgets
        self.vbox = Gtk.VBox()
        self.window.add(self.vbox)

        # Create a label and add it to the vertical box
        label = Gtk.Label("Define your own associations")
        self.vbox.pack_start(label, True, True, 0)

        # Create a button and add it to the vertical box
        add_button = Gtk.Button(label="Add Association")
        self.vbox.pack_start(add_button, True, True, 0)
        # Connect the button to a function that adds a new HBox when pressed
        add_button.connect("clicked", self.add_association_widgets)

        # Add a button for exporting the associations
        export_button = Gtk.Button(label="Save Associations")
        self.vbox.pack_start(export_button, True, True, 0)
        export_button.connect("clicked", self.save_config)

        # Add a button for importing the associations
        export_button = Gtk.Button(label="Load Associations")
        self.vbox.pack_start(export_button, True, True, 0)
        export_button.connect("clicked", self.load_config)

        # Show all widgets
        self.window.show_all()

        self.window.connect("destroy", Gtk.main_quit)

        # Run the GTK main loop
        Gtk.main()

    def add_association_widgets(self, button):
        """Adds widgets for defining a new association"""

        # Create a horizontal box to hold the text box, dropdown menu and color gui
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
        hbox.pack_start(color_button, True, True, 0)

        self.association_widgets.append((label_entry, type_combo, color_button))
        self.window.show_all()

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

        missing_widgets = len(associations) - len(self.association_widgets)
        if missing_widgets > 0:
            # add more widgets
            for _ in range(missing_widgets):
                self.add_association_widgets(button)

        for i, (label, values) in enumerate(associations.items()):
            widgets = self.association_widgets[i]
            widgets[0].get_buffer().set_text(label, len(label))
            widgets[1].set_active(self.combovalues.index(values[0]))
            color = Gdk.RGBA()
            color.parse(values[1])
            widgets[2].set_rgba(color)

    def save_config(self, button):
        """Open a window to save the associations into a JSON file"""
        out = {}
        _check_association_labels(self.association_widgets)
        for entry, combotext, colorbutton in self.association_widgets:
            out[entry.get_buffer().get_text()] = [
                combotext.get_active_text(),
                colorbutton.get_rgba().to_string(),
            ]
        # Let the user chose a filename using Gtk.FileChooserNative
        response, file_path = _json_file_chooser(
            "Save JSON associations", Gtk.FileChooserAction.SAVE, self.window
        )
        if response == Gtk.ResponseType.ACCEPT:
            # Save `out` to a json file
            with open(file_path, "w") as f:
                json.dump(out, f)

    def export(self):
        """Export the SVG file itself into the JSON file, using the associations defined
        by the widgets"""


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
    for label, _, _ in associations:
        value = label.get_buffer().get_text()
        if value in labels:
            raise RuntimeError(f"Duplicate label: {value}")
        else:
            labels.add(value)


if __name__ == "__main__":
    LaudareExtension().run()
