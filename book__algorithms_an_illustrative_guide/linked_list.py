from collections.abc import Callable


class LinkedList:
    def __init__(self):
        self.head = None
        self.tail = None

    def __iter__(self):
        self.current = self.head
        return self

    def __next__(self):
        if self.current is None:
            raise StopIteration

        value = self.current.value
        self.current = self.current.tail
        return value

    def add(self, value) -> 'LinkedList':
        new_node = Node(value=value)
        last_node = new_node
        if self.tail is not None:
            last_node = self.tail
            last_node.tail = new_node

        if self.head is None:
            self.head = last_node

        self.tail = new_node

        return self

    def _sort(self, current_node):
        if current_node is None or current_node.tail is None:
            return current_node

        next_node = current_node.tail
        if current_node.value > next_node.value:
            current_node.tail = next_node.tail
            next_node.tail = current_node
            current_node = next_node
            current_node.tail = self._sort(current_node.tail)
        return current_node

    def sort(self) -> 'LinkedList':
        self.head = self._sort(self.head)
        return self


class Node:
    def __init__(self, value=None):
        self.value = value
        self.tail = None


linked_list = LinkedList()

linked_list.add(10)
linked_list.add(2)
linked_list.add(3)

for item in linked_list:
    print(item)
print('---')


linked_list.sort()

for item in linked_list:
    print(item)
