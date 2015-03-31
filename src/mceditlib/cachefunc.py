# From http://code.activestate.com/recipes/498245/
import collections
import functools
from itertools import ifilterfalse
from heapq import nsmallest
from operator import itemgetter


class Counter(dict):
    'Mapping where default values are zero'

    def __missing__(self, key):
        return 0


def lru_cache(maxsize=100):
    def decorator(user_function):
        return lru_cache_object(user_function, maxsize)
    return decorator

class lru_cache_object(object):
    """
    Least-recently-used cache.

    Arguments to the cached function must be hashable.
    Cache performance statistics stored in f.hits and f.misses.
    Clear the cache with f.clear().
    http://en.wikipedia.org/wiki/Cache_algorithms#Least_Recently_Used

    Amended to accept two callbacks: should_decache and will_decache.

    should_decache is called with the result that is about to decache and should return True or False.
    will_decache is called with the result that is about to decache.

    Also provides an explicit decache function. Call it to decache a result with the given key.
    Calling decache will not call either callback.

    Also acts as an iterator over cached results, and can be checked if a key is in the cache with `key in cache`

    """

    def __init__(self, user_function, maxsize=100):

        self.maxqueue = maxsize * 10
        self.maxsize = maxsize
        self.cache = {}                   # mapping of args to results
        self.queue = collections.deque()  # order that keys have been used
        self.refcount = Counter()         # times each key is in the queue
        self.sentinel = object()          # marker for looping around the queue
        self.kwd_mark = object()          # separate positional and keyword args
        self.user_function = user_function

        self.hits = self.misses = 0

    def setCacheLimit(self, size):
        self.maxsize = size
        self.maxqueue = size * 10

    def __call__(self, *args, **kwds):
        # cache key records both positional and keyword args
        key = args
        if kwds:
            key += (self.kwd_mark,) + tuple(sorted(kwds.items()))

        # record recent use of this key
        self.queue.append(key)
        self.refcount[key] += 1

        # get cache entry or compute if not found
        try:
            result = self.cache[key]
            self.hits += 1
        except KeyError:
            result = self.user_function(*args, **kwds)
            self.cache[key] = result
            self.misses += 1

            # purge least recently used cache entry
            if len(self.cache) > self.maxsize:
                stale_key = self.queue.popleft()
                self.refcount[stale_key] -= 1
                cannot_decache = []
                while len(self.queue):
                    while self.refcount[stale_key]:
                        stale_key = self.queue.popleft()
                        self.refcount[stale_key] -= 1

                    if self.should_decache is None or self.should_decache(self.cache[stale_key]) is True:
                        if self.will_decache is not None:
                            self.will_decache(self.cache[stale_key])

                        del self.cache[stale_key], self.refcount[stale_key]
                        break
                    else:
                        self.refcount[stale_key] += 1
                        cannot_decache.append(stale_key)

                self.queue.extendleft(cannot_decache)

        # periodically compact the queue by eliminating duplicate keys
        # while preserving order of most recent access
        if len(self.queue) > self.maxqueue:
            self.refcount.clear()
            self.queue.appendleft(self.sentinel)
            for key in ifilterfalse(self.refcount.__contains__,
                                    iter(self.queue.pop, self.sentinel)):
                self.queue.appendleft(key)
                self.refcount[key] = 1

        return result

    def clear(self):
        self.cache.clear()
        self.queue.clear()
        self.refcount.clear()
        self.hits = self.misses = 0

    def decache(self, *args, **kwds):
        key = args
        if kwds:
            key += (self.kwd_mark,) + tuple(sorted(kwds.items()))
        if key not in self.cache:
            return
        del self.cache[key], self.refcount[key]

        # Remove all occurences of key from queue
        try:
            while True:
                self.queue.remove(key)
        except ValueError:  # x not in deque
            pass

    def store(self, result, *args, **kwds):
        key = args
        if kwds:
            key += (self.kwd_mark,) + tuple(sorted(kwds.items()))
        self.cache[key] = result
        self.refcount[key] += 1
        self.queue.append(key)

    def __contains__(self, key, **kwds):
        if kwds:
            key += (self.kwd_mark,) + tuple(sorted(kwds.items()))
        return key in self.cache

    def __iter__(self):
        return self.cache.itervalues()

    should_decache = None
    will_decache = None

def lfu_cache(maxsize=100):
    def decorator(user_function):
        return lfu_cache_object(user_function, maxsize)
    return decorator

class lfu_cache_object(object):
    """Least-frequenty-used cache.

    Arguments to the cached function must be hashable.
    Cache performance statistics stored in f.hits and f.misses.
    Clear the cache with f.clear().
    http://en.wikipedia.org/wiki/Least_Frequently_Used

    Accepts two callbacks: should_decache and will_decache

    should_decache is called with the result that is about to decache and should return True or False
    will_decache is called with the result that is about to decache.

    Also provides an explicit decache function. Call it to decache a result with the given key.
    Calling decache will not call either callback.

    Also acts as an iterator over cached results, and can be checked if a key is in the cache with `key in cache`

    """

    def __init__(self, user_function, maxsize=100):
        self.cache = {}                      # mapping of args to results
        self.use_count = Counter()           # times each key has been accessed
        self.kwd_mark = object()             # separate positional and keyword args
        self.hits = self.misses = 0
        self.user_function = user_function
        self.maxsize = maxsize

    def __call__(self, *args, **kwds):
        key = args
        if kwds:
            key += (self.kwd_mark,) + tuple(sorted(kwds.items()))
        self.use_count[key] += 1

        # get cache entry or compute if not found
        try:
            result = self.cache[key]
            self.hits += 1
        except KeyError:
            result = self.user_function(*args, **kwds)
            self.cache[key] = result
            self.misses += 1

            # purge bottom 10% of least frequently used cache entries
            if len(self.cache) > self.maxsize:
                for key, _ in nsmallest(self.maxsize // 10,
                                        self.use_count.iteritems(),
                                        key=itemgetter(1)):

                    if self.should_decache is None or self.should_decache(self.cache[key]) is True:
                        if self.will_decache is not None:
                            self.will_decache(self.cache[key])
                        del self.cache[key], self.use_count[key]

        return result

    def clear(self):
        self.cache.clear()
        self.use_count.clear()
        self.hits = self.misses = 0

    def decache(self, *args, **kwds):
        key = args
        if kwds:
            key += (self.kwd_mark,) + tuple(sorted(kwds.items()))
        if key not in self.cache:
            return
        del self.cache[key], self.use_count[key]

    def __contains__(self, *args, **kwds):
        key = args
        if kwds:
            key += (self.kwd_mark,) + tuple(sorted(kwds.items()))
        return key in self.cache

    def __iter__(self):
        return self.cache.itervalues()

    should_decache = None
    will_decache = None


if __name__ == '__main__':

    @lru_cache(maxsize=20)
    def f_lru(x, y):
        return 3 * x + y

    domain = range(5)
    from random import choice
    for i in range(1000):
        r = f_lru(choice(domain), choice(domain))

    print(f_lru.hits, f_lru.misses)

    @lfu_cache(maxsize=20)
    def f_lfu(x, y):
        return 3 * x + y

    domain = range(5)
    from random import choice
    for i in range(1000):
        r = f_lfu(choice(domain), choice(domain))

    print(f_lfu.hits, f_lfu.misses)
