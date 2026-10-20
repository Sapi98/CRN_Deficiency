"""Headless web adapters, bounded analysis execution, and graph presentation."""
import base64
import binascii
import multiprocessing
import json
from pathlib import PurePath

from crntanalysis.orchestrator import CRNAnalysisService, ConsoleReportFormatter

MAX_INPUT_BYTES = 32_000
MAX_COMPLEXES = 500
MAX_REACTIONS = 1500
COLORS = ('#167d8d', '#ae6235', '#6671bc', '#b34d76', '#559451', '#937545')
EXAMPLES = {
    'reaction': ('Reversible conversion', 'react', [],
                 'Reactions:\nA k1-> B\nB k2-> A\n\nRate Constants:\nk1=0.4\nk2=0.2'),
    'rational': ('Shared reciprocal auxiliary', 'ode', ['lift'],
                 'Species:\nx, y\n\nODE Model:\ndx/dt=-k*x/(1+x+y)\ndy/dt=-q*y/(1+x+y)\n\n'
                 'Auxiliary Species:\ns=1/(1+x+y)\n\nCoefficients:\nk=0.4\nq=0.2\n\nInitial Conditions:\nx=1\ny=2'),
    'fractional': ('Fractional power and auxiliary', 'ode', ['lift', 'fractional'],
                   'Species:\nx, y\n\nODE Model:\ndx/dt=-k*x/(1+x)\ndy/dt=-q*y^1.5\n\n'
                   'Auxiliary Species:\ns=1/(1+x)\n\nCoefficients:\nk=0.4\nq=0.2\n\nInitial Conditions:\nx=1\ny=2'),
}


def decode_upload(contents, filename):
    """Decode a single bounded UTF-8 model upload without writing it to disk."""
    if not filename or PurePath(filename).suffix.lower() not in {'.react', '.ode', '.txt'}:
        raise ValueError('Upload one .react, .ode, or .txt model file.')
    if not isinstance(contents, str) or len(contents) > MAX_INPUT_BYTES * 2:
        raise ValueError('Model files must be at most 32 KB.')
    try:
        raw = base64.b64decode(contents.split(',', 1)[1], validate=True)
        if len(raw) > MAX_INPUT_BYTES:
            raise ValueError('Model files must be at most 32 KB.')
        return raw.decode('utf-8-sig')
    except (binascii.Error, UnicodeDecodeError, IndexError) as error:
        raise ValueError('The upload must be a UTF-8 text model.') from error


