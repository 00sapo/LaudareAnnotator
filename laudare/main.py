import concurrent.futures
import datetime
import getpass
from pprint import pprint

import gui
import inkex
import utils


def to_px(value, unit):
    if unit != "px":
        return inkex.utils.convert_unit(value, "px", unit)
    else:
        return value


def process_node(node):
    if node.tag_name == "text":
        bbox = node.get_inkscape_bbox()  # slow, this is calling inkscape command!
    else:
        bbox = node.bounding_box()
    return {
        "x": to_px(bbox.top, node.unit),
        "y": to_px(bbox.left, node.unit),
        "w": to_px(bbox.width, node.unit),
        "h": to_px(bbox.height, node.unit),
        "text": node.get_text() if node.tag_name == "text" else None,
    }


class LaudareExtension(inkex.extensions.OutputExtension):
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

    def save_annotations(self, button):
        """Export the SVG file itself into the JSON file, using the associations defined
        by the widgets and destroy the window"""
        json_data = {}
        all_elements = self.svg.descendants()
        image = all_elements.get(inkex.Image)
        if len(image) > 1:
            raise RuntimeError("SVG has multiple images, not supported")
        elif len(image) == 0:
            raise RuntimeError("SVG has no image, not supported")
        else:
            image = image[0]
        json_data["metadata"] = {
            "unit": "px",
            "image": (image.top, image.left, image.width, image.height),
            "date": datetime.datetime.now().isoformat(),
            "author": getpass.getuser(),
        }
        for label, (obj, color, isgroup) in self.gui.get_association_dict().items():
            # get all elements of type obj
            inkex_class = self.object_types[obj]
            obj_elements = all_elements.get(inkex_class)

            # get only elements with this color in stroke *or* fill
            obj_elements_color = []
            for node in obj_elements:
                color_fill = utils.get_node_color(node, "fill")
                color_stroke = utils.get_node_color(node, "stroke")
                if color in [color_fill, color_stroke]:
                    obj_elements_color.append(node)

            json_data[label] = {}

            if not isgroup:
                # add the element to the json data
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    futures = [
                        executor.submit(process_node, node)
                        for node in obj_elements_color
                    ]
                    for i, future in enumerate(
                        concurrent.futures.as_completed(futures)
                    ):
                        label = obj_elements_color[i].get_id()
                        json_data[label] = future.result()
            else:
                # TODO
                pass

        pprint(json_data)
        self.gui.stop()


if __name__ == "__main__":
    __import__("sys").argv.append("~/Laudare/Federico only/mytests/Cortona1.svg")
    LaudareExtension().run()
