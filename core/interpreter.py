import re
from core.jit_compiler import JITCompiler

def tokenize(code):
    token_spec = r'\d+|[a-zA-Z_]\w*|==|!=|<=|>=|[+\-*/(){}<>=;,]|.'
    tokens = re.findall(token_spec, code)
    tokens = [t for t in tokens if t.strip() != '']
    return tokens

class Number:
    def __init__(self, value):
        self.value = value
    def __repr__(self):
        return f"Number({self.value})"

class Variable:
    def __init__(self, name):
        self.name = name
    def __repr__(self):
        return f"Variable({self.name})"

class BinaryOp:
    def __init__(self, op, left, right):
        self.op = op
        self.left = left
        self.right = right
    def __repr__(self):
        return f"BinaryOp({self.op}, {self.left}, {self.right})"

class Assign:
    def __init__(self, var, expr):
        self.var = var
        self.expr = expr
    def __repr__(self):
        return f"Assign({self.var}, {self.expr})"

class Print:
    def __init__(self, expr):
        self.expr = expr
    def __repr__(self):
        return f"Print({self.expr})"

class If:
    def __init__(self, cond, body, else_body=None):
        self.cond = cond
        self.body = body
        self.else_body = else_body
    def __repr__(self):
        return f"If({self.cond}, {self.body}, Else: {self.else_body})"

class While:
    def __init__(self, cond, body):
        self.cond = cond
        self.body = body
    def __repr__(self):
        return f"While({self.cond}, {self.body})"

class FunctionDef:
    def __init__(self, name, params, body):
        self.name = name
        self.params = params
        self.body = body
    def __repr__(self):
        return f"FunctionDef({self.name}, {self.params}, {self.body})"

class FunctionCall:
    def __init__(self, name, args):
        self.name = name
        self.args = args
    def __repr__(self):
        return f"FunctionCall({self.name}, {self.args})"

