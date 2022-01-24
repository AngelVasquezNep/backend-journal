
class EvenNumbers:
    """Clase que implementa un iterador de todos los números pares,
    o los números pares hasta un máximo
    """

    def __init__(self, max=None):
        self.max = max

    # Convertir un iterable en un iterador
    # iter() manda a llamar a este método
    def __iter__(self):
        self.num = 0  # Primer número par
        # * Convertir un iterable en un iterador
        return self

    # next() manda a llamar este método
    def __next__(self):
        if not self.max or self.num <= self.max:
            result = self.num
            self.num += 2
            return result
        else:
            raise StopIteration


even = EvenNumbers(20)

for e in even:
  print(e)