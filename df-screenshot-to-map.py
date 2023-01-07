#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Make an Excel file of Dwarf Fortress map elevations from minimap screenshots.

@author: Mike Renfro

Given a series of screenshots of Dwarf Fortress minimaps at different
elevations:

- Identify underground areas (should be around RGB (128, 128, 128))
- Use largest identified underground area to define extents of map region.
- For each elevation:
    - crop the minimap to the overall extents
    - create a normalized 2D interpolant of the minimap bounded by
      [0, 0, 0] <= (x, y, z) <= [1, 1, 255]
    - map the 2D interpolant to a (x, y) grid of size
      (48*embark_size, 48*embark_size) bounded by [0, 0] <= (x, y) <= [1, 1]
    - round each the interpolated value to 0 or 1
    - insert each interpolated value into a new workbook sheet
    - apply a color scale conditional format to the sheet
"""
import argparse
import cv2
import glob
import numpy as np
from openpyxl import Workbook
from openpyxl.formatting.rule import ColorScaleRule
from openpyxl.utils import get_column_letter
import os
import scipy


def find_valid_worlds(basedir):
    """
    Find folders containing minimap screenshots.

    Parameters
    ----------
    basedir : str
        Path to folder containing Dwarf Fortress screenshot folders.

    Returns
    -------
    valid_worlds : list
        List of paths to folders under basedir containing valid minimap
        screenshots.

    """
    worlds = glob.glob(os.path.join(basedir, '*'))
    valid_worlds = []
    if worlds:
        for world in worlds:
            if os.path.isdir(world):
                elevations = glob.glob(os.path.join(world, '*.png'))
                if elevations:
                    valid_worlds.append(world)
    return valid_worlds


def safe_imshow(title='Image', image=None):
    """
    Safely show an OpenCV image.

    Parameters
    ----------
    title : str, optional
        Title of the image window. The default is 'Image'.
    image : array_like, technically optional
        Image to show. The default is None.

    Returns
    -------
    None.

    """
    cv2.imshow(title, image)
    cv2.waitKey()
    cv2.destroyAllWindows()


def crop_top_titlebar(image):
    """
    Crop out title bar from minimap screenshot.

    Parameters
    ----------
    image : array_like
        Screenshot wih some part of title bar at top.

    Returns
    -------
    cropped_image : array_like
    """
    # Convert to greyscale, then look for first black pixel in first
    # column.
    greyscale = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    first_black_row = np.where(greyscale[:, 0] == 0)[0][0]
    image = image[first_black_row:, :, :]
    # Convert new image to greyscale, then look for the first non-black pixel
    # in the first column.
    greyscale = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    first_non_black_row = np.where(greyscale[:, 0] != 0)[0][0]
    cropped_image = image[first_non_black_row:, :, :]
    return cropped_image


def crop_right_window_border(image):
    """
    Crop out window border from minimap screenshot.

    Parameters
    ----------
    image : array_like
        Screenshot wih some part of window border at right.

    Returns
    -------
    cropped_image : array_like
    """
    # Convert to greyscale, then look for last non pure black pixel in last
    # row.
    greyscale = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    last_black_column = np.where(greyscale[-1, :] != 0)[0][-1]
    cropped_image = image[:, :last_black_column, :]
    return cropped_image


def get_underground_pixels(image, extents=None):
    """
    Get all the pixels representing underground locations.

    Parameters
    ----------
    image : array_like
        Minimap of a given elevation.
    extents : tuple of (left, right, top, bottom) or None (default)
        Extents of the underground pixels in this elevation, if known, or None
        if unknown. Image will be cropped to extents if known, or whole image
        will be used if unknown.

    Returns
    -------
    im_result : array_like
        Pixels of underground regions.
    """
    lower = (125, 125, 125)
    upper = (130, 130, 130)
    if extents is None:
        mask = cv2.inRange(image, lower, upper)
    else:
        (left, right, top, bottom) = extents
        mask = cv2.inRange(image[top:bottom, left:right], lower, upper)

    # Remove small blobs from mask
    # https://stackoverflow.com/a/42812226
    # safe_imshow(image=mask, title='Original Mask')
    (nb_blobs, im_with_separated_blobs,
     stats, _) = cv2.connectedComponentsWithStats(mask)
    sizes = stats[:, -1]
    sizes = sizes[1:]
    nb_blobs -= 1
    min_size = 50
    im_result = np.zeros((mask.shape))
    # print("Mask shape:", mask.shape)
    # for every component in the image, keep it only if it's above min_size
    for blob in range(nb_blobs):
        # print("On blob", blob, "of", nb_blobs)
        if sizes[blob] >= min_size:
            im_result[im_with_separated_blobs == blob + 1] = 255
    im_result = im_result/255.0

    return im_result


def get_elevation_underground_extents(image):
    """
    Get extents of bounding box underground regions in an elevation.

    Parameters
    ----------
    image : array_like
        Minimap with caption and surrounding border.

    Returns
    -------
    extents : tuple of (x_topleft, y_topleft, x_botright, y_botright)
        Indices of the rectangle bounding all underground regions.
    """
    # safe_imshow(image=image, title='Original')
    im_result = get_underground_pixels(image)

    # safe_imshow(image=im_result, title='Cleaned Up Mask')

    # Find bounding rectangles of mask shapes, use outermost values to define
    # underground extents of this elevation
    # https://stackoverflow.com/a/21108680 and
    # https://stackoverflow.com/a/60106329
    im_result = im_result.astype(np.uint8)
    contours, hierarchy = cv2.findContours(im_result, cv2.RETR_LIST,
                                           cv2.CHAIN_APPROX_SIMPLE)[-2:]
    idx = 0
    most_left, most_right, most_up, most_down = None, None, None, None
    for cnt in contours:
        idx += 1
        x, y, w, h = cv2.boundingRect(cnt)
        if (most_left is None) or (x < most_left):
            most_left = x
        if (most_right is None) or (x+w > most_right):
            most_right = x+w
        if (most_up is None) or (y < most_up):
            most_up = y
        if (most_down is None) or (y+h > most_down):
            most_down = y+h
    return (most_left, most_up, most_right, most_down)


def update_overall_underground_extents(elevation_extents, current_extents):
    """
    Update overall extents of underground regions for all elevations.

    Parameters
    ----------
    elevation_extents : tuple of (int, int, int, int)
        Underground extents of an elevation, ordered as
        (left, top, right, bottom).
    current_extents : tuple of (int, int, int, int) or (None, None, None, None)
        Current maximum extents of all elevations, ordered as
        (left, top, right, bottom).

    Returns
    -------
    current_extents : tuple of (int, int, int, int)
        Updated  maximum extents of all elevations, ordered as
        (left, top, right, bottom).
    """
    left, top, right, bottom = (elevation_extents)
    leftmost, topmost, rightmost, bottommost = (current_extents)
    if (leftmost is None) or (left < leftmost):
        leftmost = left
    if (rightmost is None) or (right > rightmost):
        rightmost = right
    if (topmost is None) or (top < topmost):
        topmost = top
    if (bottommost is None) or (bottom > bottommost):
        bottommost = bottom
    return (leftmost, topmost, rightmost, bottommost)


def main(world, elevation_start, elevation_step, zoom,
         basedir, embark_size):
    """
    Convert a folder of minimaps into editable Excel format.

    Parameters
    ----------
    basedir : str
        Base directory containing folders with minimap screenshots
    world : str
        Folder in basedir containing minimap screenshots
    elevation_start : int
        Elevation of first minimap screenshot
    elevation_step : int
        Elevation step size (-1 for descending order, 1 for ascending order)
    zoom : int
        Spreadsheet zoom level (in percent)
    embark_size : tuple of (int, int)
        Size of the embark area. Currently only supports square embark regions.

    Returns
    -------
    None.

    """
    # worlds = find_valid_worlds(basedir)
    # for world in worlds:
    # print('world:', world)
    elevation = elevation_start
    leftmost, rightmost, topmost, bottommost = None, None, None, None
    minimap_dict = {}
    if not glob.glob(os.path.join(basedir, world, '*.png')):
        raise OSError('{0} contains no PNG screenshots'.format(os.path.join(basedir, world)))
    for png in glob.glob(os.path.join(basedir, world, '*.png')):
        # print(png)
        minimap = cv2.imread(png)
        minimap = crop_top_titlebar(minimap)
        minimap = crop_right_window_border(minimap)
        # try:
        #     elevation = get_elevation(minimap)
        # except RuntimeError:
        #     elevation = None
        # verify_elevation(minimap, png, elevation)
        # print("{0} is from elevation {1}".format(png, elevation))
        minimap_dict[elevation] = minimap
        (left, top, right, bottom) = get_elevation_underground_extents(minimap)
        # print("Underground extents from ({0}, {1}) to ({2}, {3})".format(
        #       left, top, right, bottom))
        (leftmost, topmost,
         rightmost, bottommost) = update_overall_underground_extents(
                                    (left, top, right, bottom),
                                    (leftmost, topmost, rightmost, bottommost)
                                    )
        elevation = elevation + elevation_step
    # Figure out overall map extents from elevation underground extents
    # print("Overall extents from ({0}, {1}) to ({2}, {3})".format(
    #     leftmost, topmost, rightmost, bottommost))

    wb = Workbook()
    sheet_first_row = 1
    sheet_last_row = sheet_first_row + 48*embark_size[0] - 1
    sheet_first_column = 1
    sheet_last_column = sheet_first_column + 48*embark_size[1] - 1
    sheet_first_column_letter = get_column_letter(sheet_first_column)
    sheet_last_column_letter = get_column_letter(sheet_last_column)
    print("Converting underground pixels in elevation:", end='', flush=True)
    for elevation, minimap in minimap_dict.items():
        ws = wb.create_sheet(title="Elev {0}".format(elevation))
        print(" {0}".format(elevation), end='', flush=True)
        # All minimaps have a common upper-right location
        pixels = get_underground_pixels(minimap,
                                        (leftmost, rightmost,
                                         topmost, bottommost))
        # print(pixels.shape)
        # print(pixels[0, :])
        # safe_imshow(image=pixels)
        x_orig = np.linspace(0, 1,
                             minimap[topmost:bottommost,
                                     leftmost:rightmost].shape[1])
        y_orig = np.linspace(0, 1,
                             minimap[topmost:bottommost,
                                     leftmost:rightmost].shape[0])
        # print(x_orig.shape, y_orig.shape, pixels.shape)
        x_interp = np.linspace(0, 1, 48*embark_size[0])
        y_interp = np.linspace(0, 1, 48*embark_size[1])
        interpolant = scipy.interpolate.RectBivariateSpline(y_orig,
                                                            x_orig,
                                                            pixels)
        row = 1
        for x in x_interp:
            col = 1
            for y in y_interp:
                pixel = np.round(interpolant(y, x))
                if (pixel==1):
                    _ = ws.cell(column=row, row=col, value=pixel[0, 0])
                col = col + 1
            row = row + 1
        # Create conditional format rule for this sheet
        rule = ColorScaleRule(start_type='min', start_color='FFFFFF',
                              end_type='max', end_color='000000')
        ws.conditional_formatting.add('{0}{1}:{2}{3}'.format(
            sheet_first_column_letter, sheet_first_row,
            sheet_last_column_letter, sheet_last_row), rule)
        # Set width of columns
        for i in range(sheet_first_column, sheet_last_column+1):
            ws.column_dimensions[get_column_letter(i)].width = 2.875
        ws.sheet_view.zoomScale = zoom

    print(" done.")

    # wb.remove('Sheet')
    print("Saving spreadsheet: ", end='', flush=True)
    wb.save("{0}.xlsx".format(world))
    print("done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--basedir", type=str, default='screenshots',
                        help="Base directory containing folders with minimap screenshots (defaults to 'screenshots')")
    parser.add_argument("--zoom", type=int, default=25,
                        help="Spreadsheet zoom level (in percent, defaults to 25)")
    parser.add_argument("world", type=str,
                        help="Folder in basedir containing minimap screenshots")
    parser.add_argument("elevation_start", type=int,
                        help="Elevation of first minimap screenshot")
    parser.add_argument("elevation_step", type=int,
                        help="Elevation step size (-1 for descending order, 1 for ascending order)")
    parser.add_argument("embark_size", type=int, default=4,
                        help="Embark map size (only square embarks supported currently, defaults to 4)")
    args = parser.parse_args()
    main(world=args.world, elevation_start=args.elevation_start,
         elevation_step=args.elevation_step, basedir=args.basedir,
         embark_size=(args.embark_size, args.embark_size),
         zoom=args.zoom)
    # main(world='Camade Oroni',
    #      elevation_start=70,
    #      elevation_step=-1)
