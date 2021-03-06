import sys, ast


config = dict(
    before            = None,
    after             = None,
    condition         = False,
    ignore_exceptions = False,
)


def error(err, abort = True):
    message = str(err)

    if isinstance(err, Exception):
        message = type(err).__name__ + ": " + message

    sys.stderr.write(message + '\n')

    if abort:
        sys.exit(1)


class Context(dict):
    "Global dictionary for eval(). Imports modules lazily."

    def __missing__(self, key):
        return __import__(key)


class NameCollector(ast.NodeVisitor):
    "AST walker that detects identifiers. Used to auto-detect input mode."

    def visit_Name(self, node):
        self.names.add(node.id)
        super(NameCollector, self).generic_visit(node)

    def detect(self, expr):
        self.names = set()
        self.visit(expr)
        return self.names


def collect_variable_names(expr):
    try:
        return NameCollector().detect(ast.parse(expr))

    except SyntaxError:
        error("SyntaxError: " + expr)


def evaluate(expr, context):
    try:
        return eval(expr, context)

    except Exception as e:
        error(e, abort = not config['ignore_exceptions'])


def execute(expr, stream):
    # Input hanlding mode is auto-detected from variables used in expression
    names   = collect_variable_names(expr)
    special = names.intersection({'line', 'lines', 'input'})

    if len(special) > 1:
        error("Only one of 'line', 'lines' and 'input' can be used")


    context = Context()
    context.update(__builtins__)

    if len(special) == 0: # ignore input stream
        yield evaluate(expr, context)
        return

    mode = special.pop()

    if mode == 'input':
        context['input'] = stream.read()
        yield evaluate(expr, context)

    elif mode == 'lines':
        context['lines'] = stream.read().split('\n')
        yield evaluate(expr, context)

    elif mode == 'line':
        for line in stream:
            context['line'] = line[:-1]
            yield evaluate(expr, context)
