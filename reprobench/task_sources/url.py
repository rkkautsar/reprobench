from pathlib import Path
from zipfile import ZipFile
from loguru import logger
from reprobench.utils import download_file

from .local import LocalSource


class UrlSource(LocalSource):
    def __init__(
        self,
        urls=[],
        path=None,
        patterns="",
        skip_existing=True,
        extract_archives=True,
        **kwargs,
    ):
        super().__init__(path, patterns=patterns)
        self.urls = urls
        self.extract_archives = extract_archives
        self.skip_existing = skip_existing

    def extract_zip(self, path):
        extract_path = Path(path) / ".." / path.stem
        if not extract_path.is_dir():
            with ZipFile(path) as zip:
                zip.extractall(extract_path)

    def setup(self):
        root = Path(self.path)
        root.mkdir(parents=True, exist_ok=True)

        for url in self.urls:
            filename = url.split("/")[-1].split("?")[0]
            path = root / filename

            if not path.exists() or not self.skip_existing:
                logger.debug(f"Downloading {url} to {path}")
                download_file(url, path)
            else:
                logger.debug(f"Skipping already downloaded file {path}")

            if self.extract_archives and path.suffix == ".zip":
                self.extract_zip(path)

        return super().setup()
