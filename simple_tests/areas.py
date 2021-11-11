class Regtangulo:
    def __init__(self, base, altura):
        self.base = base
        self.altura = altura

    def area(self):
        return self.base * self.altura


class Cuadrado(Regtangulo):
    def __init__(self, lado):
        super().__init__(lado, lado)


if __name__ == "__main__":
    r = Regtangulo(10, 15)
    c = Cuadrado(10)

    print(r.area())
    print(c.area())