# Extruderz
 Inkscape extension that generates paper model of an extruded shape

Given a closed path of straight lines, this program generates a paper model of (1) another copy of the closed path; (2) an extrusion (or more if it exceeds the maximum length) represented by a strip with tabs and score lines; and (3) strips for covering the tabbed strips.

Update: This extension now extrudes not only solid closed paths, but cutouts as well. For example, if you convert a text element (such as the letter "A") to a path, it will generate two extrusions; one for the path representing the outline of the letter and one for the path representing the cutout. Don't forget that curved letters also need to be converted to straight lines.

Update: You can now set a color for solid score lines with the "dashcolor" parameter.

Installing:
 
Copy extruderz.inx and extruderz.py into your Inkscape user extensions directory. Where is that? Open Inkscape and go to the System section of the Preferences menu (Edit --> Preferences --> System). You will find a User extensions item containing the path to your user extensions directory.

Usage:

See the file [How_to_use_extruder.pdf](https://github.com/obzerving/Extruderz/blob/main/How_to_use_extruder.pdf) for details.

[Inkscape 1.1 Papercraft Extruder Extension from Installation to Design Space](https://www.youtube.com/watch?v=lTKPwi4G5_s) is a video tutorial on using the extension.

Note:

This extension (for Inkscape version 1.1 and higher) is still under development and the code reflects it. It's functional, but not yet bulletproof, so be mindful of the input constraints in the usage document.