import pandas as pd
import numpy as np
import requests
import os

from argparse import ArgumentParser
from tqdm import tqdm
from PIL import Image


def load_metadata(path):
    return pd.read_csv(path).assign(imgId=lambda df: df.Digifolia.str.split(":").str[1])


def download_image(url, path):
    img = requests.get(url).content
    with open(path, "wb") as handler:
        handler.write(img)


def check_image(path):
    good = True
    try:
        img = Image.open(path)
        img.verify()
    except(IOError, SyntaxError) as e:
        good = False

    return good


def clean_metadata(metadata):
    return (
        metadata.loc[metadata.family.notnull() & metadata.FullName.notnull() & metadata.Kewid.notnull()]
                .loc[:, ["imgId", "CatalogueNumber", "Kewid", "FullName", "family", "ISOAlpha2"]]
                .drop_duplicates(subset=["imgId"])
                .assign(
                    genus=lambda df: df.FullName.str.split(" ").str[0],
                    species=lambda df: df.FullName.apply(lambda x: " ".join(x.split()[:2]))
                )
                .assign(
                    genus=lambda df: df.apply(lambda x: np.nan if x.genus == x.family else x.genus, axis=1),
                    species=lambda df: df.apply(lambda x: np.nan if x.species == x.family else x.species, axis=1)
                )
                .assign(
                    species=lambda df: df.apply(lambda x: np.nan if x.species == x.genus else x.species, axis=1)
                )
    )


def main():
    parser = ArgumentParser()

    parser.add_argument("--meta_path", type=str, default="./kew-image-barcodes.csv")
    parser.add_argument("--save_dir", type=str, default="./")
    parser.add_argument("--check-quality", dest="check", action="store_true")
    parser.set_defaults(check=False)

    args = parser.parse_args()

    if not os.path.exists(args.save_dir):
        os.makedirs(os.path.join(args.save_dir, "images"))

    metadata = load_metadata(args.meta_path)
    cleaned_metadata = clean_metadata(metadata)

    already_downloaded = [f.split(".")[0] for f in os.listdir(os.path.join(args.save_dir, "images"))]
    # use the digifolia id as a unique id - some specimens have more than one sheet imaged
    metadata = metadata.loc[~metadata.imgId.isin(already_downloaded)]

    print(f"Already downloaded {len(already_downloaded)} images, will download the remaining {metadata.shape[0]}")
    
    for img_id, url in tqdm(metadata[["imgId", "JpegUrl"]].values, desc="downloading images"):
        img_path = os.path.join(args.save_dir, "images", f"{img_id}.jpg")
        try:
            download_image(url, img_path)
        except:
            with open(os.path.join(args.save_dir, "undownloaded-images.txt"), "a+") as txtfile:
                txtfile.writelines([url])

    print(f"Downloaded all images")

    cleaned_metadata.to_csv(os.path.join(args.save_dir, "metadata.csv"))

    if args.check:
        # if a download is interupted an invalid image can be saved
        imgs = [f for f in os.listdir(args.save_dir) if f.endswith(".jpg")]
        bad_images = [img for img in tqdm(imgs, desc="checking images") if not check_image(os.path.join(args.save_dir, img))]
        with open(os.path.join(args.save_dir, "bad-images.txt"), "w") as txtfile:
            txtfile.writelines(bad_images)


if __name__ == "__main__":
    main()