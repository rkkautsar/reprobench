import requests
from reprobench.task_sources.doi.base import BaseDOIHandler


class ZenodoHandler(BaseDOIHandler):
    doi_prefix = "10.5281/zenodo."
    api_url = "https://zenodo.org/api"

    @classmethod
    def is_compatible(cls, doi):
        return doi.startswith(cls.doi_prefix)

    @classmethod
    def get_urls(cls, doi):
        record_id = doi[len(cls.doi_prefix) :]  # remove doi_prefix
        url = "{}/records/{}".format(cls.api_url, record_id)
        record = requests.get(url).json()

        return [file["links"]["self"] for file in record["files"]]


class ZenodoSandboxHandler(ZenodoHandler):
    doi_prefix = "10.5072/zenodo."
    api_url = "https://sandbox.zenodo.org/api"
