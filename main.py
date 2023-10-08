from lottery import Lottery

superenalotto = Lottery(max_numbers=90, max_extra=90,
                        len_numbers=6, len_extra=1)

superenalotto(backend='choice', many=1_000_000).draw

print(f'\nrepeated {superenalotto._stop} times')
