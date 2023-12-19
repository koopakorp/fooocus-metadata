import os
from PIL import Image
from PIL.PngImagePlugin import PngInfo
from bs4 import BeautifulSoup

DIRECTORY = 'C:\StabilityMatrix\Data\Images\Fooocus'
UPDATE_MODE = True # False won't update the file or anything
RENAME_MODE = True # if UPDATE_MODE is True, this determines if it saves the file with a new name (adds _meta on end of new filename)

HEADINGS = ['Fooocus V2 Expansion', 'Styles', 'Resolution', 'Sharpness', 'Guidance Scale', 'ADM Guidance', 'Base Model', 'Refiner Model', 'Refiner Switch', 'Sampler', 'Scheduler', 'Seed', 'LoRA', 'Version']
SPECIAL_HEADINGS = ['Prompt', 'Negative Prompt', 'Performance']

def scandir(dirname):
    subfolders= [f.path for f in os.scandir(dirname) if f.is_dir()]
    for dirname in list(subfolders):
        subfolders.extend(scandir(dirname))
    return subfolders

def strip_html(data):
    return "|||".join(data.stripped_strings).split('|||')

def update_image(image, metadata):
    if UPDATE_MODE == True:
        print(f'Updating {image}...\n')
        with Image.open(image) as f:
            new_meta = PngInfo()
            new_meta.add_text("parameters", metadata)
            if RENAME_MODE == False:
                f.save(image,pnginfo=new_meta)
            else:
                f.save(image.replace('.png','_meta.png'),pnginfo=new_meta)
    else:
        print(f'Non-update mode. No change. Image: {image} - Metadata: {metadata}')

def check_image(image):
    with Image.open(image.replace('.png','_meta.png')) as f:
        metadata = f.info
        print(metadata)

def build_text(metadata):
    text = ''
    data_length = len(metadata)-1
    
    for heading in SPECIAL_HEADINGS:
        if heading in metadata or heading + ':' in metadata:
            try:
                head_index = metadata.index(heading)
            except:
                head_index = metadata.index(heading+':')
            
            if ('Prompt' == heading or 'Prompt:' == heading) and metadata[head_index+1] not in HEADINGS:
                text += metadata[head_index+1] + ' \n'
            if 'Negative Prompt' in heading and metadata[head_index+1] not in HEADINGS:
                text += 'Negative prompt: ' + metadata[head_index+1] + ' \n'
            if 'Performance' in heading and metadata[head_index+1] not in HEADINGS:
                match metadata[head_index+1]:
                    case "Speed":
                        text += "Steps: 30"
                    case "Quality":
                        text += "Steps: 60"
                    case "Extreme Speed":
                        text += "Steps: 8"
                    case _:
                        text += "Steps: 9000"
        else:
            return ''
        
    for index, val in enumerate(metadata, start=0):
        if val not in HEADINGS and val+':' not in HEADINGS:
            continue
        
        if metadata[index+1] in HEADINGS or metadata[index+1]+':' in HEADINGS:
            continue 
        else:
            match val:
                case 'Guidance Scale':
                    text += f', CFG scale: {metadata[index+1]}'
                case 'Base Model':
                    text += f', Model: {metadata[index+1]}'
                case _:
                    text += f', {val}: {metadata[index+1]}'
    return text

def main():
    # get list of directories
    sub_dirs = scandir(DIRECTORY)
    # loop through directories
    for dir in sub_dirs:
        print(f'Processing images in {dir}...')
        # get list of files in directory
        files = [f.name for f in os.scandir(dir) if f.is_file()]
        # check if log.html is there -- if not, go to next directory
        if 'log.html' not in files:
            print(f'No log file for {dir}. Skipping this directory.')
            continue
        else:
            log_path = dir + "\\" + "log.html"
            with open(log_path) as f:
                soup = BeautifulSoup(f, 'html.parser')
            # get a list of all divs in the html log file
            divs = soup.findAll("div")
            for div in divs:
                metadata = {}
                # strip html out -- output is a list in ['key:', 'value', 'key:', 'value'] format
                data = strip_html(div)

                # latest log.html has nested divs, just skipping the empty one.
                if len(data) == 1:
                    continue

                # build out A1111 style string from data
                text_meta = build_text(data)

                # get image name from first field value
                image_file = dir + '\\' + data[0].strip()
                
                #check if file exists
                check_file  = os.path.isfile(image_file)
                if check_file == True:
                    update_image(image_file, text_meta)
                    #check_image(image_file)

if __name__ == "__main__":
    main()