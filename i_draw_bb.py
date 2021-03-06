# -*- coding: utf-8 -*-
# Credits - Ismail.
# modified by achin a little bit

import csv # write in csv format
import os
import hashlib
from PIL import Image, ImageDraw
import argparse
import shutil

data_folder = os.path.join(os.getcwd(), 'data')

def crop_image(image, rectangle):
    cropped = image.crop([rectangle[0], rectangle[1], rectangle[0] + rectangle[2], rectangle[1] + rectangle[3]])
    bw = cropped.convert('1')
    width, height = bw.size
    pix = bw.load() # getting the pixel values
    horzhist = [0]*height
    
    for i in range(height):
        total = 0
        for j in range(width):
            total += pix[j, i]
        horzhist[i] = total
    
    first = horzhist[0] # Get the first row intensity
    last = horzhist[-1]
    j = 0
    for i in range(1, height):
        if horzhist[i] != first:
            break
    for j in range(height - 2, -1, -1):
        if horzhist[j] != last:
            break
    # Return the new values
            
    new_rect = [0]*4
    new_rect[0] = rectangle[0]
    
    if j > 2:
        new_rect[1] = rectangle[1] + j
    else:
        new_rect[1] = rectangle[1]
        j = 0
        
    if i < height - 2:
        i = height - (i + 1)
        new_rect[3] = rectangle[3] - i - j 
    else:
        new_rect[3] = rectangle[3] - j 
    new_rect[2] = rectangle[2]
    
    return new_rect

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("language", help="lang_ja,lang_ko,lang_es")
    parser.add_argument("batch_no", help="enter batch number")
    parser.add_argument("level", help="enter level number 0 - ch, 1 - word, 2 - line")
    args = parser.parse_args()
    CURR_LANG = args.language
    counter = str(args.batch_no)
    level = int(args.level)

    lang_folder = os.path.join(data_folder, CURR_LANG)

    ann_img_name = "images_annotated_folder_"
    if level == 0:
        ann_img_name += "cl"
    elif level == 1:
        ann_img_name += "wl"
    elif level == 2:
        ann_img_name += "ll"


    images_annotated_folder = os.path.join(lang_folder, ann_img_name)
    # images_raw_folder = os.path.join(lang_folder, 'images_raw_folder')
    images_folder = os.path.join(lang_folder, "images")

    create_directory(images_annotated_folder)
    # create_directory(images_raw_folder)
    
    if '-' in counter:
        spl_array = counter.strip().split('-')
        for i in range(int(spl_array[0]), int(spl_array[1])+1):
            process_transcription_file(level, lang_folder, images_annotated_folder, images_folder, str(i))
    else:
        process_transcription_file(level, lang_folder, images_annotated_folder,  images_folder, counter)
    # for each_file in os.listdir(lang_folder):
    #     if 'transcription_' in each_file:
    

def process_transcription_file(level, lang_folder, images_annotated_folder,  images_folder, counter):

    name_trans = None
    name_ann = None

    if level == 0:
        name_trans = "transcription_cl_"
        name_ann = "annotation_cl_"
    elif level == 1:
        name_trans = "transcription_wl_"
        name_ann = "annotation_wl_"
    elif level == 2:
        name_trans = "transcription_ll_"
        name_ann = "annotation_ll_"


    transcription = os.path.join(lang_folder, name_trans+counter+'.txt')

    outfile = open(os.path.join(lang_folder, name_ann+counter+'.csv'), 'w')

    fields = ['file', 'x0', 'y0', 'width', 'height', 'trans', 'md5hash']
    writer = csv.DictWriter(outfile, delimiter=',', lineterminator='\n', fieldnames=fields)
    writer.writeheader()
    annotation = {}  # contains all the annotation md5hash


    if images_annotated_folder:
        for files in os.listdir(images_annotated_folder):
            if files.endswith('csv'):
                with open(os.path.join(images_annotated_folder, files)) as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if 'md5hash' in row:
                            annotation[row['md5hash']] = row['file']


    first = True
    first_below = True
    name = image = ''

    with open(transcription) as fi:
        for line in fi:
            # pause_n_print('line = '+line)
            line = line.strip()
            if 'SlideName' in line:
                elements = line.split(" - ")
                ppt_name = elements[1]
                # outfile.write(line + '\n')
                if first == False:
                    print('saving = ', name)
                    image.save(os.path.join(images_annotated_folder, name))
                first = False
                first_below = True
            elif 'Slide' in line:
                elements = line.split()
                slide_num = elements[1]
                # outfile.write(line + '\n')
                if first_below == False:
                    print('saving = ', name)
                    image.save(os.path.join(images_annotated_folder, name))
                first_below = False
                name = ppt_name + "_"+slide_num+"_"+str(counter) + '.jpg'
                image_file = os.path.join(images_folder, name)
                try:
                    # save the image to another folder
                    # shutil.copyfile(image_file, os.path.join(images_raw_folder, name))
                    image = Image.open(os.path.join(images_folder, name))
                    # os.remove(image_file)
                except:
                    print('xxxxxxxxxxxxxxxxxxxxx Exception opening file xxxxxxxxxxxxxxxxxxxxxx')
                    continue
                dig = hashlib.md5(image.tobytes()).hexdigest()
                drawable = ImageDraw.Draw(image)

            else:
                elements = line.split()
                rectangle = elements[:4]
                rectangle = list(map(int, rectangle))

                # Now we have to do the processing to make the bounding box
                # tight
                try:
                    new_rect = crop_image(image, rectangle)
                except :
                    # decompression bomb exception handle. reject the sample.
                    print('exception in cropping')
                    continue
                new_rect[2] = new_rect[0] + new_rect[2]
                new_rect[3] = new_rect[1] + new_rect[3]
                new_rect[1], new_rect[3] = new_rect[3], new_rect[1]
                drawable.rectangle(new_rect, outline=(255, 0, 0, 255))
                trans = ' '.join(elements[4:])
                if dig not in annotation or name == annotation[dig]:
                    annotation[dig] = name
                    dic = {}
                    dic['file'] = name
                    dic['x0'] = new_rect[0]
                    dic['y0'] = new_rect[1]
                    dic['width'] = new_rect[2] - new_rect[0]  # width
                    dic['height'] = new_rect[3] - new_rect[1]  # height
                    dic['trans'] = trans
                    dic['md5hash'] = dig
                    writer.writerow(dic)
        print('saving last image = ' , name)
        image.save(os.path.join(images_annotated_folder, name))

    outfile.close()

def create_directory(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

if __name__=='__main__':
    main()
