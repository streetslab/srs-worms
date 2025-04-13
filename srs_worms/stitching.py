from pathlib import Path
import subprocess
import shutil
import numpy as np
import pandas as pd
from skimage import img_as_ubyte
from skimage.exposure import rescale_intensity
from skimage.io import imread
from skimage.io import imsave
from skimage.filters import gaussian
import tifffile

def get_fnorm_multiplier(img, radius=50):
    img = gaussian(img, sigma=radius)
    return np.max(img) / img

def normalize_image(img, fnorm_multiplier):
    orig_dtype = img.dtype
    img = img * fnorm_multiplier
    img = img.astype(orig_dtype)
    return img

def hyperstack_srs(img, num_chn=2):
    z_total, y, x = img.shape
    z = z_total // num_chn
    # Reshape (z*c, y, x) -> (z, c, y, x)
    img_reshaped = img.reshape(z, num_chn, y, x)
    # Transpose (z, c, y, x) -> (c, z, y, x)
    img_transposed = img_reshaped.transpose(1, 0, 2, 3)
    return img_transposed

def save_tif_imagej(img, output_dir):
    tifffile.imwrite(
        output_dir,
        img,
        metadata={'axes': 'CYX'},
        imagej=True,
    )

def pro_sub_lip_stack(hyperstack, ratio=None, quantile=0.999):
    pro = hyperstack[0]
    lip = hyperstack[1]
    if ratio is None:
        ratio = np.quantile(pro, quantile) / np.quantile(lip, quantile)
    lip = lip * ratio
    pro_sub_lip = pro - lip
    pro_sub_lip[pro_sub_lip < 0] = 0
    lip = lip.astype(pro.dtype)
    pro_sub_lip = pro_sub_lip.astype(pro.dtype)
    # return pro, sub, lip as a hyperstack
    return np.stack((pro, lip, pro_sub_lip))

def scan_tiles(dir, skip=2, num_chn=2):
    files = list(dir.glob('*.tif'))
    start_ends = [(int(s[-2]), int(s[-1])) for s in [f.stem.split('_') for f in files]]
    img_stack = None
    for f, (start,end) in zip(files, start_ends):
        img = imread(f)
        if skip:
            img = img[skip:,...]
        z = img.shape[0]
        try:
            assert z == (end - start + 1) * num_chn
        except AssertionError:
            print(f'{f} has {z} slices, expected {(end - start + 1) * num_chn}')
            return
        if img_stack is None:
            img_stack = img
        else:
            img_stack = np.concatenate((img_stack, img), axis=0)
    return img_stack

def run_ijm(file, fiji_dir):
    subprocess.run([fiji_dir, '--headless', '-macro', file, '--mem=32000M'], check=True)

def create_jim(template_path,stc_dir,out_path,x,y):
    with open(template_path, 'r') as f:
        template = f.read()
        template = template.replace('GRID_X', str(x))
        template = template.replace('GRID_Y', str(y))
        template = template.replace('FILE_PATH', str(stc_dir))
    with open(out_path, 'w') as f:
        f.write(template)

def batch_rename(src_dir, dest_dir, pattern, prefix="chn", suffix=None):
    dest_dir.mkdir(exist_ok=True)
    for file in src_dir.glob(pattern):
        chn_num = int(file.name.split("_c")[-1])
        if not suffix:
            output_name = f"{prefix}_{chn_num:02d}.tif"
        else:
            output_name = f"{prefix}_{suffix[chn_num-1]}.tif"
        output_file = dest_dir / output_name
        file.rename(output_file)