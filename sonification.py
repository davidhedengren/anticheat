"""Observe the original engine's scheduled sounds without changing its rules.

The vendor source is byte-for-byte v2.10. Only append arguments in sonify are
wrapped, returning the exact original tuple and collecting playback metadata.
ContextVar isolates simultaneous requests. No scoring or scheduling is copied.
A compatibility fix zero-pads both render tracks before their final mix; the
original can crash when a late sound extends beyond its planned canvas.
"""
import ast
import contextvars
import inspect
from vendor import engine

_events = contextvars.ContextVar('scheduled_events', default=None)

def capture(event, kind, word):
    events = _events.get()
    if events is not None:
        events.append({'time': float(event[0]), 'kind': kind, 'word': int(word),
                       'duration': len(event[1]) / engine.SR})
    return event

class Observe(ast.NodeTransformer):
    def visit_Assign(self, node):
        self.generic_visit(node)
        if (len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == 'y'
                and ast.unparse(node.value) == 'indicator_y + time_marker_y'):
            padding = ast.parse('n = max(len(indicator_y), len(time_marker_y))\nindicator_y = np.pad(indicator_y, (0, n - len(indicator_y)))\ntime_marker_y = np.pad(time_marker_y, (0, n - len(time_marker_y)))').body
            return padding + [node]
        return node

    def visit_Call(self, node):
        self.generic_visit(node)
        if not (isinstance(node.func, ast.Attribute) and node.func.attr == 'append'
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id in ('indicator_events', 'time_marker_events')):
            return node
        if node.func.value.id == 'time_marker_events':
            kind, word = 'tick', 'marker_word'
        else:
            source = ast.unparse(node.args[0])
            kinds = {'phrase_pair': 'pair', 'bell': 'triad', 'density_alarm': 'density',
                     'extreme_wow': 'wow', 'hit_sound': 'contrast'}
            matches = [value for key, value in kinds.items() if key in source]
            if len(matches) != 1:
                raise RuntimeError('Unknown engine sound: update observer for new engine version')
            kind = matches[0]
            word = 'running_word' if kind == 'contrast' else 'widx'
        node.args[0] = ast.Call(func=ast.Name(id='_capture', ctx=ast.Load()),
                               args=[node.args[0], ast.Constant(kind), ast.Name(id=word, ctx=ast.Load())],
                               keywords=[])
        return node

_tree = ast.fix_missing_locations(Observe().visit(ast.parse(inspect.getsource(engine.sonify))))
_namespace = dict(vars(engine), _capture=capture)
exec(compile(_tree, '<observed sonify v2.10>', 'exec'), _namespace)
_observed = _namespace['sonify']

def sonify(text, output):
    events = []
    token = _events.set(events)
    try:
        info = _observed(text, 'sv', output)
        return info, sorted(events, key=lambda event: event['time'])
    finally:
        _events.reset(token)
