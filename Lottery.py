from datetime import datetime
from random import SystemRandom

rnd = SystemRandom()


class Lottery:

    def __init__(self,
                 max_numbers=90,
                 max_extra=90,
                 len_numbers=6,
                 len_extra=1):
        self.max_numbers = max_numbers
        self.max_extra = max_extra
        self.len_numbers = len_numbers
        self.len_extra = len_extra

    @property
    def combo(self): return self._combo

    @property
    def extra(self): return self._extra

    @property
    def backend(self): return self._backend.__name__

    @property
    def many(self): return self._many

    @staticmethod
    def choice(_len, max):
        numbers = list(range(1, max+1))

        def extraction():
            sample = rnd.choice(numbers)
            numbers.remove(sample)
            return sample

        combo = (extraction() for _ in range(_len))

        return frozenset(combo)

    @staticmethod
    def sample(_len, max):
        numbers = tuple(range(1, max+1))
        combo = rnd.sample(numbers, k=_len)

        return frozenset(combo)

    @staticmethod
    def randint(_len, max):
        # create an iterator that calls draw() until it returns 0, but
        # since it is impossible to get 0 from draw(), it works as an
        # infinite generator
        def draw(): return rnd.randint(1, max)
        numbers = iter(draw, 0)

        combo = set()
        while len(combo) < _len:
            combo.add(next(numbers))

        return frozenset(combo)

    def manySamples(self):
        '''
        To add further randomness, this method simulates several extractions, 
        among 1 and <size> times, and picks one casually ... hopefully 
        the winning one :D
        '''

        size = self._many or 1
        self._stop = rnd.randint(1, size)

        for _ in range(self._stop):
            sample = self.extract()

        return sample  # type: ignore

    def extract(self):
        combo = self._backend(self.len_numbers, self.max_numbers)
        extra = self._backend(self.len_extra, self.max_extra) or None

        return combo, extra

    def __call__(self, backend='choice', many=None):
        self._many = many
        self._backend = eval(backend,
                             {'__builtins__': {}},
                             {'choice': self.choice,
                              'randint': self.randint,
                              'sample': self.sample})

        self._combo, self._extra = self.manySamples()

        return self

    @property
    def draw(self):
        now = datetime.now().strftime("%d/%m/%Y %H:%M")

        print('Estrazione del:', now, '\nNumeri Estratti:',
              *sorted(self._combo))  # type: ignore

        if self._extra is not None:
            print('Superstar:', *sorted(self._extra))  # type: ignore
