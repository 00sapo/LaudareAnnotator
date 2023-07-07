"""A module for counting the annotations from a set of files."""

import json
import re
from collections import defaultdict

import gi
import inkex

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, Gtk

from . import gui


class MyDialog(Gtk.Dialog):
    def __init__(self, parent, counts):
        sorted_counts = sorted(
            counts.items(), key=lambda x: x[0]
        )  # Sort items alphabetically by key

        Gtk.Dialog.__init__(
            self,
            title="Counts Dialog",
            transient_for=parent,
            flags=0,
        )
        self.add_buttons(Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE)

        self.set_default_size(250, 400)

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.get_content_area().add(scrolled_window)

        # Set the size of the scrolled window to match the dialog
        self.connect(
            "size-allocate",
            lambda widget, allocation: scrolled_window.set_size_request(
                allocation.width, allocation.height
            ),
        )

        grid = Gtk.Grid(column_homogeneous=True, column_spacing=10)
        scrolled_window.add(grid)

        # Create a label for each string and its corresponding count
        pattern = re.compile(r"\s+")
        for string, count in sorted_counts:
            string = pattern.sub("", string)
            label = Gtk.Label(label=f"{string}")
            label.set_xalign(0)  # Align label text to the left
            label.set_yalign(0.5)
            label.set_hexpand(True)  # Expand label horizontally
            # label.set_margin_end(10)  # Add margin to the right of the label

            count_label = Gtk.Label(label=str(count))
            count_label.set_xalign(1)  # Align count text to the right
            count_label.set_yalign(0.5)
            # count_label.set_margin_start(5)  # Add margin to the left of the count label

            # changing colors
            if len(grid.get_children()) % 2 == 0:
                label.override_background_color(
                    Gtk.StateFlags.NORMAL, Gdk.RGBA(0.9, 0.9, 0.9, 1)
                )
                count_label.override_background_color(
                    Gtk.StateFlags.NORMAL, Gdk.RGBA(0.9, 0.9, 0.9, 1)
                )

            grid.attach(label, 0, len(grid.get_children()), 1, 1)
            grid.attach(count_label, 1, len(grid.get_children()) - 1, 1, 1)

            separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
            grid.attach(separator, 0, len(grid.get_children()), 2, 1)

        self.show_all()


class LaudareCount(inkex.extensions.GenerateExtension):
    def __init__(self):
        super().__init__()

    def choose_files(self):
        response, file_paths = gui._json_file_chooser(
            title="Select Laudare JSON files",
            action=Gtk.FileChooserAction.OPEN,
            multiple_files=True,
        )

        if response == Gtk.ResponseType.ACCEPT:
            return file_paths
        else:
            return []

    def count_annotations(self, data: dict):
        counts = defaultdict(int)
        for label, annotations in data["annotations"].items():
            counts[label] += len(annotations["elements"])
            counts[label + " - group"] += len(annotations["groups"])
            for item in annotations["elements"].values():
                text = item["text"]
                # here < 10 is to protect against very long texts...
                if text is not None and len(text) < 10:
                    counts[text] += 1
        return counts

    def show_counts_dialog(self, data):
        """
        Show a Gtk dialog displaying the counts of each string in the given data.

        Args:
            data (dict): A dictionary mapping strings to integers.

        Returns:
            None
        """
        # Create an instance of the dialog and pass the counts to it
        dialog = MyDialog(None, data)

        # Run the dialog and wait for a response
        dialog.run()

    def effect(self):
        files = self.choose_files()
        all_counts = defaultdict(int)
        for file in files:
            with open(file, "r") as fp:
                data = json.load(fp)
            counts = self.count_annotations(data)
            for k, v in counts.items():
                all_counts[k] += v
        self.show_counts_dialog(all_counts)
