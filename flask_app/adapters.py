from collections import defaultdict


class SortedDefaultDict(defaultdict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


    def sorted_items(self):
        """
        Return a list that yields sorted lists sorted by keys.
        """
        return [(key, self[key]) for key in sorted(self.keys())]
    

    def sorted_iteritems(self):
        """
        Return a generator that yields sorted lists sorted by keys.
        """
        for key in sorted(self.keys()):
            yield (key, sorted(self[key]))
