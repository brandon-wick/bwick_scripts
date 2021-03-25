"""
Script for sorting all the photos that is stored in the Load directory
"""
import os
import shutil
import datetime

# Get current time
now = datetime.datetime.now()

# Get path of the hard drive
drive_path = os.path.dirname(__file__)

pictures_dir = os.path.join(drive_path, "Pictures", str(now.year))
videos_dir = os.path.join((drive_path), "Videos", str(now.year))

if not os.path.exists(pictures_dir):
    os.makedirs(pictures_dir)

if not os.path.exists(videos_dir):
    os.makedirs(videos_dir)

# Write the name of the directory here,
# that needs to get sorted
path = drive_path + "/Load"

# This will create a properly organized
# list with all the filename that is
# there in the directory
list_ = os.listdir(path)

# This will go through each and every file
for file_ in list_:
    name, ext = os.path.splitext(file_)
    creation_timestamp = datetime.datetime.fromtimestamp(os.path.getctime(os.path.join(path, file_)))

    # This is going to store the extension type
    ext = ext[1:]

    # This forces the next iteration,
    # if it is the directory
    if ext == '':
        continue

    # Move all photos to the photo directory and rename file to creation time stamp
    if ext in ["JPG", "jpg", "jpeg", "HEIC", "CR2", "PNG", "png", "raw", "RAW", "gif", "GIF"]:

        rename = "IMG_" + creation_timestamp.strftime("%Y%m%d%H%M%S") + "." + ext
        if not os.path.exists(os.path.join(pictures_dir, rename)):
            shutil.move(os.path.join(path, file_), os.path.join(pictures_dir, rename))

    # Move all videos to the video directory and rename file to creation time stamp
    if ext in ["mp4", "MP4", "mov", "MOV", "HEVC", "M4V", "m4v", "M4V", "QT", "qt", "WMV"]:

        rename = "vid_" + creation_timestamp.strftime("%Y%m%d%H%M%S") + "." + ext
        if not os.path.exists(os.path.join(videos_dir, rename)):
            shutil.move(os.path.join(path, file_), os.path.join(videos_dir, rename))

    # anything else, skip
    else:
        continue