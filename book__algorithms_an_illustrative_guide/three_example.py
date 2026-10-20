THREE = """
                                         ROOT
                     ┌─────────────────────┴──────────────────────┐
                     E                                            T
          ┌──────────┴──────────┐                     ┌───────────┴──────────┐
          I                     A                     N                      M
    ┌─────┴─────┐         ┌─────┴─────┐         ┌─────┴─────┐          ┌─────┴─────┐
    S           U         R           W         D           K          G           O
┌───┴───┐   ┌───┴───┐ ┌───┴───┐   ┌───┴───┐ ┌───┴───┐   ┌───┴───┐  ┌───┴───┐   ┌───┴───┐
H       V   F       Ü L       Ä   P       J B       X   C       Y  Z       Q   Ö       Ş
"""

class Node:
    def __init__(self, value):
        self.value = value
        self.children: list["Node"] = []

    def __str__(self) -> str:
        return f'{self.value} | {len(self.children)} children'

    def __repr__(self):
        return self.value

    def add_children(self, node: "Node"):
        self.children.append(node)



class Queue:
    def __init__(self):
        self.nodes: list[Node] = []

    def enqueue(self, node: Node):
        self.nodes.append(node)

    def addFirst(self, node: Node):
        self.nodes.insert(0, node)

    def dequeue(self):
        if len(self.nodes) > 0:
            return self.nodes.pop(0)
        return None


def get_root():
    # Level 0
    root = Node("ROOT")

    # Level 1
    lE = Node("E")
    lT = Node("T")

    root.add_children(lE)
    root.add_children(lT)


    # Level 2
    lI = Node("I")
    lA = Node("A")

    lN = Node("N")
    lM = Node("M")

    lE.add_children(lI)
    lE.add_children(lA)

    lT.add_children(lN)
    lT.add_children(lM)


    # Level 3
    lS = Node("S")
    lU = Node("U")

    lR = Node("R")
    lW = Node("W")

    lD = Node("D")
    lK = Node("K")

    lG = Node("G")
    lO = Node("O")

    lI.add_children(lS)
    lI.add_children(lU)

    lA.add_children(lR)
    lA.add_children(lW)

    lN.add_children(lD)
    lN.add_children(lK)

    lM.add_children(lG)
    lM.add_children(lO)


    # Level 4 / Leaves
    lH = Node("H")
    lV = Node("V")

    lF = Node("F")
    lU_umlaut = Node("Ü")

    lL = Node("L")
    lA_umlaut = Node("Ä")

    lP = Node("P")
    lJ = Node("J")

    lB = Node("B")
    lX = Node("X")

    lC = Node("C")
    lY = Node("Y")

    lZ = Node("Z")
    lQ = Node("Q")

    lO_umlaut = Node("Ö")
    lS_cedilla = Node("Ş")


    # Connect leaves
    lS.add_children(lH)
    lS.add_children(lV)

    lU.add_children(lF)
    lU.add_children(lU_umlaut)

    lR.add_children(lL)
    lR.add_children(lA_umlaut)

    lW.add_children(lP)
    lW.add_children(lJ)

    lD.add_children(lB)
    lD.add_children(lX)

    lK.add_children(lC)
    lK.add_children(lY)

    lG.add_children(lZ)
    lG.add_children(lQ)

    lO.add_children(lO_umlaut)
    lO.add_children(lS_cedilla)

    return root