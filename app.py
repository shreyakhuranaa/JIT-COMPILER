from flask import Flask, request, jsonify, render_template
from llvmlite import ir, binding

app = Flask(__name__)

env = {}
hot_usage = {}
HOT_THRESHOLD = 2

binding.initialize()
binding.initialize_native_target()
binding.initialize_native_asmprinter()

llvm_module = None
llvm_engine = None
llvm_builder = None
llvm_func = None
llvm_vars = {}
last_print_var = None  # track last printed variable name

def create_execution_engine():
    target = binding.Target.from_default_triple()
    target_machine = target.create_target_machine()
    backing_mod = binding.parse_assembly("")
    engine = binding.create_mcjit_compiler(backing_mod, target_machine)
    return engine

def compile_ir(ir_code):
    mod = binding.parse_assembly(ir_code)
    mod.verify()
    llvm_engine.add_module(mod)
    llvm_engine.finalize_object()
    llvm_engine.run_static_constructors()
    return mod

def reset_llvm():
    global llvm_module, llvm_engine, llvm_builder, llvm_func, llvm_vars, last_print_var
    llvm_module = ir.Module(name="module")
    llvm_engine = create_execution_engine()
    # main returns int32 now (last printed value)
    llvm_func = ir.Function(llvm_module, ir.FunctionType(ir.IntType(32), []), name="main")
    block = llvm_func.append_basic_block(name="entry")
    llvm_builder = ir.IRBuilder(block)
    llvm_vars = {}
    last_print_var = None

def reset_hot_usage():
    global hot_usage
    hot_usage = {}

def llvm_eval(expr):
    if expr["type"] == "number":
        return ir.Constant(ir.IntType(32), expr["value"])
    elif expr["type"] == "variable":
        ptr = llvm_vars.get(expr["name"])
        return llvm_builder.load(ptr, name=expr["name"]) if ptr else ir.Constant(ir.IntType(32), 0)
    elif expr["type"] == "binary_op":
        op = expr["op"]
        left = llvm_eval(expr["left"])
        right = llvm_eval(expr["right"])

        hot_usage[op] = hot_usage.get(op, 0) + 1

        if op == "+":
            return llvm_builder.add(left, right, name="addtmp")
        elif op == "-":
            return llvm_builder.sub(left, right, name="subtmp")
        elif op == "*":
            return llvm_builder.mul(left, right, name="multmp")
        elif op == "/":
            return llvm_builder.sdiv(left, right, name="divtmp")
    return ir.Constant(ir.IntType(32), 0)

def execute_llvm():
    global last_print_var
    # Return the value of last_print_var or 0 if none
    if last_print_var and last_print_var in llvm_vars:
        ret_val = llvm_builder.load(llvm_vars[last_print_var], name="retval")
    else:
        ret_val = ir.Constant(ir.IntType(32), 0)
    llvm_builder.ret(ret_val)

    mod = compile_ir(str(llvm_module))
    func_ptr = llvm_engine.get_function_address("main")
    from ctypes import CFUNCTYPE, c_int
    cfunc = CFUNCTYPE(c_int)(func_ptr)
    return cfunc()

def parse_code(lines):
    program = []
    for line in lines:
        line = line.strip()
        if line.endswith(';'):
            line = line[:-1].strip()
        if line.startswith("print"):
            if line.startswith("print(") and line.endswith(")"):
                var = line[6:-1].strip()
            else:
                var = line[5:].strip()
            program.append({"type": "print", "expr": {"type": "variable", "name": var}})
        elif "=" in line:
            var, expr = line.split("=", 1)
            var = var.strip()
            expr = expr.strip()
            for op in ["+", "-", "*", "/"]:
                if op in expr:
                    left, right = expr.split(op, 1)
                    def parse_val(v):
                        v = v.strip()
                        return {"type": "number", "value": int(v)} if v.isdigit() else {"type": "variable", "name": v}
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
            else:
                if expr.isdigit():
                    program.append({"type": "assign", "var": var, "expr": {"type": "number", "value": int(expr)}})
                else:
                    program.append({"type": "assign", "var": var, "expr": {"type": "variable", "name": expr}})
    return program

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/run', methods=['POST'])
def run():
    global env, last_print_var
    reset_hot_usage()
    env = {}
    reset_llvm()

    data = request.json
    code = data.get("code", "")
    lines = code.splitlines()

    program = parse_code(lines)
    output_lines = []

    for stmt in program:
        if stmt["type"] == "assign":
            val = llvm_eval(stmt["expr"])
            ptr = llvm_builder.alloca(ir.IntType(32), name=stmt["var"])
            llvm_builder.store(val, ptr)
            llvm_vars[stmt["var"]] = ptr
        elif stmt["type"] == "print":
            var_name = stmt["expr"]["name"]
            last_print_var = var_name

    ret = execute_llvm()
    output_lines.append(str(ret))

    hot_ops = [op for op, count in hot_usage.items() if count > HOT_THRESHOLD]

    return jsonify({
        "output": "\n".join(output_lines),
        "ast": program,
        "hot_ops": hot_ops
    })

if __name__ == '__main__':
    app.run(debug=True)
