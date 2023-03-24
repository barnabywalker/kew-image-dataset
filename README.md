# Utilities for working with Kew herbarium specimen images

This repository houses some useful scripts for dealing with Kew's herbarium specimen images.

## Using this code

To use this code, you need to download or clone this repository. 

To clone this repository from the command line, run:
```
git clone https://github.com/barnabywalker/kew-image-dataset.git
```

You should then be able to run scripts from inside the repository directory.

Some packages you might need to install are:
- `requests`
- `pillow`
- `tqdm`
- `numpy`
- `pandas`
- `pytorch`

Alternatively, you can use the `environment.yml` file to create a conda environment with these packages installed:
```
conda env create -f environment.yml
```

## Downloading images

To download the images, you'll need a CSV file with the taxonomic information and download URL for all imaged Kew specimens, as well as the associated image URL.

### Parameters
The script has the following parameters:
- `--save_dir`: the path to a directory to download images into.
- `--meta_path`: the path to the CSV file with taxonomic information and download URLs.
- `--check-quality`: a flag to check for broken images after download.

### Outputs
The script has the following outputs:
- all specimen image files downloaded to a folder called `images`.
- a file called `undownloaded-images.txt`, which stores the URLs of images that could not be downloaded.
- a file called `bad-images.txt`, which stores the file name of broken images (only if the `--check-quality` flag is used).
- a file called `metadata.csv`, with the metadata for each specimen image that has a valid name and taxonomic ID.

### Metadata
The metadata has the following structure:

| Column | Description |
| --- | --- |
| imgID | A unique identifier for each image. |
| CatalogueNumber | A unique identifier for each specimen, the barcode that is on the physical specimen. **Some specimens may have multiple images.** |
| Kewid | A unique identifier for a taxon, the identifier used for each taxon name in Kew's [Plants of the World Online](https://powo.science.kew.org/). **Many taxa will have more than one specimens.** |
| FullName | The full taxonomic name associated with the specimen. |
| family | The taxonomic family of the specimen. |
| genus | The genus of the specimen, extracted from the full name. | 
| species | The species name of the specimen, extracted from the full name. |
| ISOAlpha2 | The [two-letter ISO code](https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2) of the country the specimen was collected in. |

The metadata only includes information for specimens with complete information for the `FullName`, `family`, and `Kewid` columns. Where a specimen has not been identified to genus or species, these columns are filled in as `"Unknown"`.

### Running the script
The script can be run from the command line interface.

For example:
```
python download-kew-images.py --save_dir=kew-images --meta_path=kew-image-barcodes.csv --check-quality
```

Will download images into the `kew-images` folder using information from the `kew-image-barcodes.csv` file and will check the images load okay afer downloading.

## Using the images as a pytorch `Dataset`

The images can be loaded into python, for use by pytorch, with the `KewSpecimenDataset` object.

For example:
```
from torchvision import transforms
from datasets import KewSpecimenDataset

root = "kew-images"
tfms = transforms.Compose([
    transforms.Resize(256),
    transforms.ToTensor()
])

ds = KewSpecimenDataset(root, transform=tfms, target_type="species")
```

This has created a `Dataset` that will yeild a specimen image (as a `Tensor`) and the class number of the associated species. 
```
for img, class_id in ds:
    # do something
    ...
```

The class number is the necessary target for a classification but we can regain the name of the class (in this case species) by:
```
species_name = ds.category_name("species", class_id)
```

We can change the `target_type` to any combination of `['family', 'genus', 'species', 'name']`.
For example:
```
ds = KewSpecimenDataset(root, transform=tfms, target_type=["family", "genus", "species"])
```
will yield the family, genus, and species class indices, which might be useful for something like a hierarchical loss.

### Unidentified specimens

By default, specimen images that are not identified for all the specified targets will not be included in the dataset. Using the `include_unknown` argument will include unidentified specimens with the class "Unknown". For example:
```
ds = KewSpecimenDataset(root, transform=tfms, target_type=["family", "genus", "species"], include_unknown=True)
```
Will include specimens that have only been identified genus or family with the genus and/or species as "Unknown".

### Taxonomic information
The full taxonomic information for each taxon name in the dataset is included as a dictionary of dictionaries in the `categories_map` property:
```
ds.categories_map
> {
    "Kewid": {
        "family": FAMILY, 
        "genus": GENUS, 
        "species": SPECIES, 
        "name": NAME}, 
    ...
  }
```

The class indices associated with each family, genus, species, or name are included as a dictionary of dictionaries in the `categories_index` property:
```
ds.categories_map
> {
    "family": {
        FAMILY1: 0,
        FAMILY2: 1,
        ...
    },
    "genus": {
        GENUS1: 0,
        GENUS2: 1,
        ...
    },
    "species": {
        SPECIES1: 0,
        SPECIES2: 1,
        ...
    },
    "name": {
        NAME1: 0,
        NAME2: 1,
        ...
    }
  }
```

The dataset index is a list of tuples with each image file name, catalogue number, and kew id:
```
ds.index
> [
    (FNAME1, CATALOGUENUMBER1, KEWID1),
    ...
]
```

## Issues/improvements

Please [submit an issue](https://github.com/barnabywalker/kew-image-dataset/issues/new) if you have an difficulties using the code in this repository, or you have any suggestions for improvement.