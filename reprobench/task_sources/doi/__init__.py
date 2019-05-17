from reprobench.task_sources.url import UrlSource
from reprobench.task_sources.doi.zenodo import ZenodoHandler, ZenodoSandboxHandler


class DOISource(UrlSource):
    TYPE = "doi"
    handlers = [ZenodoHandler, ZenodoSandboxHandler]

    def __init__(self, doi, **kwargs):
        super().__init__(**kwargs)
        self.doi = doi

        for handler in self.handlers:
            if handler.is_compatible(self.doi):
                self.urls = handler.get_urls(self.doi)
                break
        else:
            raise NotImplementedError(f"No handler for doi: {doi}")

