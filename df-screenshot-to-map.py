#!/usr/bin/env python3

from collections import OrderedDict
import cv2 as cv
import glob
import imageio.v2 as imageio
import os
from PIL import Image
import pyexcel_ods3
import stitching
import time

def find_valid_worlds(basedir):
    worlds = glob.glob(os.path.join(basedir, '*'))
    valid_worlds = []
    if worlds:
        for world in worlds:
            if os.path.isdir(world):
                elevations = find_valid_elevations(world)
                if elevations:
                    valid_worlds.append(world)
    return valid_worlds

def find_valid_elevations(world):
    elevations = glob.glob(os.path.join(world, '*'))
    valid_elevations = []
    if elevations:
        for elevation in elevations:
            if os.path.isdir(elevation):
                screenshots = glob.glob(os.path.join(elevation, '*.png'))
                if screenshots:
                    valid_elevations.append(elevation)
    return valid_elevations

def stitch_images_in_elevation(elevation):
    stitched_file = '{0}.png'.format(elevation)
    if os.path.exists(stitched_file):
        print("Stitched file {0} already exists".format(stitched_file))
    else:
        screenshots = glob.glob(os.path.join(elevation, '*.png'))
        print("Found screenshots in {0}, stitching.".format(elevation))
        # print(screenshots)
        settings = {} # {"warper_type": "plane", "block_size": 128}
        #stitcher = stitching.Stitcher(**settings)
        stitcher = stitching.AffineStitcher(**settings)
        start = time.time()
        panorama = stitcher.stitch(screenshots)
        end = time.time()
        print('{0:.1f} seconds elaspsed'.format(end-start))
        print("Saving to {0}".format(stitched_file))
        cv.imwrite(stitched_file, panorama)
    return stitched_file

def find_registration_mark(stitched_file, template_file):
    # Find the registration mark to get top-left origin of embark
    template = cv.imread(template_file) 
    stitched_image = cv.imread(stitched_file)
    w, h = template.shape[-2::-1]
    res = cv.matchTemplate(stitched_image, template, cv.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv.minMaxLoc(res)
    top_left = max_loc
    bottom_right = (top_left[0] + w, top_left[1] + h)
    return top_left, bottom_right

def crop_image_to_embark(stitched_file, embark_size, top_left, bottom_right):
    # top_left to bottom_right makes up a 2x2 tile space
    # embarks have 48x48 tiles per embark space (so 4x4 embark is 192x192 tiles)
    # let w = bottom_right[0] - top_left[0], h = bottom_right[1] - top_left[1]
    # crop starting at top_left, and extending embark_size*48*w/2
    w = bottom_right[0] - top_left[0]
    h = bottom_right[1] - top_left[1]
    tile_size = int(w/2)
    tile_count = embark_size[0]*48
    cropped_size = int(tile_size*tile_count)
    stitched_image = cv.imread(stitched_file)
    print("cropping original image to size {0} x {0}".format(cropped_size))
    cropped_image = stitched_image[top_left[1]:(top_left[1]+cropped_size), top_left[0]:(top_left[0]+cropped_size)]
    dir = os.path.dirname(stitched_file)
    basename = os.path.basename(stitched_file)
    cropped_file = os.path.join(dir, 'cropped-'+basename)
    cv.imwrite(cropped_file, cropped_image)
    return cropped_file

def mask_cropped_file(cropped_file):
    print("Thresholding and masking cropped image")
    grey = cv.cvtColor(cv.imread(cropped_file), cv.COLOR_BGR2GRAY)
    # cv.imwrite('grey.png', grey)
    thresh = cv.threshold(grey, 56, 255, cv.THRESH_BINARY_INV)[1]
    # cv.imwrite('grey-thresh.png', thresh)
    # Filter using contour area and remove small noise
    cnts = cv.findContours(thresh, cv.RETR_TREE, cv.CHAIN_APPROX_SIMPLE)
    cnts = cnts[0] if len(cnts) == 2 else cnts[1]
    for c in cnts:
        area = cv.contourArea(c)
        if area < 3000:
            cv.drawContours(thresh, [c], -1, (0,0,0), -1)
    # cv.imwrite('grey-thresh2.png', thresh)
    kernel = cv.getStructuringElement(cv.MORPH_RECT, (tile_size+1, tile_size+1))
    close = 255 - cv.morphologyEx(thresh, cv.MORPH_CLOSE, kernel, iterations=2)
    dir = os.path.dirname(cropped_file)
    basename = os.path.basename(cropped_file)
    masked_file = os.path.join(dir, 'masked-'+basename)
    cv.imwrite(masked_file, close)
    return masked_file

def reduce_masked_file(masked_file, tile_size, embark_size):
    # Resize down so each new pixel corresponds to a tile
    im = Image.open(masked_file)
    tile_count = embark_size[0]*48
    masked_size = int(tile_size*tile_count)
    reduced_size = masked_size/tile_size
    print("Reducing image to size", reduced_size)
    dir = os.path.dirname(masked_file)
    basename = os.path.basename(masked_file)
    reduced_file = os.path.join(dir, 'reduced-'+basename)
    im.thumbnail((reduced_size, reduced_size), Image.Resampling.NEAREST)
    im.save(reduced_file)
    return reduced_file

def convert_to_ods(reduced_file):
    # Converting cropped image into "diggable" and "not diggable"
    print("Converting to ODS format")
    bw_data = imageio.imread(reduced_file)
    data = OrderedDict()
    data.update({'Sheet 1': bw_data.tolist()})
    dir = os.path.dirname(reduced_file)
    basename = os.path.basename(reduced_file)
    basest_name = os.path.splitext(basename)[0]
    ods_file = os.path.join(dir, basest_name+'.ods')
    pyexcel_ods3.save_data(ods_file, data)
    return ods_file

if __name__ == "__main__":
    worlds = find_valid_worlds('screenshots')
    # print('worlds:', worlds)
    for world in worlds:
        print('world:', world)
        elevations = find_valid_elevations(world)
        for elevation in elevations:
            # print('elevation:', elevation)
            stitched_file = stitch_images_in_elevation(elevation)
            template_file = os.path.join('templates', 'registration-mark.png')
            top_left, bottom_right = find_registration_mark(stitched_file, template_file)
            w = bottom_right[0] - top_left[0]
            h = bottom_right[1] - top_left[1]
            tile_size = int(w/2)
            print('Found registration mark at from {0} to {1} ({2} x {3})'.format(top_left, bottom_right, w, h))
            embark_size = (4, 4)
            cropped_file = crop_image_to_embark(stitched_file, embark_size, top_left, bottom_right)
            masked_file = mask_cropped_file(cropped_file)
            reduced_file = reduce_masked_file(masked_file, tile_size, embark_size)
            ods_file = convert_to_ods(reduced_file)
