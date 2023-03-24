# pytorch dataset for loading digitised specimens from RBG, Kew
import os
import pandas as pd

from PIL import Image
from torchvision.datasets.vision import VisionDataset

from typing import Union, List, Optional, Callable, Tuple, Any

TARGET_TYPES = ["family", "genus", "species", "name"]

def _verify_type(value: str, valid_values: Optional[List[str]]=None) -> str:
    if valid_values is None:
        return value
    
    if value not in valid_values:
        raise ValueError(f"Unknown target type '{value}', should be one of {{{valid_values}}}")
        
    return value

class KewSpecimenDataset(VisionDataset):
    def __init__(
        self, 
        root: str, 
        target_type: Union[List[str], str] = "name",
        transform: Optional[Callable] = None, 
        target_transform: Optional[Callable] = None,
        include_unknown: Optional[bool] = False
    ) -> None:
        super().__init__(root, transform=transform, target_transform=target_transform)
        os.makedirs(root, exist_ok=True)
            
        if not self._check_exists():
            raise RuntimeError(f"Dataset not found at location: {self.root}")
            
        if not isinstance(target_type, list):
            target_type = [target_type]
            
        self.target_type = [_verify_type(t, TARGET_TYPES) for t in target_type]

        self._load_meta(include_unknown)
    
    def _load_meta(self, include_unknown: Optional[bool] = False) -> None:
        metadata = (
            pd.read_csv(os.path.join(self.root, "metadata.csv"))
              .rename(columns={"FullName": "name"})
              .loc[:, ["imgId", "CatalogueNumber", "Kewid", "family", "genus", "species", "name"]]
              .fillna("Unknown")
        )

        if not include_unknown:
            metadata = metadata.loc[~(metadata[self.target_type] == "Unknown").any(axis=1)]

        metadata = metadata.sort_values(by=TARGET_TYPES)

        # dictionary mapping ipni id (Kewid) to taxonomic info
        self.categories_map = (
            metadata.loc[:, ["Kewid", *TARGET_TYPES]]
                    .drop_duplicates(subset="Kewid")
                    .set_index("Kewid")
                    .to_dict(orient="index")
        )

        # image id for path to image, barcode to keep link to specimen, ipni id for category info
        self.index: List[Tuple[int, str, str]] = []
        for img_id, barcode, ipni_id in metadata[["imgId", "CatalogueNumber", "Kewid"]].values:
            if os.path.exists(os.path.join(self.root, "images", f"{img_id}.jpg")):
                self.index.append((
                    f"{img_id}.jpg", 
                    barcode,
                    ipni_id
                ))

        # numerical values for categories in each target type
        self.categories_index = {k: {} for k in TARGET_TYPES}
        for target_type in TARGET_TYPES:
            for ipni_id, item in self.categories_map.items():
                if item[target_type] not in self.categories_index[target_type]:
                    self.categories_index[target_type][item[target_type]] = len(self.categories_index[target_type])

    def __getitem__(self, index: int) -> Tuple[Any, Any]:
        fname, barcode, ipni_id = self.index[index]
        img = Image.open(os.path.join(self.root, "images", fname))

        target: Any = []
        for t in self.target_type:
            cat_name = self.categories_map[ipni_id][t]
            target.append(self.categories_index[t][cat_name])

        target = tuple(target) if len(target) > 1 else target[0]

        if self.transform is not None:
            img = self.transform(img)

        if self.target_transform is not None:
            target = self.target_transform(target)

        return img, target

    def __len__(self) -> int:
        return len(self.index)

    def category_name(self, category_type: str, category_id: int) -> str:
        category_type = _verify_type(category_type)

        for name, idx in self.categories_index[category_type].items():
            if idx == category_id:
                return name
        
        raise ValueError(f"Invalid category ID {category_id} for {category_type}")

    def _check_exists(self) -> bool:
        img_dir = os.path.join(self.root, "images")
        return os.path.exists(img_dir) and len(img_dir) > 0
