# Add to spec:
# - printing out a nil value is undefined

from env_v1 import EnvironmentManager
from type_valuev1 import Type, Value, create_value, get_printable
from intbase import InterpreterBase, ErrorType
from brewparse import parse_program


# Main interpreter class
class Interpreter(InterpreterBase):
    # constants
    BIN_OPS = {"+", "-", "*", "/"} # Add * and / to Binary operators
    COM_OPS = {">", "<", ">=", "<="} # Comparison operators
    LOG_OPS = {"&&", "||", "!"} # Logical operators
    EQU_OPS = {"==", "!="} # Equality Operators

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
        self.__set_up_function_table(ast)
        # Initialize a new environment scope for the main function
        main_scope = EnvironmentManager()
        self.env = [main_scope]
        # Execute the statements in the main function and capture the return value
        result = self.__run_statements(main_func.get("statements"))
        # Clean up by removing the main function's scope from the environment stack
        self.env.pop()
        # Return the final result of the main function execution
        return result.value().value()


    def __set_up_function_table(self, ast):
        self.func_name_to_ast = {}
        for func_def in ast.get("functions"):
            self.func_name_to_ast[func_def.get("name"),len(func_def.get("args"))] = func_def

    def __get_func_by_name(self, name):
        if name not in self.func_name_to_ast:
            super().error(ErrorType.NAME_ERROR, f"Function {name} not found")
        return self.func_name_to_ast[name]

    def __run_statements(self, statements):
        # all statements of a function are held in arg3 of the function AST node
        for statement in statements:
            if self.trace_output:
                print(statement)
            if statement.elem_type == InterpreterBase.FCALL_NODE:
                self.__call_func(statement)
            elif statement.elem_type == "=":
                self.__assign(statement)
            elif statement.elem_type == InterpreterBase.VAR_DEF_NODE:
                self.__var_def(statement)
            elif statement.elem_type == InterpreterBase.IF_NODE:
                result = self.__call_if_statement(statement)
                if result is not None:
                    return result
            elif statement.elem_type == InterpreterBase.WHILE_NODE:
                self.__call_while_loop(statement)
                result = self.__call_if_statement(statement)
                if result is not None:
                    return result

    def __call_func(self, call_node):
        func_name = call_node.get("name")
        if func_name == "print":
            return self.__call_print(call_node)
        elif func_name == "inputi":
            return self.__call_input(call_node)
        elif func_name == "inputs":
            return self.__call_input(call_node)
        # Check if the function is a user-defined function
        args = call_node.get("args")
        func_key = (func_name, len(args))
        if func_key in self.func_name_to_ast:
            # Retrieve the function definition and set up a new environment scope
            func_def = self.__get_func_by_name(func_key)
            new_scope = EnvironmentManager()
            # Initialize function parameters with evaluated argument values
            for param, arg_value in zip(func_def.get("args"), args):
                evaluated_value = self.__eval_expr(arg_value)
                new_scope.set(param.get("name"), evaluated_value)
                
            # Run the function with the new scope in place
            self.env.append(new_scope)
            return_value = self.__run_statements(func_def.get("statements"))
            self.env.pop()
            
            # Return the evaluated function result
            return return_value.value()
            
        # If function name or argument count do not match, an error could be raised
        else:
            super().error(ErrorType.NAME_ERROR, f"Function {func_name} not found")

        

        # add code here later to call other functions
        super().error(ErrorType.NAME_ERROR, f"Function {func_name} not found")
    
    def __call_if_statement(self, if_node):
        # Evaluate the condition of the if-statement
        condition_expr = if_node.get("condition")

        # Ensure the condition is of boolean type
        if condition_expr.elem_type == InterpreterBase.VAR_NODE and condition_result.type() != Type.BOOL:
            super().error(ErrorType.TYPE_ERROR)

        condition_result = self.__eval_expr(condition_expr)

        # Execute the 'if' block if the condition is true
        if condition_result.value():
            if_scope = EnvironmentManager()
            self.env.append(if_scope)
            result = self.__run_statements(if_node.get("statements"))
            self.env.pop()  # Remove scope after execution

            # Return if a return value is encountered
            if result.type() == Type.RET:
                return result

        # Execute the 'else' block if present and condition is false
        elif if_node.get("else_statements") is not None:
            else_scope = EnvironmentManager()
            self.env.append(else_scope)
            result = self.__run_statements(if_node.get("else_statements"))
            self.env.pop()  # Remove scope after execution

            # Return if a return value is encountered
            if result.type() == Type.RET:
                return result

    def __call_while_loop(self, while_node):
        # Initialize a new scope for the while-loop
        loop_scope = EnvironmentManager()
        self.env.append(loop_scope)
        
        # Validate the loop condition
        condition_expr = while_node.get("condition")
        if condition_expr.elem_type == InterpreterBase.VAR_NODE:
            super().error(ErrorType.TYPE_ERROR)

        # Evaluate and execute the loop as long as the condition is true
        while True:
            condition_value = self.__eval_expr(condition_expr)

            # Ensure the condition evaluates to a boolean
            if not isinstance(condition_value.value(), bool) or not condition_value.value():
                break  # Exit loop if condition is false or not a boolean

            # Execute loop body statements
            result = self.__run_statements(while_node.get("statements"))

            # Return early if a return value is encountered in the loop body
            if result.type() == Type.RET:
                self.env.pop()  # Remove loop scope
                return result

        # Clean up the environment after loop completion
        self.env.pop()

    def __call_print(self, call_ast):
        output = ""
        for arg in call_ast.get("args"):
            result = self.__eval_expr(arg)  # result is a Value object
            output = output + get_printable(result)
        super().output(output)
        return create_value(InterpreterBase.NIL_NODE)

    def __call_input(self, call_ast):
        args = call_ast.get("args")
        if args is not None and len(args) == 1:
            result = self.__eval_expr(args[0])
            super().output(get_printable(result))
        elif args is not None and len(args) > 1:
            super().error(
                ErrorType.NAME_ERROR, "No inputi() function that takes > 1 parameter"
            )
        inp = super().get_input()
        if call_ast.get("name") == "inputi":
            return Value(Type.INT, int(inp))
        # we can support inputs here later
        if call_ast.get("name") == "inputs":
            first_word = str(inp).split()[0]  # Extract the first word from input
            return Value(Type.STRING, first_word)


    def __assign(self, assign_ast):
        var_name = assign_ast.get("name")
        value_obj = self.__eval_expr(assign_ast.get("expression"))
        # Default to the innermost (current) scope
        target_scope = self.env[-1]

        # Traverse the environment stack from innermost to outermost scope
        bool found = False
        for scope in reversed(self.env):
            if scope.get(var_name) is not None:
                target_scope = scope
                found = True
                break  # Stop once the variable is found in a scope
        if not found:
            super().error(
                ErrorType.NAME_ERROR, f"Undefined variable {var_name} in assignment"
            )
        # Update the variable's value in the appropriate scope
        target_scope.set(var_name, value_obj)


    def __var_def(self, var_ast):
        var_name = var_ast.get("name")
        if not self.env.create(var_name, Value(Type.INT, 0)):
            super().error(
                ErrorType.NAME_ERROR, f"Duplicate definition for variable {var_name}"
            )

    def __eval_expr(self, expr_ast):
        if expr_ast.elem_type == InterpreterBase.INT_NODE:
            return Value(Type.INT, expr_ast.get("val"))
        if expr_ast.elem_type == InterpreterBase.STRING_NODE:
            return Value(Type.STRING, expr_ast.get("val"))
        if expr_ast.elem_type == InterpreterBase.BOOL_NODE:
            return Value(Type.BOOL, expr_ast.get("val"))
        if expr_ast.elem_type == InterpreterBase.NIL_NODE: 
            return Value(Type.NIL, expr_ast.get("val"))
        if expr_ast.elem_type == InterpreterBase.NEG_NODE:
            operand = self.__eval_expr(expr_ast.get("op1"))
            # Ensure the operand is an integer for negation
            if operand.type() != Type.INT:
                super().error(ErrorType.TYPE_ERROR)
            negated_value = operand.value() * -1
            return Value(Type.INT, negated_value)
        if expr_ast.elem_type == Interpreter.NOT_NODE:
            operand = self.__eval_expr(expr_ast.get("op1"))
            # Ensure the operand is a boolean for negation
            if operand.type() != Type.BOOL:
                super().error(ErrorType.TYPE_ERROR)
            negated_value = not operand.value()
            return Value(Type.BOOL, negated_value)
        if expr_ast.elem_type == InterpreterBase.VAR_NODE:
            var_name = expr_ast.get("name")
            val = None
            for var in reversed(self.env):
                if var.get(var_name) != None:
                    return var.get(var_name)
            if val is None:
                super().error(ErrorType.NAME_ERROR, f"Variable {var_name} not found")
        if expr_ast.elem_type == InterpreterBase.FCALL_NODE:
            return self.__call_func(expr_ast)
        if expr_ast.elem_type in Interpreter.BIN_OPS:
            return self.__eval_op(expr_ast)
        if expr_ast.elem_type in Interpreter.COM_OPS:
            return self.__eval_com(expr_ast)
        if expr_ast.elem_type in Interpreter.LOG_OPS:
            return self.__eval_log(expr_ast)
        if expr_ast.elem_type in Interpreter.EQU_OPS:
            return self.__eval_equ(expr_ast)

    def __eval_op(self, arith_ast):
        left_value_obj = self.__eval_expr(arith_ast.get("op1"))
        right_value_obj = self.__eval_expr(arith_ast.get("op2"))
        if left_value_obj.type() != right_value_obj.type():
            super().error(
                ErrorType.TYPE_ERROR,
                f"Incompatible types for {arith_ast.elem_type} operation",
            )
        if arith_ast.elem_type not in self.op_to_lambda[left_value_obj.type()]:
            super().error(
                ErrorType.TYPE_ERROR,
                f"Incompatible operator {arith_ast.elem_type} for type {left_value_obj.type()}",
            )
        f = self.op_to_lambda[left_value_obj.type()][arith_ast.elem_type]
        return f(left_value_obj, right_value_obj)
    
    def __eval_com(self, arith_ast):
        left_value_obj = self.__eval_expr(arith_ast.get("op1"))
        right_value_obj = self.__eval_expr(arith_ast.get("op2"))

        if left_value_obj.type() != Type.INT:
            super().error(
                ErrorType.TYPE_ERROR,
                f"Incompatible types for {arith_ast.elem_type} operation",
            )
        if right_value_obj.type() != Type.INT:
            super().error(
                ErrorType.TYPE_ERROR,
                f"Incompatible types for {arith_ast.elem_type} operation",
            )
        f = self.op_to_lambda[left_value_obj.type()][arith_ast.elem_type]
        return f(left_value_obj, right_value_obj)
    
    def __eval_log(self, arith_ast):
        left_value_obj = self.__eval_expr(arith_ast.get("op1"))
        right_value_obj = self.__eval_expr(arith_ast.get("op2"))

        if left_value_obj.type() != Type.BOOL:
            super().error(
                ErrorType.TYPE_ERROR,
                f"Incompatible types for {arith_ast.elem_type} operation",
            )
        if right_value_obj.type() != Type.BOOL:
            super().error(
                ErrorType.TYPE_ERROR,
                f"Incompatible types for {arith_ast.elem_type} operation",
            )
        f = self.op_to_lambda[left_value_obj.type()][arith_ast.elem_type]
        return f(left_value_obj, right_value_obj)

    def __eval_equ(self, arith_ast):
        left_value_obj = self.__eval_expr(arith_ast.get("op1"))
        right_value_obj = self.__eval_expr(arith_ast.get("op2"))

        if arith_ast.elem_type == "==":
            if left_value_obj.type() == Type.NIL and right_value_obj.type() == Type.NIL:
                return Value(Type.BOOL, True)
            elif left_value_obj.type() != right_value_obj.type():
                return Value(Type.BOOL, False)
        elif arith_ast.elem_type == "!=":
            if left_value_obj.type() == Type.NIL and right_value_obj.type() == Type.NIL:
                return Value(Type.BOOL, False)
            elif left_value_obj.type() != right_value_obj.type():
                return Value(Type.BOOL, True)
        f = self.op_to_lambda[left_value_obj.type()][arith_ast.elem_type]
        return f(left_value_obj, right_value_obj)

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
        self.op_to_lambda[Type.INT][">"] = lambda x, y: Value(
            Type.BOOL, x.value() > y.value()
        )
        self.op_to_lambda[Type.INT]["<"] = lambda x, y: Value(
            Type.BOOL, x.value() < y.value()
        )
        self.op_to_lambda[Type.INT][">="] = lambda x, y: Value(
            Type.BOOL, x.value() >= y.value()
        )
        self.op_to_lambda[Type.INT]["<="] = lambda x, y: Value(
            Type.BOOL, x.value() <= y.value()
        )
        self.op_to_lambda[Type.INT]["=="] = lambda x, y: Value(
            Type.BOOL, x.value() == y.value()
        )
        self.op_to_lambda[Type.INT]["!="] = lambda x, y: Value(
            Type.BOOL, x.value() != y.value()
        )

        # set up operations on strings
        self.op_to_lambda[Type.STRING]["+"] = lambda x, y: Value(
            x.type(), x.value() + y.value()
        )
        self.op_to_lambda[Type.STRING]["=="] = lambda x, y: Value(
            Type.BOOL, x.value() == y.value()
        )
        self.op_to_lambda[Type.STRING]["!="] = lambda x, y: Value(
            Type.BOOL, x.value() != y.value()
        )

        # set up operations on bools
        self.op_to_lambda[Type.BOOL]["=="] = lambda x, y: Value(
            Type.BOOL, x.value() == y.value()
        )
        self.op_to_lambda[Type.BOOL]["!="] = lambda x, y: Value(
            Type.BOOL, x.value() != y.value()
        )
        self.op_to_lambda[Type.BOOL]["&&"] = lambda x, y: Value(
            Type.BOOL, x.value() and y.value()
        )
        self.op_to_lambda[Type.BOOL]["||"] = lambda x, y: Value(
            Type.BOOL, x.value() or y.value()
        )

        # set up operations on NIL
        self.op_to_lambda[Type.NIL]["=="] = lambda x, y: Value(
            Type.BOOL, x.value() == y.value()
        )
        self.op_to_lambda[Type.NIL]["!="] = lambda x, y: Value(
            Type.BOOL, x.value() != y.value()
        )
        # add other operators here later for int, string, bool, etc