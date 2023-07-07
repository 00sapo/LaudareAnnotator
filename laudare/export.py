import concurrent.futures
import datetime
import getpass
import json
import warnings
from tempfile import TemporaryDirectory

import inkex
from inkex import units
from inkex.command import inkscape, write_svg
from inkex.transforms import BoundingBox

from . import gui, utils

warnings.filterwarnings("ignore")


def to_px(value, unit):
    if unit != "px":
        return units.convert_unit(value, "px", unit)
    else:
        return value


def bake_transforms_recursively(group, apply_to_paths=True):
    """
    Back-ported from inkex >= 1.4
    """
    for element in group:
        if isinstance(element, inkex.PathElement) and apply_to_paths:
            element.path = element.path.transform(group.transform)
        else:
            element.transform = group.transform @ element.transform
            if isinstance(element, inkex.elements._groups.GroupBase):
                bake_transforms_recursively(element, apply_to_paths)
    group.transform = None


def node_to_annotation(
    node, children=[], relative_to=(0, 0), text_bboxes: dict[str, BoundingBox] = {}
):
    if node.tag_name == "text":
        bbox = text_bboxes[node.get_id()]
    else:
        bbox = node.bounding_box()
    return {
        "x": to_px(bbox.left - relative_to[0], node.unit),
        "y": to_px(bbox.top - relative_to[1], node.unit),
        "w": to_px(bbox.width, node.unit),
        "h": to_px(bbox.height, node.unit),
        "text": node.get_text() if node.tag_name == "text" else None,
        "children": [c.get_id() for c in children],
    }


def get_text_element_bounding_box(svg):
    """Executes an external call to Inkscape and queries all the bounding boxes of all
    the text elements. Returns a dict with keys the text elements ids starting with `#`
    and with values a `BoundingBox` object"""

    outmap = {}
    with TemporaryDirectory(prefix="inkscape-command") as tmpdir:
        svg_file = write_svg(svg, tmpdir, "input.svg")
        out = inkscape(svg_file, actions="select-by-element:text;query-all")

        for line in out.strip().split("\n"):
            elements = line.split(",")
            element_id = elements[0]
            bbox = BoundingBox.new_xywh(
                float(elements[1]),
                float(elements[2]),
                float(elements[3]),
                float(elements[4]),
            )
            outmap[element_id] = bbox

    return outmap


class LaudareExport(inkex.extensions.OutputExtension):
    def __init__(self) -> None:
        super().__init__()
        self.object_types = utils.SUPPORTED_TYPES
        self.gui = gui.MainGui(
            self.save_annotations,
            "Save Annotations",
            combovalues=sorted(self.object_types.keys()),
        )

    def save(self, stream):
        """
        Methods run when the user clicks on "Save"
        """
        self.gui.set_palette(utils.get_svg_palette(self.svg))
        self.gui.start()

    def fill_info(self, all_elements, json_data):
        image = all_elements.get(inkex.Image)
        if len(image) > 1:
            raise RuntimeError("SVG has multiple images, not supported")
        elif len(image) == 0:
            raise RuntimeError("SVG has no image, not supported")
        else:
            image = image[0]
        # compute the size of the image, considering transforms
        image_bbox = image.bounding_box()
        self._image_x = image_bbox.left
        self._image_y = image_bbox.top

        unit = self.svg.unit
        # inserting metadata
        json_data["info"] = {
            "unit": "px",
            "date": datetime.datetime.now().isoformat(),
            "author": getpass.getuser(),
            "image": {
                "position": (
                    to_px(image_bbox.left, unit),
                    to_px(image_bbox.top, unit),
                    to_px(image_bbox.width, unit),
                    to_px(image_bbox.height, unit),
                ),
                "href": next(
                    v for k, v in image.attrib.items() if k.endswith("href")
                ),  # href may be preceeded by {...} # this can be base4 binary encoding!
            },
        }

    def insert_groups(self, all_groups, obj_elements_color, json_data, label):
        # iterate all groups and selects only those that contain obj with
        # color
        for group in all_groups:
            if group.groupmode == "layer":
                continue
            grouped_nodes = [
                node for node in group.descendants() if node in obj_elements_color
            ]
            if len(grouped_nodes) > 1:
                json_data["annotations"][label]["groups"][
                    group.get_id()
                ] = node_to_annotation(
                    group,
                    children=grouped_nodes,
                    relative_to=(self._image_x, self._image_y),
                )

    def insert_elements(self, json_data, label, obj_elements_color):
        # add the element to the json data
        for node in obj_elements_color:
            id = node.get_id()
            json_data["annotations"][label]["elements"][id] = node_to_annotation(
                node,
                relative_to=(self._image_x, self._image_y),
                text_bboxes=self.text_bboxes,
            )

    def save_annotations(self, callback=None, args=None):
        """Export the SVG file itself into the JSON file, using the rules defined
        by the widgets and destroy the window"""
        json_data = {}
        all_elements = self.svg.descendants()
        self.text_bboxes = get_text_element_bounding_box(self.svg)

        all_groups = all_elements.get(inkex.Group)
        for g in all_groups:
            # apply transforms to lement, and remove them from groups
            bake_transforms_recursively(g)

        self.fill_info(all_elements, json_data)

        # inserting annotations
        json_data["annotations"] = {}
        for label, (obj, color, isgroup) in self.gui.get_rule_dict().items():
            # get all elements of type obj
            inkex_class = self.object_types[obj]
            obj_elements = all_elements.get(inkex_class)

            # get only elements with this color in stroke *or* fill
            obj_elements_color = []
            for node in obj_elements:
                color_fill = utils.get_node_color(node, "fill")
                color_stroke = utils.get_node_color(node, "stroke")

                if utils.match_colors(color, color_fill, color_stroke):
                    obj_elements_color.append(node)

            json_data["annotations"][label] = {
                "color": color,
                "shape": obj,
                "elements": {},
                "groups": {},
            }

            if not isgroup:
                self.insert_elements(json_data, label, obj_elements_color)
            else:
                self.insert_groups(all_groups, obj_elements_color, json_data, label)

        json_string = json.dumps(json_data)
        print(json_string)
        if callback is not None:
            callback(*args)
        self.gui.stop()
