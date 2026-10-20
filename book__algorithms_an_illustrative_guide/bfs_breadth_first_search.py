"""
BFS: Goes by layers, from "left" to "right", one layer at a time

Difference between BFS and DFS is the q.enqueue vs q.addFirst
"""
from three_example import get_root, Node, Queue, THREE


def breadth_first_search(root: Node, target: str):
    q = Queue()
    q.enqueue(root)

    searched: list[Node] = []

    while neighbor := q.dequeue():
        if neighbor in searched:
            print('ALREADY CHECKED', neighbor)
            continue
        searched.append(neighbor)

        if neighbor.value == target:
            return (True, searched)

        for _neighbor in neighbor.children:
            q.enqueue(_neighbor)
    return (False, [])


if __name__ == "__main__":
    import sys
    # python dfs_depth_first_search.py <UPPER_CASE_LETTER>
    letter = sys.argv[1] if len(sys.argv) > 1 else "O"
    found, steps = breadth_first_search(get_root(), letter)

    print(THREE)
    print(steps)
