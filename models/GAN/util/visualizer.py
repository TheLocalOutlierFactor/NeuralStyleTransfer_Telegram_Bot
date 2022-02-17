import os
import sys
import ntpath
from . import util


if sys.version_info[0] == 2:
    VisdomExceptionBase = Exception
else:
    VisdomExceptionBase = ConnectionError


def save_images(visuals, image_path, aspect_ratio=1.0):
    """Save images to the disk.

    Parameters:
        visuals (OrderedDict)    -- an ordered dictionary that stores (name, images (either tensor or numpy) ) pairs
        image_path (str)         -- the string is used to create image paths
        aspect_ratio (float)     -- the aspect ratio of saved images
        width (int)              -- the images will be resized to width x width

    This function will save images stored in 'visuals' to the HTML file specified by 'webpage'.
    """
    short_path = ntpath.basename(image_path[0])
    name = os.path.splitext(short_path)[0]

    for label, im_data in visuals.items():
        if label == 'real':
            continue
        im = util.tensor2im(im_data)
        save_path = 'images/result/res.jpg'
        util.save_image(im, save_path, aspect_ratio=aspect_ratio)

