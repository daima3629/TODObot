class ArgParser:
    def __init__(self, args: tuple):
        self.baseargs = args
        self.args = []
        self.options = {}
        self.parse()
    
    def parse(self):
        for arg in self.baseargs:
            if arg.startswith("--"):
                arg = arg.split("=")
                key = arg[0][2:]
                if len(arg) == 2:
                    value = arg[1]
                else:
                    value = "true"
                self.options[key] = value
                continue
            self.args.append(arg)