def analyze_document(text, input_format='auto', options=(), unresolved='symbolic'):
    """Analyze a model and create JSON-safe output; called inside a child process."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError('Paste a model or upload a file before analyzing.')
    if len(text.encode('utf-8')) > MAX_INPUT_BYTES:
        raise ValueError('Models must be at most 32 KB.')
    outcome = CRNAnalysisService().analyze_text(
        text, input_format=input_format, unresolved=unresolved,
        allow_fractional='fractional' in options, lift_rational='lift' in options,
        source='<web input>',
    )
    if len(outcome.network.complexes) > MAX_COMPLEXES or len(outcome.network.reactions) > MAX_REACTIONS:
        raise ValueError('This network exceeds the interactive limit of 500 complexes or 1500 reactions.')
    payload = {'outcome': outcome.to_dict(), 'report': ConsoleReportFormatter().format(outcome)}
    if len(json.dumps(payload).encode('utf-8')) > 1_000_000:
        raise ValueError('The result exceeds the 1 MB browser limit. Use the desktop tool for this model.')
    return payload


def _analysis_worker(connection, arguments):
    try:
        # Linux deployment containers also enforce a per-analysis address-space
        # limit. macOS uses the timeout; container limits remain recommended.
        import sys
        if sys.platform.startswith('linux'):
            import resource
            resource.setrlimit(resource.RLIMIT_AS, (1024**3, 1024**3))
        connection.send((True, analyze_document(*arguments)))
    except Exception as error:
        connection.send((False, f'{type(error).__name__}: {error}'))
    finally:
        connection.close()


class AnalysisRunner:
    """Run each request in a killable process with a fixed wall-clock budget."""

    def __init__(self, timeout=20):
        self.timeout = timeout

    def run(self, text, input_format, options, unresolved):
        if not isinstance(text, str) or len(text.encode('utf-8')) > MAX_INPUT_BYTES:
            raise ValueError('Models must be text and at most 32 KB.')
        context = multiprocessing.get_context('spawn')
        receiver, sender = context.Pipe(duplex=False)
        process = context.Process(target=_analysis_worker,
                                  args=(sender, (text, input_format, options, unresolved)))
        try:
            process.start()
            sender.close()
            if not receiver.poll(self.timeout):
                raise ValueError(f'Analysis exceeded the {self.timeout:g}-second limit. Simplify the model or use the desktop tool.')
            try:
                success, result = receiver.recv()
            except EOFError:
                raise ValueError('Analysis worker stopped; the model may have exceeded its memory budget.') from None
            if not success:
                raise ValueError(result)
            return result
        finally:
            sender.close()
            receiver.close()
            if process.pid is not None:
                if process.is_alive():
                    process.terminate()
                process.join(timeout=2)
                if process.is_alive():
                    process.kill()
                    process.join()
                process.close()


def format_rate(value):
    """Display rates without importing desktop plotting dependencies."""
    if isinstance(value, (int, float)):
        if 0 < abs(value) < 0.001:
            return f'{value:.3e}'
        return f'{value:.3f}'.rstrip('0').rstrip('.')
    return str(value).replace('**', '^')


class GraphPresenter:
    """Map serialized networks to Cytoscape elements and inspectable details."""

    def elements(self, payload, mode='reaction', linkage='all'):
        if not payload:
            return []
        outcome = payload['outcome']
        network = outcome['network']
        classes = outcome['deficiency']['linkage_classes']
        membership = {index: item['index'] for item in classes for index in item['complex_indices']}
        selected = {item['index'] for item in network['complexes']
                    if linkage == 'all' or str(membership[item['index']]) == str(linkage)}
        elements = []
        for item in network['complexes']:
            index = item['index']
            if index not in selected:
                continue
            group = membership[index]
            elements.append({'data': {
                'id': f'C{index}', 'label': f'C{index}: {item["label"]}',
                'species': item['species'], 'linkage': f'L{group}',
                'color': COLORS[group % len(COLORS)],
                'details': f'C{index}: {item["label"]}\nLinkage class L{group}\nComposition: {item["species"]}',
            }})
        pairs = {}
        for reaction in network['reactions']:
            source, target = reaction['source_complex'], reaction['target_complex']
            if source not in selected or target not in selected:
                continue
            label = f'r{reaction["index"]}: {format_rate(reaction.get("weight", reaction["rate_constant"]))}'
            details = (f'r{reaction["index"]}: C{source} → C{target}\n'
                       f'Rate constant: {reaction["rate_constant"]}\n'
                       f'Numeric value: {reaction.get("rate")}\n'
                       f'Rate law: {reaction.get("rate_expression", "source-complex mass action")}')
            if mode == 'reaction':
                elements.append({'data': {'id': f'r{reaction["index"]}', 'source': f'C{source}',
                                         'target': f'C{target}', 'label': label,
                                         'details': details.replace('**', '^')}})
            else:
                pairs.setdefault(tuple(sorted((source, target))), []).append((label, details))
        for (source, target), entries in pairs.items():
            elements.append({'data': {'id': f'L{source}-{target}', 'source': f'C{source}',
                                     'target': f'C{target}', 'label': ', '.join(x[0] for x in entries),
                                     'details': '\n\n'.join(x[1] for x in entries).replace('**', '^')}})
        return elements
