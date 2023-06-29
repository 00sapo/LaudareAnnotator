import logging
import platform
from pathlib import Path
from typing import Optional

import inkex

SUPPORTED_TYPES = {
    "Path": inkex.PathElement,
    "Text": inkex.TextElement,
    "Polygon": inkex.Polygon,
    "Ellipse": inkex.Ellipse,
}


def color_string_to_rgb(color):
    """
    Returns the color in rgb(...) syntax.

    Args:
        color (Optional[str]): The color string in either rgb(...) or hex #... format.

    Returns:
        Optional[str]: The color string in rgb(...) format. None if input is None.

    Raises:
        ValueError: If the input color string is not in a valid format.

    Examples:
        >>> color_string_to_rgb('rgb(255, 0, 0)')
        'rgb(255, 0, 0)'
        >>> color_string_to_rgb('#FF0000')
        'rgb(255, 0, 0)'
    """
    if color is None:
        return color
    elif not color.startswith("#") and not color.startswith("rgb"):
        # Raise an error if the color string is not in a valid format
        raise ValueError(
            "Invalid color format. Please provide the color in either rgb(...) or hex #... format."
        )
    elif color.startswith("rgb(") and color.endswith(")"):
        # get values r, g, and b, considering possible spaces in the string
        color = color.replace("rgb(", "").replace(")", "")
        r, g, b = color.split(",")
        r = int(r.strip())
        g = int(g.strip())
        b = int(b.strip())
    elif color.startswith("#") and len(color) == 7:
        # Convert the hex color to rgb(...) format
        r = int(color[1:3], 16)
        g = int(color[3:5], 16)
        b = int(color[5:7], 16)
    return f"rgb({r},{g},{b})"


def check_rule_labels(rules):
    labels = set()
    combinations = set()
    for label, obj, color, isgroup in rules.values():
        value = label.get_buffer().get_text()
        combination = (
            obj.get_active_text(),
            color.get_rgba().to_string(),
            isgroup.get_active(),
        )
        if value in labels or combination in combinations:
            raise RuntimeError(
                f"Duplicate label or combination: {value}, {combination}"
            )
        else:
            labels.add(value)
            combinations.add(combination)


def get_cache_dir():
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


def get_node_color(node, name="fill") -> Optional[str]:
    """Returns the RGB color, without opacity levels. `None` if it is not set."""
    style_str = node.attrib.get("style", None)
    if style_str is None:
        return None
    style = dict(inkex.Style.parse_str(style_str))
    color = style.get(name)
    if color == "none":
        return None
    # check that this element really contains something
    if isinstance(node, inkex.TextElement):
        if node.get_text().replace(" ", "").replace("\t", "") != "":
            return color_string_to_rgb(color)
    elif isinstance(node, inkex.ShapeElement):
        bbox = node.bounding_box()
        if bbox is not None and bbox.area > 0:
            return color_string_to_rgb(color)
    return None


def get_svg_palette(svg):
    """Returns all colors from an SVG object as a set of rgb(..) strings"""
    colors = set()
    for node in svg.descendants():
        stroke = get_node_color(node, "stroke")
        if stroke not in colors and stroke is not None:
            colors.add(stroke)

        fill = get_node_color(node, "fill")
        if fill not in colors and fill is not None:
            colors.add(fill)

    return colors


log_file_path = get_cache_dir() / f"laudare_annotator.log"
logging.basicConfig(
    filename=log_file_path,
    level=logging.DEBUG,
    filemode="a",
    format="%(asctime)s - %(levelname)s - %(message)s",
)
