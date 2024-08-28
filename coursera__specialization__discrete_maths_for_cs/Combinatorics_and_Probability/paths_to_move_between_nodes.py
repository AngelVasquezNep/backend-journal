"""
There is a three like this

      a ---> d ---> t
     / \      ^   / ^
    /   \     | /   |
s -    c ---->/     |
    \  |            |
     \ v            |
      b ---> e -----|

Connections:
    - s -> a
    - s -> b
    - a -> c
    - a -> d
    - b -> c
    - b -> e
    - c -> d
    - c -> t
    - d -> t
    - e -> t

How many ways are there to go from s to t?
"""

from typing import TypeVar


T = TypeVar('T')


class Tree:
    def __init__(self):
        self.nodes = []

    def queue(self, node: 'Node'):
        self.nodes.append(node)

    def dequee(self):
        if self.nodes:
            return self.nodes.pop(0)


class Node:
    def __init__(self, value: T):
        self.visited = 0
        self.value = value
        self.children: list['Node'] = list()

    def __str__(self):
        return f'node={self.value} | visited={self.visited}'

    def add(self, node: 'Node') -> 'Node':
        self.children.append(node)
        return self

    def visit(self):
        self.visited += 1


s = Node('s')
a = Node('a')
b = Node('b')
c = Node('c')
d = Node('d')
e = Node('e')
t = Node('t')

s.add(a)
s.add(b)
a.add(c)
a.add(d)
b.add(c)
b.add(e)
c.add(d)
c.add(t)
d.add(t)
e.add(t)

if __name__ == '__main__':
    tree = Tree()
    tree.queue(s)

    while node := tree.dequee():
        node.visit()
        print('Visiting', node)
        for child in node.children:
            print(f'Adding', child)
            tree.queue(child)

    print(s)
    print(a)
    print(b)
    print(c)
    print(d)
    print(e)
    print(t)

