from pathlib import Path
from zipfile import ZipFile
from loguru import logger
from reprobench.utils import download_file

from .local import LocalSource


class UrlSource(LocalSource):
    def __init__(
        self,
        url,
        path,
        patterns="",
        skip_existing=True,
        extract_archives=True,
        **kwargs,
    ):
        super().__init__(path, patterns=patterns)
        self.url = url
        self.extract_archives = extract_archives
        self.skip_existing = skip_existing

    def extract_zip(self, path):
        extract_path = Path(path) / ".." / path.stem
        if not extract_path.is_dir():
            with ZipFile(path) as zip:
                zip.extractall(extract_path)

    def setup(self):
        path = Path(self.path)
        path.mkdir(parents=True, exist_ok=True)
        filename = self.url.split("/")[-1].split("?")[0]
        path = path / filename

        if not path.exists() or not self.skip_existing:
            logger.debug(f"Downloading {self.url} to {path}")
            download_file(self.url, path)
        else:
            logger.debug(f"Skipping already download file {path}")

        if self.extract_archives and path.suffix == ".zip":
            self.extract_zip(path)

        return super().setup()
