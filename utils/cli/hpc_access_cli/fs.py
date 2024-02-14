"""Code for load file system resource management."""

from pathlib import Path
from typing import List

from hpc_access_cli.models import FsDirectory


class FsResourceManager:
    """Helper class to manage resources on file system.

    Effectively, it reads/writes the well-known folders and attributes.
    """

    def __init__(self, *, prefix: str = ""):
        self.path_tier1 = f"{prefix}/data/cephfs-1"
        self.path_tier2_mirrored = f"{prefix}/data/cephfs-2/mirrored"
        self.path_tier2_unmirrored = f"{prefix}/data/cephfs-2/unmirrored"

    def load_directories(self) -> List[FsDirectory]:
        """Load the directories and their sizes."""
        result = []
        for path_obj in Path(self.path_tier1).glob("*/*/*"):
            if path_obj.is_dir():
                result.append(FsDirectory.from_path(str(path_obj)))
        for path in (self.path_tier2_mirrored, self.path_tier2_unmirrored):
            for path_obj in Path(path).glob("*/*/*"):
                if path_obj.is_dir():
                    result.append(FsDirectory.from_path(str(path_obj)))
        result.sort(key=lambda x: x.path)
        return result
