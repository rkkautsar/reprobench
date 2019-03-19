class BaseDOIHandler(object):
    @classmethod
    def is_compatible(cls, doi):
        return False

    @classmethod
    def get_urls(cls, doi):
        return []
