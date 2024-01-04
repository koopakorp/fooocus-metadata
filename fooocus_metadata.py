# --------------------------------------------------------------------------------------
# Since Fooocus change the log.html file all the time, I'm not going to support every iteration of it.
# 2023.12.25: 
# - Changed a bit so CivitAI will pick up sampler.
# - Added some code to handle the new button, which has the metadata in json format.
# 2023.12.26:
# - Added some code to grab the hash from StabilityMatrix info files.
# 2023.12.29:
# - Did more to handle the json format in the button
# - Implemented calculating hash if needed.
# - Cleaned up handling older log files (at least early december)
# - Added hash section for button json. Civitai will pick up all loras used as resources with this.
# 2024.01.03:
# - Added option to process just a single file rather than deal with whole directories. (button json processing)
# --------------------------------------------------------------------------------------
import os
import json
import hashlib
from urllib.parse import unquote
from PIL import Image
from PIL.PngImagePlugin import PngInfo
from bs4 import BeautifulSoup


DIRECTORY = 'C:\AI_ART\StabilityMatrix\Data\Images\Fooocus'
MODEL_DIRECTORY = 'C:\AI_ART\StabilityMatrix\Data\Models\StableDiffusion'
LORA_DIRECTORY = 'C:\AI_ART\StabilityMatrix\Data\Models\Lora'
PROCESS_MODE = 'FILE' # Process entire directories or just a single file.
PROCESS_FILE = 'C:\AI_ART\StabilityMatrix\Data\Images\Fooocus\\2024-01-03\\2024-01-03_20-44-35_8488.png'
UPDATE_MODE = True # False won't update the file or anything
RENAME_MODE = True # if UPDATE_MODE is True, this determines if it saves the file with a new name (adds _meta on end of new filename)

HEADINGS = ['Fooocus V2 Expansion', 'Styles', 'Resolution', 'Sharpness', 'Guidance Scale', 'ADM Guidance', 'Base Model', 'Refiner Model', 'Refiner Switch', 'Sampler', 'Scheduler', 'Seed', 'LoRA', 'LoRA 1', 'LoRA 2', 'LoRA 3', 'LoRA 4', 'LoRA 5', 'LoRA 6', 'Version']
SPECIAL_HEADINGS = ['Prompt', 'Negative Prompt', 'Performance']

def scandir(dirname):
    subfolders= [f.path for f in os.scandir(dirname) if f.is_dir()]
    for dirname in list(subfolders):
        subfolders.extend(scandir(dirname))
    return subfolders

def strip_html(data):
    return "|||".join(data.stripped_strings).split('|||')

