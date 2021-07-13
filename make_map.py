from PIL import Image, ExifTags
from PIL.ExifTags import TAGS, GPSTAGS
from pyheif_pillow_opener import register_heif_opener

import folium
from folium import IFrame
from folium.plugins import Fullscreen, MarkerCluster

import base64

import os
import sys

# Required to import from root directory
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

def get_exif(image):
    try:
        exif = image._getexif()
    except:
        exif = None

    if exif is not None:
        for key, value in exif.copy().items():
            name = TAGS.get(key, key)
            exif[name] = exif.pop(key)

        if 'GPSInfo' in exif.copy():
            for key in exif['GPSInfo'].copy().keys():
                name = GPSTAGS.get(key,key)
                exif['GPSInfo'][name] = exif['GPSInfo'].pop(key)
        else:
            exif = None
    return exif

def get_decimal_coordinates(info):
    for key in ['Latitude', 'Longitude']:
        if 'GPS'+key in info and 'GPS'+key+'Ref' in info:
            e = info['GPS'+key]
            ref = info['GPS'+key+'Ref']
            info[key] = ( e[0][0]/e[0][1] +
                          e[1][0]/e[1][1] / 60 +
                          e[2][0]/e[2][1] / 3600
                        ) * (-1 if ref in ['S','W'] else 1)

    if 'Latitude' in info and 'Longitude' in info:
        return [info['Latitude'], info['Longitude']]

def rotate_image(image):
    '''
    Rotates image based on orienation when photo was taken
    '''
    for orientation in ExifTags.TAGS.keys():
        if ExifTags.TAGS[orientation]=='Orientation':
            break

    exif = image._getexif()

    if exif[orientation] == 3:
        image=image.rotate(180, expand = True)
    elif exif[orientation] == 6:
        image=image.rotate(270, expand = True)
    elif exif[orientation] == 8:
        image=image.rotate(90, expand = True)
    return image

def calculate_size(image):
    '''
    Resizes image to fit popup
    '''
    old_width, old_height = image.size
    if old_width > old_height:
        if old_width > max_width:
            width = max_width
            height = old_height * width/old_width
    else:
        if old_height > max_height:
            height = max_height
            width = old_width * height/old_height

    new_size = (int(round(width)), int(round(height)))
    return new_size

# Base parameters
max_width = 1000
max_height = 750
filelist = []
i = 0
j = 0

# Directories
current_dir = os.path.dirname(os.path.realpath(__file__))
photo_dir = current_dir + '/photos'
resize_dir = current_dir + '/resized'

# Create base map
print('Creating base map...')
m=folium.Map(location=[52.0907, 5.1214], zoom_start=14)
marker_cluster = MarkerCluster().add_to(m)
fullscreen = Fullscreen()
fullscreen.add_to(m)

# Add photos in dir to list
print('Gathering photographs from directory...')
for photos in os.listdir(photo_dir):
    if photos.endswith('.HEIC'):
        filelist.append(photos)
    if photos.endswith('.jpg'):
        filelist.append(photos)
    if photos.endswith('.jpeg'):
        filelist.append(photos)

print('Processing photographs...')
for file in filelist:
    # Open file
    if file.endswith('.HEIC'):
        register_heif_opener()
    image = Image.open(photo_dir + '/' + file)

    # Get coordinates
    exif = get_exif(image)
    if exif is None:
        j+=1
        continue
    (lat,lon) = get_decimal_coordinates(exif['GPSInfo'])

    # Process image
    image = rotate_image(image)
    (width, height)  = calculate_size(image)
    image = image.resize((width, height) , Image.ANTIALIAS)
    resized_location = resize_dir + '/' + file
    image.save(resized_location, 'jpeg', quality=100)

    # Create marker
    encoded = base64.b64encode(open(resized_location, 'rb').read())
    html = ''' <img src="data:image/png;base64,{}">'''.format
    iframe = IFrame(html(encoded.decode('UTF-8')), width=width+20, height=height+20)
    popup = folium.Popup(iframe, max_width=1000)
    icon = folium.Icon(color='red', icon='camera')
    marker = folium.Marker(location=[lat, lon], popup=popup, icon=icon)
    marker.add_to(marker_cluster)
    i+=1
    print(f'    Added {i} photographs to the map', end='\r')

print(f'\n    {j} photographs had no geodata and are thus not included in the map')

# Saving map
print('Saving map...')
filename = "graffiti-map.html"
path = os.path.join(current_dir, filename)
m.save(path)
print('Saved')
