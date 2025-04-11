import os
import random
from PIL import Image
from pathlib import Path
from rembg import remove

def random_color():
    return tuple(random.randint(0, 255) for _ in range(3))

def crop_to_content(img):
    bbox = img.getbbox()
    if bbox:
        return img.crop(bbox)
    return img

def create_background(bg_mode, size, bg_images_dir=None):
    if bg_mode == 'color':
        return Image.new('RGB', size, random_color())
    elif bg_mode == 'image' and bg_images_dir:
        bg_path = random.choice(list(Path(bg_images_dir).glob("*")))
        bg = Image.open(bg_path).convert('RGB')
        return bg.resize(size)
    else:
        raise ValueError("Invalid background mode or background directory not provided.")

def pad_with_background(fruit_img, padding_ratio, bg_mode, bg_images_dir=None):
    w, h = fruit_img.size
    pad_w = int(w * padding_ratio)
    pad_h = int(h * padding_ratio)
    new_size = (w + 2 * pad_w, h + 2 * pad_h)

    bg = create_background(bg_mode, new_size, bg_images_dir)
    bg.paste(fruit_img, (pad_w, pad_h), fruit_img)
    return bg

def process_images(input_dir, output_dir, padding_range=(0.2, 0.4), bg_modes=['color', 'image'], bg_images_dir=None):
    input_paths = list(Path(input_dir).rglob("*.[jp][pn]g"))

    for img_path in input_paths:
        try:
            img = Image.open(img_path).convert("RGBA")
            fruit_nobg = remove(img)
            fruit_nobg = crop_to_content(fruit_nobg)
            bg_mode = random.choice(bg_modes)
            padding_ratio = random.uniform(*padding_range)
            new_img = pad_with_background(fruit_nobg, padding_ratio, bg_mode, bg_images_dir)

            relative_path = img_path.relative_to(input_dir).with_suffix('')
            save_subdir = Path(output_dir) / relative_path.parent
            save_subdir.mkdir(parents=True, exist_ok=True)
            save_path = save_subdir / f"{img_path.stem}_padded.jpg"
            new_img = resize_image_max_size(new_img, max_size=512)
            new_img.save(save_path)
        except Exception as e:
            print(f"❌ Failed to process {img_path.name}: {e}")

def resize_image_max_size(img, max_size=512):
    w, h = img.size
    if max(w, h) <= max_size:
        return img
    scale = max_size / max(w, h)
    new_size = (int(w * scale), int(h * scale))
    return img.resize(new_size, resample=Image.LANCZOS)


input_directory = "./dataset"
output_directory = "./fruit_padded1"
padding_range = (0.15, 0.4)
background_modes = ['color', 'image']
background_images_dir = "./bg_pool"

process_images(input_directory, output_directory, padding_range, background_modes, background_images_dir)