def get_model_hash(model, type="SD", method="SM-Info"):
    file_found = False

    # find file
    if type == 'SD':
        for root, dirs, files in os.walk(MODEL_DIRECTORY):
            if model in files:
                file_found = True
                break
    elif type == 'lora':
        for root, dirs, files in os.walk(LORA_DIRECTORY):
            if model in files:
                file_found = True
                break
    
    if file_found == False:
        return ''
    
    if method == "SM-Info":
        try:
            info_file = root + '\\' + model
            info_file = info_file.replace('.safetensors', '.cm-info.json')
            print(info_file)
            info_json = json.loads(open(info_file, 'r').read())
            return info_json['Hashes']['SHA256']
        except:
            print('Could not find model information.')
            return ''
    elif method == 'calculate':
        print('Calculating hash...')
        info_file = root + model
        sha256_hash = hashlib.sha256()
        with open(info_file, 'rb') as f:
            for byte_block in iter(lambda: f.read(4096),b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    else:
        print('Dunno.')

def parse_button(div):
    try:
        button_json = div.findAll("button")[0].get("onclick")
        button_json = button_json.replace('to_clipboard(\'', '').replace('\')', '')
        button_json = unquote(button_json)
        button_json = json.loads(button_json)
        #print(f'test: {button_json}')
        return button_json
    except:
        return None

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

def build_text_json(metadata):
    print('building metadata from json...')
    text = ''
    resource_hashes = {}
    meta_keys = []
    meta_keys = list(metadata.keys())
    if 'Prompt' in metadata:
        text += metadata['Prompt'] + '\n'
        meta_keys.remove('Prompt')
    if 'Negative Prompt' in metadata:
        text += 'Negative prompt: ' + metadata['Negative Prompt'] + ' \n'
        meta_keys.remove('Negative Prompt')
    if 'Performance' in metadata:
        match metadata['Performance']:
            case "Speed":
                text += "Steps: 30"
            case "Quality":
                text += "Steps: 60"
            case "Extreme Speed":
                text += "Steps: 8"
            case _:
                text += "Steps: 9000"
        meta_keys.remove('Performance')
    if 'Guidance Scale' in metadata:
        text += f", CFG scale: {metadata['Guidance Scale']}"
        meta_keys.remove('Guidance Scale')
    if 'Sampler' in metadata:
        if metadata['Sampler'] == 'dpmpp_2m_sde_gpu':
            text += f', Sampler: DPM++ 2M SDE'
        else:
            text += f", Sampler: {metadata['Sampler']}"
        meta_keys.remove('Sampler')
    if 'Base Model' in metadata:
        text += f", Model: {metadata['Base Model']}"
        model_hash = get_model_hash(metadata['Base Model'])
        text += f', Model hash: {model_hash}'
        meta_keys.remove('Base Model')
    for item in meta_keys:
        text += f", {item}: {metadata[item]}"
        if 'lora' in item.casefold():
            pos_find = metadata[item].find('.safetensors')
            if pos_find > 0:
                lora_name = metadata[item][:pos_find+12]
                # could have subdirectory as part of the string, which the get_model_hash isn't expecting, so just stripping it out for now.
                prefix_find = lora_name.find("\\")
                if prefix_find != -1:
                    lora_name = lora_name[prefix_find+1:]
                lora_hash = get_model_hash(lora_name,'lora')
                resource_hashes['lora:'+lora_name] = lora_hash
    if resource_hashes != {}:
        text += f", Hashes: {json.dumps(resource_hashes)}"
    return text

def build_text(metadata):
    # Stupid fix
    metadata2 = []
    for item in metadata:
        if item[:2] == ', ':
            item = item[2:]
        if item[-1] == ':':
            item = item[:-1]
        metadata2.append(item)
    metadata = metadata2

    text = ''
    data_length = len(metadata)-1
    hashes = {}
    
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
        if val not in HEADINGS:
            continue
        
        if metadata[index+1] in HEADINGS:
            continue
        else:
            match val:
                case 'Guidance Scale':
                    text += f', CFG scale: {metadata[index+1]}'
                case 'Base Model':
                    text += f', Model: {metadata[index+1]}'
                    model_hash = get_model_hash(metadata[index+1])
                    text += f', Model hash: {model_hash}'
                case 'Sampler':
                    if metadata[index+1] == 'dpmpp_2m_sde_gpu':
                        text += f', Sampler: DPM++ 2M SDE'
                    else:
                        text += f', {val}: {metadata[index+1]}'
                case _:
                    text += f', {val}: {metadata[index+1]}'
                    if 'lora' in val.casefold():
                        print(val)
                        # put in hash calculate here
    return text

def process_directories():
    # get list of directories
    sub_dirs = scandir(DIRECTORY)
    # loop through directories
    for dir in sub_dirs:
        #if dir != "C:\\AI_ART\StabilityMatrix\\Data\\Images\\Fooocus\\2023-12-29":
        #    continue
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
                metadata = parse_button(div)

                # strip html out -- output is a list in ['key:', 'value', 'key:', 'value'] format
                data = strip_html(div)

                if metadata == None:
                    # latest log.html has nested divs, just skipping the empty one.
                    if len(data) == 1:
                        continue

                    # build out A1111 style string from data
                    text_meta = build_text(data)
                    #print(f'Text metadata: {text_meta}')
                else: # json button metadata
                    text_meta = build_text_json(metadata)

                # get image name from first field value
                image_file = dir + '\\' + data[0].strip()
            
                #check if file exists
                check_file  = os.path.isfile(image_file)
                if check_file == True:
                    update_image(image_file, text_meta)
                    check_image(image_file)
                else:
                    continue
                #break

def process_file(filepath):
    print(f'Processing {filepath}')
    # log.html better be in the same directory as the file
    dir_file = filepath.rfind('\\')
    if dir_file > 0:
        filename = filepath[dir_file+1:]
        log_file = filepath[:dir_file] + '\log.html'

        try:
            with open(log_file) as f:
                soup = BeautifulSoup(f, 'html.parser')
        except:
            print(f'No log file named: {log_file}')
            return None
        # get a list of all divs in the html log file
        divs = soup.findAll("div")
        for div in divs:
            data = strip_html(div)
            if data[0] == filename:
                metadata = {}
                metadata = parse_button(div)
                text_meta = build_text_json(metadata)
                update_image(filepath, text_meta)
                #check_image(filepath)
                break
        print(f'File updated!')
    else:
        return None

def main():
    if PROCESS_MODE == 'DIR':
        process_directories()
    elif PROCESS_MODE == 'FILE':
        process_file(PROCESS_FILE)

if __name__ == "__main__":
    main()
