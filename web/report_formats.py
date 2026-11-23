"""Download formats and safe import of current/older human-readable reports."""
import ast
import json
import math
import re

from crntanalysis.crn_models import Complex, Reaction, ReactionNetwork
from crntanalysis.graph_utils import ReactionGraphBuilder
from crntanalysis.orchestrator import AnalysisReportWriter
from crntanalysis.parser_policies import SymbolicValuePolicy
from crntanalysis.reaction_parser import ComplexParser

BEGIN_DATA = '--- BEGIN CRNTANALYSIS STRUCTURED RESULT JSON ---'
END_DATA = '--- END CRNTANALYSIS STRUCTURED RESULT JSON ---'


def build_download(payload, extension):
    """TXT is readable plus restorable data; ANALYSIS/OUTPUT are compact JSON."""
    if extension not in {'txt', 'analysis', 'output'}:
        raise ValueError('Choose txt, analysis, or output.')
    serialized = json.dumps(payload['outcome'], ensure_ascii=False, separators=(',', ':'))
    if extension == 'txt':
        content = payload['report'] + '\n\n' + BEGIN_DATA + '\n' + serialized + '\n' + END_DATA + '\n'
    else:
        content = serialized
    stem = AnalysisReportWriter._default_stem(payload['outcome'].get('input', {}).get('source'))
    return {'content': content, 'filename': f'{stem}.{extension}',
            'type': 'text/plain' if extension == 'txt' else 'application/json'}


def read_report_document(text):
    """Read JSON, embedded lossless JSON, or a complete older detailed report."""
    text = text.lstrip('\ufeff')
    if text.lstrip().startswith(('{', '[')):
        return json.loads(text)
    normalized = '\n' + text.replace('\r\n', '\n')
    marker = '\n' + BEGIN_DATA + '\n'
    if marker in normalized:
        _, _, structured = normalized.rpartition(marker)
        end_marker = '\n' + END_DATA
        if end_marker not in structured:
            raise ValueError('The saved text report is incomplete: missing structured-data end marker.')
        data, _, trailing = structured.partition(end_marker)
        if trailing.strip():
            raise ValueError('Unexpected content after the saved report data.')
        return json.loads(data)
    try:
        return _read_legacy_text(text)
    except (SyntaxError, TypeError, KeyError) as error:
        raise ValueError(f'Invalid detailed text report: {error}') from None


