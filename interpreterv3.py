# document that we won't have a return inside the init/update of a for loop

import copy
from enum import Enum

from brewparse import parse_program
from env_v3 import EnvironmentManager
from intbase import InterpreterBase, ErrorType
from type_valuev3 import Type, Value, create_value, get_printable


class ExecStatus(Enum):
    CONTINUE = 1
    RETURN = 2


# Main interpreter class
class Interpreter(InterpreterBase):
    # constants
    NIL_VALUE = create_value(InterpreterBase.NIL_DEF)
    TRUE_VALUE = create_value(InterpreterBase.TRUE_DEF)
    BIN_OPS = {"+", "-", "*", "/", "==", "!=", ">", ">=", "<", "<=", "||", "&&"}

    # methods
    def __init__(self, console_output=True, inp=None, trace_output=False):
        super().__init__(console_output, inp)
        self.trace_output = trace_output
        self.__setup_ops()

    # run a program that's provided in a string
    # usese the provided Parser found in brewparse.py to parse the program
    # into an abstract syntax tree (ast)
    def run(self, program):
        ast = parse_program(program)
        self.__set_up_struct_table(ast)
        self.__set_up_function_table(ast)
        self.env = EnvironmentManager()
        self.__call_func_aux("main", [])

    def __set_up_struct_table(self, ast):
        self.struct_defs = {}
        for struct_def in ast.get("structs"):
            struct_name = struct_def.get("name")
            if struct_name in self.struct_defs:
                super().error(ErrorType.NAME_ERROR, f"Duplicate struct definition: {struct_name}")
            field_defs = struct_def.get("fields")
            fields = {}
            for field_def in field_defs:
                field_name = field_def.get("name")
                field_type = field_def.get("var_type")
                if field_name in fields:
                    super().error(ErrorType.NAME_ERROR, f"Duplicate field name {field_name} in struct {struct_name}")
                fields[field_name] = Value(field_type, self.__default_val(field_type))
            self.struct_defs[struct_name] = fields

    def __set_up_function_table(self, ast):
        self.func_name_to_ast = {}
        for func_def in ast.get("functions"):
            func_name = func_def.get("name")
            args = func_def.get("args")
            for arg in args:
                if arg.get("var_type") != Type.BOOL and arg.get("var_type") != Type.INT and arg.get("var_type") != Type.STRING and arg.get("var_type") not in self.struct_defs:
                    super().error(ErrorType.TYPE_ERROR, f"Parameter can not be of type {arg.get("var_type")}")
            if func_def.get("return_type") == None:
                super().error(ErrorType.TYPE_ERROR, f"No return type for function {func_name}")
            num_params = len(func_def.get("args"))
            if func_name not in self.func_name_to_ast:
                self.func_name_to_ast[func_name] = {}
            self.func_name_to_ast[func_name][num_params] = func_def

    #Can use this func to get func_def node, can also append return type and arg types to hash map
    def __get_func_by_name(self, name, num_params):
        if name not in self.func_name_to_ast:
            super().error(ErrorType.NAME_ERROR, f"Function {name} not found")
        candidate_funcs = self.func_name_to_ast[name]
        if num_params not in candidate_funcs:
            super().error(
                ErrorType.NAME_ERROR,
                f"Function {name} taking {num_params} params not found",
            )
        return candidate_funcs[num_params]

    def __run_statements(self, statements):
        self.env.push_block()
        for statement in statements:
            if self.trace_output:
                print(statement)
            status, return_val = self.__run_statement(statement)
            if status == ExecStatus.RETURN:
                self.env.pop_block()
                return (status, return_val)

        self.env.pop_block()
        return (ExecStatus.CONTINUE, Interpreter.NIL_VALUE)

    def __run_statement(self, statement):
        status = ExecStatus.CONTINUE
        return_val = None
        if statement.elem_type == InterpreterBase.FCALL_NODE:
            self.__call_func(statement)
        elif statement.elem_type == "=":
            self.__assign(statement)
        elif statement.elem_type == InterpreterBase.VAR_DEF_NODE:
            self.__var_def(statement)
        elif statement.elem_type == InterpreterBase.RETURN_NODE:
            status, return_val = self.__do_return(statement)
        elif statement.elem_type == Interpreter.IF_NODE:
            status, return_val = self.__do_if(statement)
        elif statement.elem_type == Interpreter.FOR_NODE:
            status, return_val = self.__do_for(statement)

        return (status, return_val)
    
    def __call_func(self, call_node):
        func_name = call_node.get("name")
        actual_args = call_node.get("args")
        return self.__call_func_aux(func_name, actual_args)

    def __call_func_aux(self, func_name, actual_args):
        if func_name == "print":
            return self.__call_print(actual_args)
        if func_name == "inputi" or func_name == "inputs":
            return self.__call_input(func_name, actual_args)

        func_ast = self.__get_func_by_name(func_name, len(actual_args))
        arg_types = []
        for arg in func_ast.get("args"):
            arg_types.append(arg.get("var_type"))
        return_type = func_ast.get("return_type")
        if return_type == None:
            super().error(
                ErrorType.TYPE_ERROR,
                f"No return type provided",
            )

        formal_args = func_ast.get("args")
        if len(actual_args) != len(formal_args):
            super().error(
                ErrorType.NAME_ERROR,
                f"Function {func_ast.get('name')} with {len(actual_args)} args not found",
            )

        # first evaluate all of the actual parameters and associate them with the formal parameter names
        args = {}
        #add param types to check in this for loop
        for formal_ast, actual_ast, arg_type in zip(formal_args, actual_args, arg_types):
            if actual_ast.elem_type == InterpreterBase.NEW_NODE:
                v = actual_ast.get("var_type")
            elif actual_ast.elem_type == InterpreterBase.VAR_NODE:
                temp = self.env.get(actual_ast.get("name"))
                v = temp.type()
            else:
                v = actual_ast.elem_type
            # if arg_type != Type.BOOL and arg_type != Type.INT and arg_type != Type.STRING and arg_type not in self.struct_defs:
            #     super().error(
            #         ErrorType.TYPE_ERROR,
            #         f"You can not pass an argument of type {v} to {arg_type}",
            #     )
            if v != arg_type and not (v in self.BIN_OPS and (arg_type == Type.INT or arg_type == Type.BOOL)) and not(v == Type.NIL and arg_type in self.struct_defs):
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"You can not pass an argument of type {v} to {arg_type}",
                )
            result = copy.copy(self.__eval_expr(actual_ast))
            if arg_type == Type.BOOL and result.type() == Type.INT:
                result = self.__coerce(result.value())
            arg_name = formal_ast.get("name")
            args[arg_name] = result

        # then create the new activation record 
        self.env.push_func()
        # and add the formal arguments to the activation record
        for arg_name, value in args.items():
          self.env.create(arg_name, value)
        #Can check if this is a return using the blank
        status, return_val = self.__run_statements(func_ast.get("statements"))
        self.env.pop_func()
        if status == ExecStatus.RETURN:
            if return_type in self.struct_defs and return_val.type() == Type.NIL:
                return return_val
            if return_val.type() == Type.NIL:
                return Value(return_type, self.__default_val(return_type))
            if return_val.type() == Type.INT and return_type == Type.BOOL:
                return_val = self.__coerce(return_val.value())
            if return_val.type() != return_type:
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"You can not return a value of type {return_val.type()} to a function of return type {return_type}",
                )
        if return_type == Type.VOID:
            return_val = Value(Type.VOID, None)
        if return_val.type() == Type.NIL:
                return Value(return_type, self.__default_val(return_type))
        return return_val

    def __call_print(self, args):
        output = ""
        for arg in args:
            result = self.__eval_expr(arg)  # result is a Value object
            output = output + get_printable(result)
        super().output(output)
        return Interpreter.NIL_VALUE

    def __call_input(self, name, args):
        if args is not None and len(args) == 1:
            result = self.__eval_expr(args[0])
            super().output(get_printable(result))
        elif args is not None and len(args) > 1:
            super().error(
                ErrorType.NAME_ERROR, "No inputi() function that takes > 1 parameter"
            )
        inp = super().get_input()
        if name == "inputi":
            return Value(Type.INT, int(inp))
        if name == "inputs":
            return Value(Type.STRING, inp)

    def __assign(self, assign_ast):
        var_name = assign_ast.get("name")
        var_val = self.env.get(var_name)
        value_obj = self.__eval_expr(assign_ast.get("expression"))
        if "." in var_name:
            self.__assign_field_value(var_name, value_obj)
            return
        if var_val.type() == Type.BOOL and value_obj.type() == Type.INT:
            if value_obj.value() == 0:
                value_obj = create_value("false")
            else:
                value_obj = create_value("true")
        if var_val.type() != value_obj.type() and not (var_val.type() in self.struct_defs and value_obj.type() == Type.NIL) and not (var_val.type() == Type.NIL and value_obj.type() in self.struct_defs):
            super().error(
                ErrorType.TYPE_ERROR, f"Types {var_val.type()} and {value_obj.type()} are imcompatible for assignment"
            )
        if not self.env.set(var_name, value_obj):
            super().error(
                ErrorType.NAME_ERROR, f"Undefined variable {var_name} in assignment"
            )
    
    def __var_def(self, var_ast):
        var_name = var_ast.get("name")
        var_type = var_ast.get("var_type")
        if var_type == None:
            super().error(
                ErrorType.TYPE_ERROR, f"No type provided for {var_name}"
            )
        if var_type != Type.BOOL and var_type != Type.INT and var_type != Type.STRING and var_type != Type.NIL and var_type not in self.struct_defs:
            super().error(
                ErrorType.TYPE_ERROR, f"No type {var_type} exists"
            )
        default = self.__default_val(var_type)
        if default == None:
            value = Interpreter.NIL_VALUE
        else:
            value = Value(var_type, self.__default_val(var_type))
        if not self.env.create(var_name, value):
            super().error(
                ErrorType.NAME_ERROR, f"Duplicate definition for variable {var_name}"
            )
    
    def __default_val(self, var_type):
        if var_type == Type.BOOL:
            return False
        if var_type == Type.INT:
            return 0
        if var_type == Type.STRING:
            return ""
        if var_type in self.struct_defs:
            return None
        #Add default value for structs here
        ErrorType.TYPE_ERROR, f"Unknown type {var_type}"

    def __eval_expr(self, expr_ast):
        if expr_ast.elem_type == InterpreterBase.NIL_NODE:
            return Interpreter.NIL_VALUE
        if expr_ast.elem_type == InterpreterBase.INT_NODE:
            return Value(Type.INT, expr_ast.get("val"))
        if expr_ast.elem_type == InterpreterBase.STRING_NODE:
            return Value(Type.STRING, expr_ast.get("val"))
        if expr_ast.elem_type == InterpreterBase.BOOL_NODE:
            return Value(Type.BOOL, expr_ast.get("val"))
        if expr_ast.elem_type == InterpreterBase.VAR_NODE:
            var_name = expr_ast.get("name")
            if "." in var_name:
                return self.__get_field_value(var_name)
            val = self.env.get(var_name)
            if val is None:
                super().error(ErrorType.NAME_ERROR, f"Variable {var_name} not found")
            return val
        if expr_ast.elem_type == InterpreterBase.FCALL_NODE:
            return self.__call_func(expr_ast)
        if expr_ast.elem_type in Interpreter.BIN_OPS:
            return self.__eval_op(expr_ast)
        if expr_ast.elem_type == Interpreter.NEG_NODE:
            return self.__eval_unary(expr_ast, Type.INT, lambda x: -1 * x)
        if expr_ast.elem_type == Interpreter.NOT_NODE:
            return self.__eval_unary(expr_ast, Type.BOOL, lambda x: not x)
        if expr_ast.elem_type == Interpreter.NEW_NODE:
            struct_name = expr_ast.get("var_type")
            if struct_name not in self.struct_defs:
                super().error(ErrorType.TYPE_ERROR, f"Struct {struct_name} not found")
            return Value(struct_name, self.__default_val(struct_name))
    
    def __get_field_value(self, dot_line):
        parts = dot_line.split(".")
        var_name = parts[0]
        field_name = parts[1]
        var = self.env.get(var_name)
        if var.type() == Type.NIL:
            super().error(
                ErrorType.FAULT_ERROR,
                f"Variable to the left of the dot operator is nil",
            )
        if var.type() not in self.struct_defs:
            super().error(
                ErrorType.TYPE_ERROR,
                f"Variable to the left of the dot operator is not type struct",
            )
        if field_name not in self.struct_defs[var.type()]:
            super().error(
                ErrorType.NAME_ERROR,
                f"{parts[1]}, is not a field",
            )
        return self.struct_defs[var.type()][field_name]
    
    def __assign_field_value(self, dot_line, value):
        parts = dot_line.split(".")
        var_name = parts[0]
        field_name = parts[1]
        var = self.env.get(var_name)
        if var.type() == Type.NIL:
            super().error(
                ErrorType.FAULT_ERROR,
                f"Variable to the left of the dot operator is nil",
            )
        if var.type() not in self.struct_defs:
            super().error(
                ErrorType.TYPE_ERROR,
                f"{var_name} is not type struct",
            )
        if field_name not in self.struct_defs[var.type()]:
            super().error(
                ErrorType.NAME_ERROR,
                f"{parts[1]}, is not a field",
            )
        self.struct_defs[var.type()][field_name] = value

    def __eval_op(self, arith_ast):
        left_value_obj = self.__eval_expr(arith_ast.get("op1"))
        right_value_obj = self.__eval_expr(arith_ast.get("op2"))
        t = left_value_obj.type()
        if t in self.struct_defs:
            t = "struct"
        if not self.__compatible_types(
            arith_ast.elem_type, left_value_obj, right_value_obj
        ):
            super().error(
                ErrorType.TYPE_ERROR,
                f"Incompatible types for {arith_ast.elem_type} operation",
            )
        if arith_ast.elem_type not in self.op_to_lambda[t]:
            super().error(
                ErrorType.TYPE_ERROR,
                f"Incompatible operator {arith_ast.elem_type} for type {t}",
            )
        if left_value_obj.type() in self.struct_defs:
            f = self.op_to_lambda["struct"][arith_ast.elem_type]
        else:
            f = self.op_to_lambda[left_value_obj.type()][arith_ast.elem_type]
        if arith_ast.elem_type in ["==", "!="]:
            if left_value_obj.type() == Type.BOOL and right_value_obj.type() == Type.INT:
                right_value_obj = self.__coerce(right_value_obj.value())
            if left_value_obj.type() == Type.INT and right_value_obj.type() == Type.BOOL:
                left_value_obj = self.__coerce(left_value_obj.value())
        if arith_ast.elem_type in ["||", "&&"]:
            if left_value_obj.type() == Type.INT:
                left_value_obj = self.__coerce(left_value_obj.value())
            if right_value_obj.type() == Type.INT:
                right_value_obj = self.__coerce(right_value_obj.value())
        return f(left_value_obj, right_value_obj)

    def __compatible_types(self, oper, obj1, obj2):
        # DOCUMENT: allow comparisons ==/!= of anything against anything
        if oper in ["==", "!=", "||", "&&"]:
            if obj1.type() == Type.BOOL and obj2.type() == Type.INT:
                obj2 = self.__coerce(obj2.value())
            if obj1.type() == Type.INT and obj2.type() == Type.BOOL:
                obj1 = self.__coerce(obj1.value())
            if obj1.type() != obj2.type() and not ((obj1.type() == Type.NIL and obj2.type() in self.struct_defs) or (obj2.type() == Type.NIL and obj1.type() in self.struct_defs)):
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Can not compare types of {obj1.type()} and {obj2.type()}",
                )
            # if (obj1.type() == Type.NIL and obj2.type() != Type.NIL) or (obj2.type() == Type.NIL and obj1.type() != Type.NIL):
            #     super().error(
            #         ErrorType.TYPE_ERROR,
            #         f"Can not compare types of {obj1.type()} and {obj2.type()}",
            #     )
            return True
        return obj1.type() == obj2.type()
    
    def __coerce(self, int_val):
        if int_val == 0:
             return create_value("false")
        else:
            return create_value("true")

    def __eval_unary(self, arith_ast, t, f):
        value_obj = self.__eval_expr(arith_ast.get("op1"))
        if value_obj.type() == Type.INT:
            value_obj = self.__coerce(value_obj.value())
        if value_obj.type() != t:
            super().error(
                ErrorType.TYPE_ERROR,
                f"Incompatible type for {arith_ast.elem_type} operation",
            )
        return Value(t, f(value_obj.value()))

    def __setup_ops(self):
        self.op_to_lambda = {}
        # set up operations on integers
        self.op_to_lambda[Type.INT] = {}
        self.op_to_lambda[Type.INT]["+"] = lambda x, y: Value(
            x.type(), x.value() + y.value()
        )
        self.op_to_lambda[Type.INT]["-"] = lambda x, y: Value(
            x.type(), x.value() - y.value()
        )
        self.op_to_lambda[Type.INT]["*"] = lambda x, y: Value(
            x.type(), x.value() * y.value()
        )
        self.op_to_lambda[Type.INT]["/"] = lambda x, y: Value(
            x.type(), x.value() // y.value()
        )
        self.op_to_lambda[Type.INT]["=="] = lambda x, y: Value(
            Type.BOOL, x.type() == y.type() and x.value() == y.value()
        )
        self.op_to_lambda[Type.INT]["!="] = lambda x, y: Value(
            Type.BOOL, x.type() != y.type() or x.value() != y.value()
        )
        self.op_to_lambda[Type.INT]["<"] = lambda x, y: Value(
            Type.BOOL, x.value() < y.value()
        )
        self.op_to_lambda[Type.INT]["<="] = lambda x, y: Value(
            Type.BOOL, x.value() <= y.value()
        )
        self.op_to_lambda[Type.INT][">"] = lambda x, y: Value(
            Type.BOOL, x.value() > y.value()
        )
        self.op_to_lambda[Type.INT][">="] = lambda x, y: Value(
            Type.BOOL, x.value() >= y.value()
        )
        self.op_to_lambda[Type.INT]["||"] = lambda x, y: Value(
            Type.BOOL, x.value() or y.value()
        )
        self.op_to_lambda[Type.INT]["&&"] = lambda x, y: Value(
            Type.BOOL, x.value() and y.value()
        )
        #  set up operations on strings
        self.op_to_lambda[Type.STRING] = {}
        self.op_to_lambda["struct"] = {}
        self.op_to_lambda[Type.STRING]["+"] = lambda x, y: Value(
            x.type(), x.value() + y.value()
        )
        self.op_to_lambda[Type.STRING]["=="] = lambda x, y: Value(
            Type.BOOL, x.value() == y.value()
        )
        self.op_to_lambda[Type.STRING]["!="] = lambda x, y: Value(
            Type.BOOL, x.value() != y.value()
        )
        self.op_to_lambda["struct"]["=="] = lambda x, y: Value(
            Type.BOOL, x is y 
        )
        self.op_to_lambda["struct"]["!="] = lambda x, y: Value(
            Type.BOOL, x != y
        )
        #  set up operations on bools
        self.op_to_lambda[Type.BOOL] = {}
        self.op_to_lambda[Type.BOOL]["&&"] = lambda x, y: Value(
            x.type(), x.value() and y.value()
        )
        self.op_to_lambda[Type.BOOL]["||"] = lambda x, y: Value(
            x.type(), x.value() or y.value()
        )
        self.op_to_lambda[Type.BOOL]["=="] = lambda x, y: Value(
            Type.BOOL, x.type() == y.type() and x.value() == y.value()
        )
        self.op_to_lambda[Type.BOOL]["!="] = lambda x, y: Value(
            Type.BOOL, x.type() != y.type() or x.value() != y.value()
        )

        #  set up operations on nil
        self.op_to_lambda[Type.NIL] = {}
        self.op_to_lambda[Type.NIL]["=="] = lambda x, y: Value(
            Type.BOOL, x.type() == y.type() and x.value() == y.value()
        )
        self.op_to_lambda[Type.NIL]["!="] = lambda x, y: Value(
            Type.BOOL, x.type() != y.type() or x.value() != y.value()
        )

    def __do_if(self, if_ast):
        cond_ast = if_ast.get("condition")
        result = self.__eval_expr(cond_ast)
        if result.type() == Type.INT:
            if result.value() == 0:
                result = create_value("false")
            else:
                result = create_value("true")
        if result.type() != Type.BOOL:
            super().error(
                ErrorType.TYPE_ERROR,
                "Incompatible type for if condition",
            )
        if result.value():
            statements = if_ast.get("statements")
            status, return_val = self.__run_statements(statements)
            return (status, return_val)
        else:
            else_statements = if_ast.get("else_statements")
            if else_statements is not None:
                status, return_val = self.__run_statements(else_statements)
                return (status, return_val)

        return (ExecStatus.CONTINUE, Interpreter.NIL_VALUE)

    def __do_for(self, for_ast):
        init_ast = for_ast.get("init") 
        cond_ast = for_ast.get("condition")
        update_ast = for_ast.get("update") 

        self.__run_statement(init_ast)  # initialize counter variable
        run_for = Interpreter.TRUE_VALUE
        while run_for.value():
            run_for = self.__eval_expr(cond_ast)  # check for-loop condition
            if run_for.type() == Type.INT:
                if run_for.value() != 0:
                    run_for = create_value("true")
                else:
                    run_for = create_value("false")
            if run_for.type() != Type.BOOL:
                super().error(
                    ErrorType.TYPE_ERROR,
                    "Incompatible type for for condition",
                )
            if run_for.value():
                statements = for_ast.get("statements")
                status, return_val = self.__run_statements(statements)
                if status == ExecStatus.RETURN:
                    return status, return_val
                self.__run_statement(update_ast)  # update counter variable

        return (ExecStatus.CONTINUE, Interpreter.NIL_VALUE)

    def __do_return(self, return_ast):
        expr_ast = return_ast.get("expression")
        if expr_ast is None:
            return (ExecStatus.RETURN, Interpreter.NIL_VALUE)
        value_obj = copy.copy(self.__eval_expr(expr_ast))
        return (ExecStatus.RETURN, value_obj)

# interpreter = Interpreter()
# interpreter.run("""func main() : int {
#   var a: int; 
#   a = true;
#   print(a);
# }
# """)