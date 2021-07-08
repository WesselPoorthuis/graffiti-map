from PIL import Image, ExifTags
from PIL.ExifTags import TAGS, GPSTAGS
from pyheif_pillow_opener import register_heif_opener

import folium
from folium import IFrame
from folium.plugins import Fullscreen
import pandas
import base64

import os
import sys
# Required to import from root directory
sys.path.append(os.path.dirname(os.path.dirname(__file__)))


def get_exif(filename):
    if filename.endswith('.HEIC'):
        register_heif_opener()

    image = Image.open(photo_dir + '/' + filename)
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
    Rotates image based on orienation when photo was taken.
    '''
    for orientation in ExifTags.TAGS.keys():
        if ExifTags.TAGS[orientation]=='Orientation':
            break

    exif = image._getexif()

    if exif[orientation] == 3:
        image=image.rotate(180)
    elif exif[orientation] == 6:
        image=image.rotate(270)
    elif exif[orientation] == 8:
        image=image.rotate(90)
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
        elif old_height > max_height:
            height = max_height
            width = old_width * height/old_height
        else:
            height = old_height
            width = old_width
    else:
        if old_height > max_height:
            height = max_height
            width = old_width * height/old_height
        elif old_width > max_width:
            width = max_width
            height = old_height * width/old_width
        else:
            height = old_height
            width = old_width

    new_size = (int(round(width)), int(round(height)))
    return new_size

# Base parameters
max_width = 1000
max_height = 750

# Lists
filelist = []
lat = []
lon = []
removelist = []

# Directories
current_dir = os.path.dirname(os.path.realpath(__file__))
photo_dir = current_dir + '/photos'
resize_dir = current_dir + '/resized'

# Create base map
print('Creating base map...')
m=folium.Map(location=[52.0907, 5.1214], zoom_start=14)
fullscreen = Fullscreen()
fullscreen.add_to(m)
# Add photos in dir to list
print('Gathering photographs...')
for photos in os.listdir(photo_dir):
    # if photos.endswith('.jpg'):
    #     o+=1
    #     filelist.append(photos)
    if photos.endswith('.HEIC'):
        filelist.append(photos)

# Get coordinates
print('Getting coordinates...')
for file in filelist:
    exif = get_exif(file)
    if exif is None:
        removelist.append(file)
    else:
        latlon = get_decimal_coordinates(exif['GPSInfo'])
        lat.append(latlon[0])
        lon.append(latlon[1])

filelist = [x for x in filelist if x not in removelist]

# Create dataframe
index = range(1,len(filelist)+1)
columns = ['filename','lat','lon']
df = pandas.DataFrame(index=index, columns=columns)

df['filename']=filelist
df['lat']=lat
df['lon']=lon

# Process images
print('Processing images...')
for lat,lon,filename in zip(df['lat'],df['lon'],df['filename']):
    image = Image.open(photo_dir + '/' + filename)
    image = rotate_image(image)
    new_size = calculate_size(image)
    (width, height) = new_size
    image = image.resize(new_size, Image.ANTIALIAS)
    resized_location = resize_dir + '/' + filename
    image.save(resized_location, 'jpeg', quality=100)

# Construct markers
print('Constructing markers...')
for lat,lon,filename in zip(df['lat'],df['lon'],df['filename']):
    # image = Image.open(resized_location)
    encoded = base64.b64encode(open(resize_dir + '/' + filename, 'rb').read())
    html = ''' <img src="data:image/png;base64,{}">'''.format
    iframe = IFrame(html(encoded.decode('UTF-8')), width=width+20, height=height+20)
    popup = folium.Popup(iframe, max_width=1000)
    icon = folium.Icon(color='red')
    marker = folium.Marker(location=[lat, lon], popup=popup, icon=icon)
    marker.add_to(m)


# Saving map
print('Saving map...')

filename = "map.html"
path = os.path.join(current_dir, filename)
m.save(path)
