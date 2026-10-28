"""Headless web adapters, bounded analysis execution, and graph presentation."""
import base64
import binascii
import multiprocessing
import json
import colorsys
from math import ceil, cos, sin, sqrt
from pathlib import PurePath

from crntanalysis.orchestrator import CRNAnalysisService, ConsoleReportFormatter, AnalysisReportReader
from web.report_formats import read_report_document
from web.limits import (MAX_INPUT_BYTES, MAX_RESULT_BYTES, MAX_COMPLEXES,
                        MAX_REACTIONS, MAX_RENDER_COMPLEXES, MAX_RENDER_REACTIONS,
                        ANALYSIS_TIMEOUT, WORKER_MEMORY_MB)
COLORS = ('#167d8d', '#ae6235', '#6671bc', '#b34d76', '#559451', '#937545',
          '#3479c0', '#80509b', '#c34c38', '#41877b', '#a57c17', '#526477')


def linkage_color(index):
    """Stable class colors shared by graphs and legends, without a six-color cycle."""
    if index < len(COLORS):
        return COLORS[index]
    rgb = colorsys.hls_to_rgb((index * 0.61803398875) % 1, 0.43, 0.6)
    return '#' + ''.join(f'{round(value * 255):02x}' for value in rgb)


def selected_linkages(value):
    """None means all classes; accept legacy scalar and multi-select values."""
    if not value or value == 'all':
        return None
    values = value if isinstance(value, (list, tuple)) else [value]
    selected = {str(item) for item in values if item != 'all'}
    return selected or None


def toggle_linkage_selection(value, index):
    selected = selected_linkages(value) or set()
    index = str(index)
    if index in selected:
        selected.remove(index)
    else:
        selected.add(index)
    return sorted(selected, key=int)
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
    return _decode_text_upload(contents, filename, {'.react', '.ode', '.txt'}, MAX_INPUT_BYTES)


def decode_saved_upload(contents, filename):
    """Saved structured reports have their own (larger) result-size budget."""
    return _decode_text_upload(contents, filename, {'.analysis', '.output', '.txt', '.txr'}, MAX_RESULT_BYTES)


def _decode_text_upload(contents, filename, extensions, limit):
    if not filename or PurePath(filename).suffix.lower() not in extensions:
        raise ValueError('Upload a supported file: ' + ', '.join(sorted(extensions)) +
                         '.')
    if not isinstance(contents, str) or len(contents) > limit * 2:
        raise ValueError(f'This upload must be at most {limit / 1048576:g} MiB.')
    try:
        raw = base64.b64decode(contents.split(',', 1)[1], validate=True)
        if len(raw) > limit:
            raise ValueError(f'This upload must be at most {limit / 1048576:g} MiB.')
        return raw.decode('utf-8-sig')
    except (binascii.Error, UnicodeDecodeError, IndexError) as error:
        raise ValueError('The upload must be a UTF-8 text model.') from error