class Return:
    def __init__(self, expr):
        self.expr = expr
    def __repr__(self):
        return f"Return({self.expr})"

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def current(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def eat(self, token=None):
        cur = self.current()
        if token and cur != token:
            raise Exception(f"Expected '{token}', got '{cur}'")
        self.pos += 1
        return cur

    def parse(self):
        stmts = []
        while self.current() is not None:
            stmts.append(self.parse_stmt())
        return {
            "type": "program",
            "body": stmts
        }

    def parse_stmt(self):
        cur = self.current()
        if cur == "if":
            return self.parse_if()
        elif cur == "def":
            return self.parse_function_def()
        elif cur == "return":
            return self.parse_return()
        elif cur == "while":
            return self.parse_while()
        elif cur == "print":
            return self.parse_print()
        else:
            return self.parse_assign()

    def parse_if(self):
        self.eat("if")
        self.eat("(")
        cond = self.parse_expr()
        self.eat(")")
        self.eat("{")
        body = []
        while self.current() != "}":
            body.append(self.parse_stmt())
        self.eat("}")

        else_body = None
        if self.current() == "else":
            self.eat("else")
            self.eat("{")
            else_body = []
            while self.current() != "}":
                else_body.append(self.parse_stmt())
            self.eat("}")

        return {"type": "if", "cond": cond, "body": body, "else_body": else_body}

    def parse_function_def(self):
        self.eat("def")
        name = self.eat()
        self.eat("(")
        params = []
        while self.current() != ")":
            params.append(self.eat())
            if self.current() == ",":
                self.eat(",")
        self.eat(")")
        self.eat("{")
        body = []
        while self.current() != "}":
            body.append(self.parse_stmt())
        self.eat("}")
        return {"type": "function_def", "name": name, "params": params, "body": body}

    def parse_return(self):
        self.eat("return")
        expr = self.parse_expr()
        self.eat(";")
        return {"type": "return", "expr": expr}

    def parse_while(self):
        self.eat("while")
        self.eat("(")
        cond = self.parse_expr()
        self.eat(")")
        self.eat("{")
        body = []
        while self.current() != "}":
            body.append(self.parse_stmt())
        self.eat("}")
        return {"type": "while", "cond": cond, "body": body}

    def parse_print(self):
        self.eat("print")
        self.eat("(")
        expr = self.parse_expr()
        self.eat(")")
        self.eat(";")
        return {"type": "print", "expr": expr}

    def parse_assign(self):
        var = self.eat()
        if not re.match(r"[a-zA-Z_]\w*", var):
            raise Exception(f"Invalid variable name {var}")
        self.eat("=")
        expr = self.parse_expr()
        self.eat(";")
        return {
            "type": "assign",
            "var": var,
            "expr": expr
        }


    def parse_expr(self):
        return self.parse_rel()

    def parse_rel(self):
        node = self.parse_add()
        while self.current() in ("==", "!=", "<", ">", "<=", ">="):
            op = self.eat()
            right = self.parse_add()
            node = {"type": "binary_op", "op": op, "left": node, "right": right}
        return node

    def parse_add(self):
        node = self.parse_mul()
        while self.current() in ("+", "-"):
            op = self.eat()
            right = self.parse_mul()
            node = {"type": "binary_op", "op": op, "left": node, "right": right}
        return node

    def parse_mul(self):
        node = self.parse_factor()
        while self.current() in ("*", "/"):
            op = self.eat()
            right = self.parse_factor()
            node = {"type": "binary_op", "op": op, "left": node, "right": right}
        return node

    def parse_factor(self):
        cur = self.current()
        if cur == "(":
            self.eat("(")
            node = self.parse_expr()
            self.eat(")")
            return node
        elif cur is not None and cur.isdigit():
            val = int(self.eat())
            return {"type": "number", "value": val}
        elif cur is not None and re.match(r"[a-zA-Z_]\w*", cur):
            name = self.eat()
            if self.current() == "(":  
                self.eat("(")
                args = []
                while self.current() != ")":
                    args.append(self.parse_expr())
                    if self.current() == ",":
                        self.eat(",")
                self.eat(")")
                return {"type": "function_call", "name": name, "args": args}
            else:
                return {"type": "variable", "name": name}
        else:
            raise Exception(f"Unexpected token {cur}")

class Interpreter:
    def __init__(self, ast):
        self.ast = ast
        self.env = {}
        self.output = []
        self.functions = {}
        self.call_counts = {}  
        self.hot_threshold = 10 
        self.jit = JITCompiler()
        self.compiled_functions = {}

    class ReturnException(Exception):
        def __init__(self, value):
            self.value = value

    def eval_expr(self, expr, env):
        t = expr["type"]
        if t == "number":
            return expr["value"]
        elif t == "variable":
            return env.get(expr["name"], 0)
        elif t == "binary_op":
            left = self.eval_expr(expr["left"],env)
            right = self.eval_expr(expr["right"],env)
            op = expr["op"]
            if op == "+":
                return left + right
            elif op == "-":
                return left - right
            elif op == "*":
                return left * right
            elif op == "/":
                return left // right if right != 0 else 0
            elif op == "==":
                return 1 if left == right else 0
            elif op == "!=":
                return 1 if left != right else 0
            elif op == "<":
                return 1 if left < right else 0
            elif op == ">":
                return 1 if left > right else 0
            elif op == "<=":
                return 1 if left <= right else 0
            elif op == ">=":
                return 1 if left >= right else 0
            else:
                raise Exception(f"Unknown op {op}")
        elif t == "function_call":
            func_name = expr["name"]
            func = self.functions.get(func_name)
            if not func:
                raise Exception(f"Function {func_name} not defined")

            self.call_counts[func_name] = self.call_counts.get(func_name, 0) + 1
            if self.call_counts[func_name] == self.hot_threshold:
                func_ptr = self.jit.compile_function(func)
                callable_fn = self.jit.get_callable(func_name)
                self.compiled_functions[func_name] = callable_fn
            if func_name in self.compiled_functions:
                args = [self.eval_expr(arg, env) for arg in expr["args"]]
                while len(args) < 5:
                    args.append(0)
                result = self.compiled_functions[func_name](*args[:5])
                return result
            args = [self.eval_expr(arg, env) for arg in expr["args"]]
            new_env = dict(zip(func["params"], args))
            saved_env = env
            env = new_env
            try:
                for stmt in func["body"]:
                    self.run_stmt(stmt, env)
            except Interpreter.ReturnException as r:
                env = saved_env
                return r.value
            env = saved_env
            return 0
        
    def get_hot_operations(self):
        return {
            name: count
            for name, count in self.call_counts.items()
            if count >= self.hot_threshold
        }

    def run_stmt(self, stmt, env):
        t = stmt["type"]
        if t == "assign":
            val = self.eval_expr(stmt["expr"], env)
            env[stmt["var"]] = val
        elif t == "print":
            val = self.eval_expr(stmt["expr"], env)
            self.output.append(str(val))
        elif t == "if":
            cond = self.eval_expr(stmt["cond"], env)
            if cond != 0:
                self.run_block(stmt["body"], env)
            elif stmt.get("else_body") is not None:
                self.run_block(stmt["else_body"], env)
        elif t == "while":
            while self.eval_expr(stmt["cond"], env) != 0:
                self.run_block(stmt["body"], env)
        elif t == "function_def":
            self.functions[stmt["name"]] = stmt
        elif t == "return":
            val = self.eval_expr(stmt["expr"], env)
            raise Interpreter.ReturnException(val)
        else:
            raise Exception(f"Unknown stmt type {t}")

    def run_block(self, stmts, env):
        for stmt in stmts:
            self.run_stmt(stmt, env)

    def run(self):
        self.run_block(self.ast["body"], self.env)
        return self.output

def parse_code(code_str):
    tokens = tokenize(code_str)
    parser = Parser(tokens)
    ast = parser.parse()
    if isinstance(ast, list):
        ast = {"body": ast}  
    return ast

def eval_program(ast):
    interpreter = Interpreter(ast)  
    output = interpreter.run()
    hot_ops = interpreter.get_hot_operations()
    return "\n".join(output), hot_ops

def print_ast_tree(ast, indent=0):
    spacing = "  " * indent
    if isinstance(ast, dict):
        for key, value in ast.items():
            print(f"{spacing}{key}:")
            print_ast_tree(value, indent + 1)
    elif isinstance(ast, list):
        for i, item in enumerate(ast):
            print(f"{spacing}- item {i}:")
            print_ast_tree(item, indent + 1)
    else:
        print(f"{spacing}{ast}")
        
if __name__ == "__main__":
    print("Enter your code (end with an empty line):")
    lines = []
    while True:
        line = input()
        if line.strip() == "":
            break
        lines.append(line)
    code = "\n".join(lines)

    ast = parse_code(code)

    import json
    print("\nAST (as JSON):")
    print(json.dumps(ast, indent=2))

    print("\nAST (as Tree):")
    print_ast_tree(ast) 

    output, hot_ops = eval_program(ast)

    print("\nOutput:")
    print(output)

    print("\nHot Operations:")
    print(hot_ops)
