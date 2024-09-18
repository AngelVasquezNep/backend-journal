"""
I'm playing with combinations and permutations
I build this mini site to see them


Run:
    flask --app simple_server run --host=0.0.0.0 --port 5001 --debug


Usage:
    - Permutations
        GET http://localhost:5001/permutations?total=4
    - Combinations
        GET http://localhost:5001/combinations?total=5&size=3
"""

from itertools import combinations, permutations
from flask import Flask, request


app = Flask(__name__)


def make_combinations(total: int, size: int) -> list[tuple]:
    return [numbers for numbers in combinations(range(total), size)]


def make_permutations(total: int) -> list[tuple]:
    return [numbers for numbers in permutations(range(total))]



@app.route("/")
def index():
    return """
    <h1>Hi</h1>
    <a href="/combinations">Combinations</a>
    <a href="/permutations">Permutations</a>
    """


@app.route("/combinations")
def try_combinations(): 
    total = int(request.args.get('total', 1))
    size = int(request.args.get('size', 1))
    template = ""

    box_styles = "width: 2rem; height: 2rem; padding: 0.5rem; border: 1px solid red;"
    active_styles = box_styles + "background-color: red;"

    for numbers in make_combinations(total, size):
        boxes = []
        for index in range(total):
            active = active_styles if index in numbers else box_styles
            boxes.append(f"<div style='{active}'>{index}</div>")
        template += '\n' + "<div style='display:flex; gap: 0.5rem; margin: 0 auto;'>" + '\n'.join(boxes) + "</div>"

    return f"""
    <div style="display: flex; flex-direction: column; justify-content: center; gap: 0.5rem;">
        {template}
    </div>
    """


@app.route("/permutations")
def try_permutations():
    total = int(request.args.get('total', 1))

    template = ""
    box_styles = "width: 2rem; height: 2rem; padding: 0.5rem; border: 1px solid red;"
    active_styles = box_styles + "background-color: red;"

    for numbers in make_permutations(total):
        boxes = []
        for number in numbers:
            boxes.append(f"<div style='{box_styles}'>{number}</div>")
        template += '\n' + "<div style='display:flex; gap: 0.5rem; margin: 0 auto;'>" + '\n'.join(boxes) + "</div>"
    return f"""
    <div style="display: flex; flex-direction: column; justify-content: center; gap: 0.5rem;">
        {template}
    </div>
    """
