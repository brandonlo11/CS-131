# The EnvironmentManager class keeps a mapping between each variable name (aka symbol)
# in a brewin program and the Value object, which stores a type, and a value.
class VariableEntry:
    def __init__(self, value=None, expr_ast=None, is_evaluated=False, captured_env=None):
        self.value = value          # The evaluated value (Value object)
        self.expr_ast = expr_ast    # The unevaluated expression (AST node)
        self.is_evaluated = is_evaluated  # Boolean flag indicating if evaluated
        self.captured_env = captured_env  # Captured environment (list of scopes)

class EnvironmentManager:
    def __init__(self):
        self.environment = []
    
    def copy_current_env(self):
        # Deep copy the current environment
        import copy
        return copy.deepcopy(self.environment)

    @staticmethod
    def from_captured_env(captured_env):
        env_manager = EnvironmentManager()
        env_manager.environment = captured_env
        return env_manager

    # returns a VariableDef object
    def get(self, symbol):
        cur_func_env = self.environment[-1]
        for env in reversed(cur_func_env):
            if symbol in env:
                var_entry = env[symbol]
                return var_entry  # Return the VariableEntry object
        return None

    def set(self, symbol, var_entry):
        cur_func_env = self.environment[-1]
        for env in reversed(cur_func_env):
            if symbol in env:
                env[symbol] = var_entry  # Store the VariableEntry object
                return True
        return False

    # create a new symbol in the top-most environment, regardless of whether that symbol exists
    # in a lower environment
    def create(self, symbol, var_entry):
        cur_func_env = self.environment[-1]
        if symbol in cur_func_env[-1]:   # symbol already defined in current scope
            return False
        cur_func_env[-1][symbol] = var_entry
        return True

    # used when we enter a new function - start with empty dictionary to hold parameters.
    def push_func(self):
        self.environment.append([{}])  # [[...]] -> [[...], [{}]]

    def push_block(self):
        cur_func_env = self.environment[-1]
        cur_func_env.append({})  # [[...],[{....}] -> [[...],[{...}, {}]]

    def pop_block(self):
        cur_func_env = self.environment[-1]
        cur_func_env.pop() 

    # used when we exit a nested block to discard the environment for that block
    def pop_func(self):
        self.environment.pop()

