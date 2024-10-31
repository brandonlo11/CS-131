from brewparse import parse_program
from intbase import InterpreterBase
from intbase import ErrorType


class Interpreter(InterpreterBase):
    # required constructor
    def __init__(self, console_output=True, inp=None, trace_output=False):
        super().__init__(console_output, inp)   

    def run(self, program):
        ast = parse_program(program) # parse program into AST
        self.map = {}  # dictionary to hold variables
        main_func_node = ast.get('functions') # get the function node for main()
        self.run_func(main_func_node)

    def run_func(self, main_func_node):
        for func_node in main_func_node:
            if func_node.get('name') == 'main': # make sure function is the main() function
                for statement_node in func_node.get('statements'):
                    self.run_statement(statement_node) # run each statement node in the main func node
            else:
                #if we reach here, there is no main function
                super().error(
                    ErrorType.NAME_ERROR,
                    "No main() function was found",
                )
    
    def run_statement(self, statement_node):
        # check for a definition
        if statement_node.elem_type == 'vardef':
            self.do_definition(statement_node)
        # check for an assignement
        elif statement_node.elem_type == '=':
            self.do_assignment(statement_node)
        # check for a function call
        elif statement_node.elem_type == 'fcall':
            self.do_func_call(statement_node)

    def do_definition(self, statement_node):
        name = statement_node.get('name')
        # check if variable has already been declared
        if name in self.map:
            super().error(
                ErrorType.NAME_ERROR,
                f"Variable {name} defined more than once",
            )
        else:
            # default value of zero
            self.map[name] = 0

    def do_assignment(self, statement_node):
        # check that the variable exists
        if statement_node.get('name') not in self.map:
            super().error(
                ErrorType.NAME_ERROR,
                f"Variable {statement_node.get('name')} has not been defined",
            )
        # call evaluate_expression to get assignment value
        value = self.evaluate_expression(statement_node.get('expression'))
        # check that statement node has a name before assigning a value to the variable in map
        if (statement_node.get('name') != None):
                self.map[statement_node.get('name')] = value

    def do_func_call(self, function_node):
        # inputi implementation
        if (function_node.get('name') == 'inputi'):
            args = function_node.get('args')
            # check that there is only one argument passed in
            if len(args) > 1:
                super().error(
                    ErrorType.NAME_ERROR,
                    f"No inputi() function found that takes > 1 parameter",
                )
            # output the argument passed to inputi
            for arg in args:
                super().output(arg.get('val'))
                value = 0
            # get input
            value = int(self.get_input())
            return value
        # print implementation
        elif (function_node.get('name') == 'print'):
            args = function_node.get('args')
            # string to be printed, default empty
            toprint = ""
            # check for the value of the args and convert them to strings
            for arg in args:
                if (arg.elem_type == '+') or (arg.elem_type == '-') or (arg.elem_type == 'var'):
                    toprint += str(self.evaluate_expression(arg))
                elif arg.elem_type == 'int':
                    toprint += str(arg.get('val'))
                elif arg.elem_type == 'string':
                    toprint += arg.get('val')
                elif arg.elem_type == 'fcall':
                    toprint += str(self.do_func_call(arg))
            super().output(toprint)
        else:
            # if we reach here, the function is not print or inputi
            super().error(
                ErrorType.NAME_ERROR,
                f"Function {function_node.get('name')} has not been defined",
            )

    def evaluate_expression(self, expression_node):
        # if the expression node is a value, you can return the value
        if expression_node.get('val') != None:
            return expression_node.get('val')
        # if the elem type is fcall do a fucntion call
        elif expression_node.elem_type == 'fcall':
            return self.do_func_call(expression_node)
        # addition and subtraction implementation
        elif expression_node.elem_type == '+' or expression_node.elem_type == '-':
            # recursively get the values of the operands
            op1 = self.evaluate_expression(expression_node.get('op1'))
            op2 = self.evaluate_expression(expression_node.get('op2'))
            if(type(op1) == int and type(op2) == int):
                if expression_node.elem_type == '+':
                    return op1 + op2
                elif expression_node.elem_type == '-':
                    return op1 - op2
            else:
                # if we reach here the types are not able to be added/subtracted
                super().error(
                    ErrorType.TYPE_ERROR,
                    "Incompatible types for arithmetic operation",
                )
        # variable implementation
        elif expression_node.elem_type == 'var':
            # check if variable has been declared
            if expression_node.get('name') in self.map:
                return self.map[expression_node.get('name')]
            else:
                # if we reach here the variable has not been declared
                super().error(
                    ErrorType.NAME_ERROR,
                    f"Variable {expression_node.get('name')} has not been defined",
                )
        else:
            super().error(ErrorType.NAME_ERROR,f"Invalid Expression",)
