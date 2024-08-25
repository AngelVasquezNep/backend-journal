class Stack:
    def __init__(self) -> None:
        self.head = None

    def __iter__(self):
        self.current = self.head
        return self

    def __next__(self):
        if self.current is None:
            raise StopIteration

        new_current = self.current
        self.current = new_current.next
        return new_current.value

    def push(self, value) -> 'Stack':
        node = Node(value=value)
        node.next = self.head
        self.head = node
        return self

    def pop(self) -> 'Node':
        assert self.head is not None, 'Out of range'

        lastest_node = self.head
        self.head = lastest_node.next
        lastest_node.next = None
        return lastest_node


class Node:
    def __init__(self, value) -> None:
        self.value = value
        self.next = None


stack = Stack()
stack.push(1)
stack.push(2)
stack.push(3)

for item in stack:
    print(item)

print('---')
stack.pop()
stack.pop()
for item in stack:
    print(item)
stack.pop()

print(stack)
