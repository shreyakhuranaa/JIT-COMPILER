from flask import Flask, request, jsonify, render_template
import json

app = Flask(__name__)

# Environment and hot operation tracking
env = {}
hot_usage = {}
HOT_THRESHOLD = 2

def reset_hot_usage():
    global hot_usage
    hot_usage = {}

def eval_expr(expr):
    if isinstance(expr, dict):
        t = expr.get("type")
        if t == "number":
            return expr["value"]
        elif t == "variable":
            name = expr["name"]
            return env.get(name, 0)
        elif t == "binary_op":
            op = expr["op"]
            left = eval_expr(expr["left"])
            right = eval_expr(expr["right"])

            key = f"{op}"
            hot_usage[key] = hot_usage.get(key, 0) + 1

            if op == "+": return left + right
            elif op == "-": return left - right
            elif op == "*": return left * right
            elif op == "/": return left // right if right != 0 else 0
        elif t == "array":
            return [eval_expr(item) for item in expr["items"]]
        elif t == "function_call":
            name = expr["name"]
            args = [eval_expr(arg) for arg in expr["args"]]
            if name == "sum": return sum(args)
            elif name == "max": return max(args)
    return 0

def parse_code(lines):
    program = []
    for line in lines:
        line = line.strip()
        if line.endswith(';'):
            line = line[:-1].strip()  # strip trailing semicolon

        if line.startswith("print "):
            var = line[6:].strip()
            if var.endswith(';'):
                var = var[:-1].strip()
            program.append({"type": "print", "expr": {"type": "variable", "name": var}})
        elif "=" in line:
            var, expr = line.split("=", 1)
            var = var.strip()
            expr = expr.strip()
            if expr.endswith(';'):
                expr = expr[:-1].strip()

            if expr.startswith("[") and expr.endswith("]"):
                items = expr[1:-1].split(",")
                items = [{"type": "number", "value": int(item.strip())} for item in items if item.strip().isdigit()]
                program.append({"type": "assign", "var": var, "expr": {"type": "array", "items": items}})
            elif any(op in expr for op in ["+", "-", "*", "/"]):
                for op in ["+", "-", "*", "/"]:
                    if op in expr:
                        left, right = expr.split(op)
                        def parse_val(v):
                            v = v.strip()
                            if v.endswith(';'):
                                v = v[:-1].strip()
                            if v.isdigit():
                                return {"type": "number", "value": int(v)}
                            else:
                                return {"type": "variable", "name": v}
                        program.append({
                            "type": "assign",
                            "var": var,
                            "expr": {
                                "type": "binary_op",
                                "op": op,
                                "left": parse_val(left),
                                "right": parse_val(right)
                            }
                        })
                        break
            elif expr.isdigit():
                program.append({"type": "assign", "var": var, "expr": {"type": "number", "value": int(expr)}})
            else:
                program.append({"type": "assign", "var": var, "expr": {"type": "variable", "name": expr}})
    return program

@app.route('/')
def index():
    return render_template("index.html")  # frontend page

@app.route('/run', methods=['POST'])
def run():
    global env
    reset_hot_usage()
    env = {}

    data = request.json
    code = data.get("code", "")
    lines = code.splitlines()

    program = parse_code(lines)
    output_lines = []

    for stmt in program:
        if stmt["type"] == "assign":
            value = eval_expr(stmt["expr"])
            env[stmt["var"]] = value
        elif stmt["type"] == "print":
            val = eval_expr(stmt["expr"])
            output_lines.append(str(val))

    hot_ops = [op for op, count in hot_usage.items() if count > HOT_THRESHOLD]

    return jsonify({
        "output": "\n".join(output_lines),
        "ast": program,
        "hot_ops": hot_ops
    })

if __name__ == '__main__':
    app.run(debug=True)