def analyze_document(text, input_format='auto', options=(), unresolved='symbolic'):
    """Analyze a model and create JSON-safe output; called inside a child process."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError('Paste a model or upload a file before analyzing.')
    limit = MAX_RESULT_BYTES if input_format == 'saved-result' else MAX_INPUT_BYTES
    if len(text.encode('utf-8')) > limit:
        raise ValueError(f'Input must be at most {limit / 1048576:g} MiB.')
    if input_format == 'saved-result':
        try:
            document = read_report_document(text)
            network = document['network']
            if len(network['complexes']) > MAX_COMPLEXES or len(network['reactions']) > MAX_REACTIONS:
                raise ValueError('Saved network exceeds this deployment\'s analysis limits.')
            outcome = AnalysisReportReader().from_dict(document)
        except (KeyError, TypeError, json.JSONDecodeError) as error:
            raise ValueError(f'Invalid saved analysis report: {error}') from None
    else:
        outcome = CRNAnalysisService().analyze_text(
            text, input_format=input_format, unresolved=unresolved,
            allow_fractional='fractional' in options, lift_rational='lift' in options,
            source='<web input>',
        )
    if len(outcome.network.complexes) > MAX_COMPLEXES or len(outcome.network.reactions) > MAX_REACTIONS:
        raise ValueError(f'This network exceeds the analysis limit of {MAX_COMPLEXES} complexes '
                         f'or {MAX_REACTIONS} reactions. The server administrator can adjust '
                         'CRNT_WEB_MAX_COMPLEXES / CRNT_WEB_MAX_REACTIONS after checking capacity.')
    formatter = ConsoleReportFormatter()
    equations = formatter.equation_systems(outcome)
    payload = {'outcome': outcome.to_dict(), 'report': formatter.format(outcome, equation_systems=equations),
               'equations': equations}
    if len(json.dumps(payload).encode('utf-8')) > MAX_RESULT_BYTES:
        raise ValueError(f'The result exceeds the {MAX_RESULT_BYTES / 1048576:g} MiB browser limit. '
                         'The server administrator can adjust CRNT_WEB_MAX_RESULT_BYTES.')
    return payload


def _analysis_worker(connection, arguments):
    try:
        # Linux deployment containers also enforce a per-analysis address-space
        # limit. macOS uses the timeout; container limits remain recommended.
        import sys
        if sys.platform.startswith('linux'):
            import resource
            memory_bytes = WORKER_MEMORY_MB * 1024**2
            resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
        connection.send((True, analyze_document(*arguments)))
    except Exception as error:
        connection.send((False, f'{type(error).__name__}: {error}'))
    finally:
        connection.close()


class AnalysisRunner:
    """Run each request in a killable process with a fixed wall-clock budget."""

    def __init__(self, timeout=ANALYSIS_TIMEOUT):
        self.timeout = timeout

    def run(self, text, input_format, options, unresolved):
        limit = MAX_RESULT_BYTES if input_format == 'saved-result' else MAX_INPUT_BYTES
        if not isinstance(text, str) or len(text.encode('utf-8')) > limit:
            raise ValueError(f'Input must be text and at most {limit / 1048576:g} MiB.')
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

    def elements(self, payload, mode='reaction', linkage='all', page=1, focus=None):
        return self.view(payload, mode, linkage, page, focus)[0]

    def view(self, payload, mode='reaction', linkage='all', page=1, focus=None):
        """Bound rendering only; never truncate the calculated/downloaded network."""
        if not payload:
            return [], 'Analyze a model to explore its graph.', 1
        outcome = payload['outcome']
        network = outcome['network']
        classes = outcome['deficiency']['linkage_classes']
        selected_classes = selected_linkages(linkage)
        classes_in_view = [item for item in classes if selected_classes is None or str(item['index']) in selected_classes]
        membership = {index: item['index'] for item in classes for index in item['complex_indices']}
        selected = {item['index'] for item in network['complexes']
                    if selected_classes is None or str(membership[item['index']]) in selected_classes}
        if focus:
            try:
                index = int(str(focus).strip().removeprefix('C').removeprefix('c'))
            except ValueError:
                return [], 'Enter a valid complex index such as C123.', 1
            if index not in selected:
                return [], 'That complex is not in the selected linkage class/network.', 1
            neighbors = {index}
            for reaction in network['reactions']:
                source, target = reaction['source_complex'], reaction['target_complex']
                if source == index:
                    neighbors.add(target)
                if target == index:
                    neighbors.add(source)
            selected &= neighbors
        total = len(selected)
        full_linkage = mode == 'linkage'
        pages = 1 if full_linkage else max(1, (total + MAX_RENDER_COMPLEXES - 1) // MAX_RENDER_COMPLEXES)
        try:
            page = min(pages, max(1, int(page or 1)))
        except (ValueError, TypeError, OverflowError):
            page = 1
        start = (page - 1) * MAX_RENDER_COMPLEXES
        if not full_linkage:
            selected = set(sorted(selected)[start:start + MAX_RENDER_COMPLEXES])
        positions = self._separated_positions(selected, classes_in_view)
        class_sizes = {item['index']: item['n'] for item in classes}
        elements = []
        for item in network['complexes']:
            index = item['index']
            if index not in selected:
                continue
            group = membership[index]
            elements.append({'data': {
                'id': f'C{index}', 'label': f'C{index}: {item["label"]}',
                'species': item['species'], 'linkage': f'L{group}',
                'color': linkage_color(group),
                'render_size': 8 if full_linkage and class_sizes[group] > 300 else 28,
                'details': f'C{index}: {item["label"]}\nLinkage class L{group}\nComposition: {item["species"]}',
            }})
            elements[-1]['position'] = positions[index]
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
                                         'color': linkage_color(membership[source]),
                                         'details': details.replace('**', '^')}})
            else:
                pairs.setdefault(tuple(sorted((source, target))), []).append((label, details))
        for (source, target), entries in pairs.items():
            elements.append({'data': {'id': f'L{source}-{target}', 'source': f'C{source}',
                                     'target': f'C{target}',
                                     'color': linkage_color(membership[source]),
                                     'label': ', '.join(x[0] for x in entries[:3]) + (f' (+{len(entries)-3} channels)' if len(entries)>3 else ''),
                                     'details': ('\n\n'.join(x[1] for x in entries[:50]) +
                                                 ('\nAdditional channels are in the full report.' if len(entries)>50 else '')).replace('**', '^')}})
        nodes = [item for item in elements if 'source' not in item['data']]
        edges = [item for item in elements if 'source' in item['data']]
        shown = edges if full_linkage else edges[:MAX_RENDER_REACTIONS]
        if full_linkage:
            count = len({membership[index] for index in selected})
            return nodes + shown, (f'Complete selected linkage graph: {len(nodes)} complexes and {len(shown)} '
                                   f'undirected connections across {count} linkage classes. '
                                   'All selected complexes/connections are shown; colors match the legend. '
                                   'The default separated layout places disconnected classes in distinct regions. '
                                   'Zoom to read labels or select fewer classes for detail.'), 1
        message = f'Graph page {page}/{pages}: {len(nodes)} of {total} selected complexes; {len(shown)} of {len(edges)} within-page edges shown.'
        if pages > 1 or len(shown) < len(edges):
            message += ' Rendering is limited: cross-page/extra edges are hidden. All reactions remain in the calculation and downloads. Use linkage filters or a complex neighborhood.'
        return nodes + shown, message, pages

    @staticmethod
    def _separated_positions(selected, classes):
        """Linear-time, non-overlapping class disks; actual complexes, no boxes."""
        groups = [sorted(selected.intersection(item['complex_indices'])) for item in classes]
        groups = [group for group in groups if group]
        columns = max(1, ceil(sqrt(len(groups))))
        positions = {}
        for group_index, indices in enumerate(groups):
            center_x, center_y = (group_index % columns) * 1000, (group_index // columns) * 1000
            radius = max(65, min(400, 18 * sqrt(len(indices))))
            for index, complex_index in enumerate(indices):
                distance = 0 if len(indices) == 1 else radius * sqrt((index + 0.5) / len(indices))
                angle = index * 2.399963229728653
                positions[complex_index] = {'x': center_x + distance * cos(angle),
                                            'y': center_y + distance * sin(angle)}
        return positions
