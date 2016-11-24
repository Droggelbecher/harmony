
class FileState:

    # TODO: automatically normalize path. Either on string level or
    # ask WorkingDirectory to do it when creating these

    def __init__(self, path = None, digest = None, size = None, mtime = None,
                 clock = {}):
        self.path = path
        self.digest = digest
        self.size = size
        self.mtime = mtime
        self.clock = clock

    def contents_different(self, other):
        return self.size != other.size or self.digest != other.digest

    def compare_clock(self, other):
        # TODO

        keys = set(self.clock.keys()).union(other.clock.keys())

        sign = 0
        for k in keys:
            new_sign = cmp(self.clock.get(k, 0), other.clock.get(k, 0))
            if sign == 0:
                sign = new_sign
            if new_sign == -sign:
                return None
        return sign


    @classmethod
    def get_heads(self, states):
        """
        Return all "maximal" entries (acc. to their vector clock),
        that is all the entries that are not cause for any others
        """
        unseen = set(states)
        candidates = set(states)

        while unseen:
            entry = unseen.pop()
            # Now remove all entries in s that are "lower" than entry
            to_remove = set(e for e in candidates if e.compare_clock(entry) < 0)
            candidates -= to_remove
            unseen -= to_remove
        return candidates



