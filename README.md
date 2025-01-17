# SRS Worms
Package for processing and analysing multi-channel SRS worm images.

## Requirements
TBD.

## Data folder structure
There should be invididual experiment folders. For simplicity, it is recommended that all experiment folders are managed under the same project folder:

```
project_folder
    ├── experiment_1
    ├── experiment_2
    ...
```

Each experiment folder should look like this:

```
experiment_folder
    ├── calibration_fnorm.tif
    ├── image_subfolder_1
    |   ├── worm_image_with_desc_1.tif
    |   ├── worm_image_with_desc_2.tif
    |   ...
    ├── image_subfolder_2
    ...
```

The files include:
- `calibration_fnorm.tif`: the calibration image taken for field normalisation
- `worm_image_with_desc_1.tif`: the worm image with a description of the worm (e.g. treatment, timepoint, imaging parameters, etc.). For example, it can be
```
AD01_vit1mCherry_vit2GFP_300gain_10pbf_Zoom1_20240617_plate1_worm1_1x7.tif
```

## Usage
TBD.