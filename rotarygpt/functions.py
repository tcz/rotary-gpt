import logging


class FunctionManager:
    def __init__(self):
        self.functions = dict()

    def register(self, function):
        self.functions[function['name']] = function
        logging.debug(f'Registered function {function["name"]}')

    def available_functions(self):
        return [
            {
                'name': function['name'],
                'description': function['description'],
                'parameters': function['parameters']
            }
            for function in self.functions.values()
        ]

    def call(self, name, params):
        if name not in self.functions:
            return f'Function with name {name} not found.'
        return self.functions[name]['callable'](params)