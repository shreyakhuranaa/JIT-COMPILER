from flask import Flask, request, jsonify, render_template
from core.interpreter import parse_code, eval_program

app = Flask(__name__)

def ast_to_tree_string(ast, indent=0):
    spacing = "  " * indent
    if isinstance(ast, dict):
        s = ""
        for k, v in ast.items():
            s += f"{spacing}{k}:\n"
            s += ast_to_tree_string(v, indent + 1)
        return s
    elif isinstance(ast, list):
        s = ""
        for i, item in enumerate(ast):
            s += f"{spacing}- item {i}:\n"
            s += ast_to_tree_string(item, indent + 1)
        return s
    else:
        return f"{spacing}{ast}\n"

@app.route('/run', methods=['POST'])
def run():
    data = request.json
    code = data.get("code", "")
    try:
        ast = parse_code(code)
        output, hot_ops = eval_program(ast)

        # Ensure output is always a list
        if isinstance(output, str):
            output = [output]

        tree_str = ast_to_tree_string(ast)
        return jsonify({
            "output": output,
            "ast_tree": tree_str,
            "hot_ops": hot_ops
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)