def _read_legacy_text(text):
    """Reconstruct only complete older CRNTAnalysis reports, never arbitrary text."""
    if not text.startswith('Chemical Reaction Network Deficiency Analysis'):
        raise ValueError('This is not a saved CRNTAnalysis report. Open a complete report or a structured .analysis/.output file.')
    headings = {'Whole network', 'Network details', 'Indexed complexes', 'Reactions and rates',
                'Parameters / rate constants', 'Stoichiometric coefficients', 'Initial conditions',
                'Original ODE system', 'ODE system used for network construction (including auxiliaries)',
                'ODE system implied by the reaction network', 'Auxiliary definitions and derived ODEs', 'Warnings'}
    sections, current = {}, None
    kind, source = 'react', None
    for line in text.splitlines():
        if line.startswith('Format:'):
            kind = line.split(':', 1)[1].strip()
        if line.startswith('Input:'):
            source = line.split(':', 1)[1].strip()
        if line in headings:
            current = line
            sections.setdefault(current, [])
        elif line.startswith(' ') and current:
            sections[current].append(line)
        elif line.strip():
            current = None
    if 'Indexed complexes' not in sections or 'Reactions and rates' not in sections:
        raise ValueError('This older summary lacks indexed complexes/reaction details and cannot restore the network. Use .analysis/.output or a new TXT download.')

    def assignments(heading):
        result = {}
        for line in sections.get(heading, []):
            name, separator, raw = line.strip().partition(' = ')
            if not separator:
                raise ValueError(f'Incomplete {heading} in text report.')
            value = float(raw)
            if not math.isfinite(value):
                raise ValueError('Nonfinite parameter in saved report.')
            result[name] = value
        return result

    rates = assignments('Parameters / rate constants')
    coefficients = assignments('Stoichiometric coefficients')
    parser = ComplexParser(SymbolicValuePolicy())
    complexes = []
    for line in sections['Indexed complexes']:
        match = re.fullmatch(r'\s*C(\d+): (.+)', line)
        if not match:
            raise ValueError('Incomplete complex entry in text report.')
        index, label = int(match[1]), match[2]
        complexes.append(Complex(index, label, parser.parse(label, coefficients, 1)))
    reactions, current_reaction = [], None
    for line in sections['Reactions and rates']:
        match = re.fullmatch(r'\s*r(\d+): C(\d+) \(.*\) -> C(\d+) \(.*\); rate constant = (.*); weight = (.*)', line)
        if match:
            current_reaction = {'index': int(match[1]), 'source_complex': int(match[2]),
                                'target_complex': int(match[3]), 'rate_constant': match[4].replace('^', '**')}
            try:
                rate = float(match[5])
            except ValueError:
                rate = None
            if rate is not None and not math.isfinite(rate):
                raise ValueError('Nonfinite rate in text report.')
            current_reaction['rate'] = rate
            reactions.append(current_reaction)
        elif current_reaction is not None and line.strip().startswith('Rate law: '):
            current_reaction['rate_expression'] = line.strip()[10:].replace('^', '**')
        elif current_reaction is not None and line.strip().startswith('Kinetic orders: '):
            orders = ast.literal_eval(line.strip()[16:])
            if not isinstance(orders, dict):
                raise ValueError('Invalid kinetic orders in text report.')
            current_reaction['kinetic_orders'] = orders
        else:
            raise ValueError('Incomplete reaction details in text report.')
    if len({c.index for c in complexes}) != len(complexes) or len({r['index'] for r in reactions}) != len(reactions):
        raise ValueError('Duplicate indices in text report.')
    expected_n = next((int(line.split('=')[1]) for line in sections.get('Whole network', []) if line.strip().startswith('n =')), None)
    expected_reactions = next((int(line.split(':')[1]) for line in sections.get('Network details', []) if line.strip().startswith('Reaction count:')), None)
    if expected_n != len(complexes) or expected_reactions is None or expected_reactions != len(reactions):
        raise ValueError('The text report is incomplete or has inconsistent network counts.')
    edges = [Reaction(**reaction) for reaction in reactions]
    graph, adjacency = ReactionGraphBuilder().build(complexes, edges)
    metadata = {}
    for heading, key in [('Original ODE system', 'original_equations'),
                         ('ODE system used for network construction (including auxiliaries)', 'transformed_equations')]:
        if heading in sections:
            metadata[key] = {}
            for line in sections[heading]:
                match = re.fullmatch(r'\s*d([A-Za-z_]\w*)/dt = (.+)', line)
                if not match:
                    raise ValueError('Incomplete ODE in text report.')
                metadata[key][match[1]] = match[2].replace('^', '**')
    auxiliaries, auxiliary = [], None
    for line in sections.get('Auxiliary definitions and derived ODEs', []):
        if line.startswith('  ') and not line.startswith('    '):
            name, _, definition = line.strip().partition(' = ')
            auxiliary = {'species': name, 'definition': definition.replace('^', '**')}
            auxiliaries.append(auxiliary)
        elif auxiliary is not None:
            raw = line.strip()
            if raw.startswith(f'd{auxiliary["species"]}/dt = '):
                auxiliary['derivative'] = raw.partition(' = ')[2].replace('^', '**')
            else:
                name, _, value = raw.partition(': ')
                keys = {'Dependencies': 'dependencies', 'Constraint': 'constraint', 'Domain': 'domain',
                        'Initial expression': 'initial_expression', 'Initial value': 'initial_value',
                        'Chain rule verified': 'chain_rule_verified'}
                if name in keys:
                    if name in {'Dependencies', 'Chain rule verified'}:
                        value = ast.literal_eval(value)
                    elif name == 'Initial value':
                        value = None if value == 'unresolved' else float(value)
                    else:
                        value = value.replace('^', '**')
                    auxiliary[keys[name]] = value
    if auxiliaries:
        if any('derivative' not in item for item in auxiliaries):
            raise ValueError('Incomplete auxiliary equations in text report.')
        metadata['auxiliary_species'] = auxiliaries
    network = ReactionNetwork(edges, complexes, graph, adjacency, rates, coefficients,
                              assignments('Initial conditions'), metadata)
    warnings = [line.strip()[2:] for line in sections.get('Warnings', []) if line.strip().startswith('- ')]
    warnings.append('Imported from an older human-readable report; fields not present in that file cannot be recovered. New TXT downloads include lossless structured data.')
    return {'input': {'format': kind, 'source': source}, 'network': network.to_dict(), 'warnings': warnings}
