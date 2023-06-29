# Laudare Annotator

This is an Inkscape plugin for annotating images for Computer Vision tasks.

It has been developed in the context of the Laudare ERC project for annotating ancient
characters to build font in a document augmentation approach. However, I have built it
with general-purpose annotation tasks in mind, so it is likely useful for other projects
as well.

The plugin stores the bounding boxes of each shape in a JSON file, connecting each
object to a label according to customizable rules.

## Features

1. Automatic color palette detection
2. Exporting and importing rules (each rule connect a combination of shape-color to a
   label)
3. Ability to assign labels to group of objects and to remember objects labeled inside
   the groups
4. Export to JSON format, easy for parsing in other projects
5. Embed the image in base64 format
6. Supports text, rectangles, paths, and ellipses, but only the bounding boxes and the
   text content are remembered
7. Remember last used rules

## TODO

1. The plugin performs check of formal correctness of the annotations, but that part can
   largely be improved
2. Provide some good general-purpose color palette and tweak the Inkscape UI in order to
   decrease the probability of errors
3. Add ability for automatic detection of shapes inside the bounding boxes
4. Right now, stroke and fill colors are checked in an or fashion: shapes with different
   color in shape and fill will be labeled in an unpredictable way

## How to use

1. Download the Zip file and extract it into the directory listed at `Edit` > `Preferences` > `System: User extensions`. After a restart of Inkscape, the new extension will be available.
2. Define a color palette with a little number of colors
3. Use shaes and text to annotate images
4. Use `File` > `Save As` and look for "Laudare JSON" format
5. Press `Save` and choose the file name
6. In the GUI that shows up, define your own rules. You can export them to reload them
   later. The last used rules will be remembered without needing to save them
7. Press `Export Annotations` and wait

If a window shows up saying that "Inkscape has received additional data" but that "there
was no error", that is ok.

## Credits

Federico Simonetta, federico.simonetta [at] gssi.it, https://federicosimonetta.eu.org
