from llvmlite import ir, binding
import ctypes

class JITCompiler:
    def __init__(self):
        try:
            binding.initialize()
            binding.initialize_native_target()
            binding.initialize_native_asmprinter()

            self.module = ir.Module(name="jit_module")
            self.engine = self.create_execution_engine()
            self.func_protos = {}
        except Exception as e:
            print(f"[Init Error] Failed to initialize LLVM: {e}")
            raise

    def create_execution_engine(self):
        try:
            target = binding.Target.from_default_triple()
            target_machine = target.create_target_machine()
            backing_mod = binding.parse_assembly("")
            engine = binding.create_mcjit_compiler(backing_mod, target_machine)
            return engine
        except Exception as e:
            print(f"[Engine Error] Failed to create execution engine: {e}")
            raise

    def compile_ir(self):
        try:
            llvm_ir = str(self.module)
            mod = binding.parse_assembly(llvm_ir)
            mod.verify()
            self.engine.add_module(mod)
            self.engine.finalize_object()
            self.engine.run_static_constructors()
            self.module = ir.Module(name="jit_module") 
        except Exception as e:
            print(f"[IR Compile Error] Failed to compile LLVM IR: {e}")
            raise

    def compile_function(self, func_ast):
        try:
            func_name = func_ast["name"]
            params = func_ast["params"]

            func_type = ir.FunctionType(ir.IntType(64), [ir.IntType(64)] * len(params))
            function = ir.Function(self.module, func_type, name=func_name)

            block = function.append_basic_block(name="entry")
            builder = ir.IRBuilder(block)

            named_vars = {}
            for i, arg in enumerate(function.args):
                arg.name = params[i]
                named_vars[arg.name] = arg

            retval = self.compile_statements(func_ast["body"], builder, named_vars)
            builder.ret(retval)

            self.compile_ir()
        except Exception as e:
            print(f"[Function Compile Error] Failed to compile function '{func_ast.get('name', '?')}': {e}")
            raise

    def compile_statements(self, stmts, builder, named_vars):
        retval = None
        for stmt in stmts:
            if stmt["type"] == "return":
                retval = self.compile_expr(stmt["expr"], builder, named_vars)

            elif stmt["type"] == "assign":
                var_name = stmt["var"]
                val = self.compile_expr(stmt["expr"], builder, named_vars)
                if var_name not in named_vars:
                    alloca = builder.alloca(ir.IntType(64), name=var_name)
                    named_vars[var_name] = alloca
                builder.store(val, named_vars[var_name])

            elif stmt["type"] == "while":
                self.compile_while(stmt, builder, named_vars)

            else:
                raise Exception(f"Unsupported statement type: {stmt['type']}")
        return retval
    
    def compile_while(self, stmt, builder, named_vars):
        loop_cond = builder.append_basic_block("loop_cond")
        loop_body = builder.append_basic_block("loop_body")
        loop_end = builder.append_basic_block("loop_end")
        builder.branch(loop_cond)
        builder.position_at_end(loop_cond)
        cond_val = self.compile_expr(stmt["cond"], builder, named_vars)
        zero = ir.Constant(ir.IntType(64), 0)
        cond = builder.icmp_signed("!=", cond_val, zero, name="while_cond")
        builder.cbranch(cond, loop_body, loop_end)
        builder.position_at_end(loop_body)
        self.compile_statements(stmt["body"], builder, named_vars)
        builder.branch(loop_cond)
        builder.position_at_end(loop_end)

    def compile_expr(self, expr, builder, named_vars):
        try:
            t = expr["type"]

            if t == "number":
                return ir.Constant(ir.IntType(64), expr["value"])

            elif t == "variable":
                var_name = expr["name"]
                if var_name not in named_vars:
                    raise Exception(f"Unknown variable '{var_name}'")
                return named_vars[var_name]

            elif t == "binary_op":
                left = self.compile_expr(expr["left"], builder, named_vars)
                right = self.compile_expr(expr["right"], builder, named_vars)
                op = expr["op"]
                if op == "+":
                    return builder.add(left, right, name="addtmp")
                elif op == "-":
                    return builder.sub(left, right, name="subtmp")
                elif op == "*":
                    return builder.mul(left, right, name="multmp")
                elif op == "/":
                    return builder.sdiv(left, right, name="divtmp")
                else:
                    raise Exception(f"Unsupported binary operation '{op}'")
            elif t == "function_call":
                func_name = expr["name"]
                args = [self.compile_expr(arg, builder, named_vars) for arg in expr["args"]]
                func = self.module.globals.get(func_name)
                if not func or not isinstance(func, ir.Function):
                    raise Exception(f"Function '{func_name}' not defined")

                return builder.call(func, args, name=f"call_{func_name}")

            else:
                raise Exception(f"Unsupported expression type '{t}'")
        except Exception as e:
            print(f"[Expression Error] {e}")
            raise

    def get_callable(self, func_name):
        try:
            func_ptr = self.engine.get_function_address(func_name)

            if func_ptr == 0:
                raise Exception(f"Function '{func_name}' not found in JIT")

            def make_callable(nargs):
                FUNC_TYPE = ctypes.CFUNCTYPE(ctypes.c_longlong, *([ctypes.c_longlong] * nargs))
                return FUNC_TYPE(func_ptr)

            return make_callable(5)
        except Exception as e:
            print(f"[Callable Error] Failed to get callable for '{func_name}': {e}")
            raise
