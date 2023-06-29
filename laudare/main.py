import inkex

import gui, utils


class LaudareExtension(inkex.extensions.OutputExtension):
    def __init__(self) -> None:
        super().__init__()
        self.object_types = utils.SUPPORTED_TYPES
        self.gui = gui.MainGui(
            self.save_laudare,
            "Save Annotations",
            combovalues=sorted(self.object_types.keys())
        )

    def save(self, stream):
        """
        Methods run when the user clicks on "Save"
        """
        self.gui.set_palette(utils.get_svg_palette(self.svg))
        self.gui.start()

    @__import__("snoop").snoop
    def save_laudare(self, button):
        """Export the SVG file itself into the JSON file, using the associations defined
        by the widgets and destroy the window"""
        json_data = {}
        all_elements = self.svg.descendants()
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
                for node in obj_elements_color:
                    bbox = node.bounding_box()
                    json_data[label][node.get_id()] = (
                        bbox.top,
                        bbox.left,
                        bbox.bottom,
                        bbox.right,
                    )
            else:
                # TODO
                pass

        print(json_data)
        self.gui.stop()


if __name__ == "__main__":
    __import__("sys").argv.append("~/Laudare/Federico only/mytests/Cortona1.svg")
    LaudareExtension().run()
