class Node:
    def __init__(self, value):
        self.value = value
        self.children = []

    def __str__(self) -> str:
        return f'{self.value} | {len(self.children)} children'


class Neighbor(Node):
    def add_neighbor(self, neighbor: Node):
        self.children.append(neighbor)


class Queue:
    def __init__(self):
        self.nodes: list[Node] = []

    def enqueue(self, node: Node):
        self.nodes.append(node)

    def dequeue(self):
        if len(self.nodes) > 0:
            return self.nodes.pop(0)
        return None


"""
        angel ------- moni ------- migue
        |                           |
        dani                       yami

"""

angel = Neighbor('Angel')
mom = Neighbor('Mom')
dani = Neighbor('Dani')
migue = Neighbor('Migue')
yami = Neighbor('Yami')


# migue.add_neighbor(yami)
# mom.add_neighbor(migue)

# angel.add_neighbor(mom)
# angel.add_neighbor(dani)

dani.add_neighbor(angel)
angel.add_neighbor(dani)


def breadth_first_search(target: str):
    q = Queue()
    q.enqueue(angel)

    searched: list[Neighbor] = []

    while neighbor := q.dequeue():
        if neighbor in searched:
            print('ALREADY CHECKED', neighbor)
            continue
        searched.append(neighbor)

        if neighbor.value == target:
            return True

        print(neighbor)

        for _neighbor in neighbor.children:
            q.enqueue(_neighbor)
    return False


print(breadth_first_search('Angel 2'))
