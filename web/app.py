"""Dash application factory and local web launcher."""
import argparse
import json
from pathlib import Path

from crntanalysis import __version__
from web.limits import MAX_REQUEST_BYTES, MAX_INPUT_BYTES
from web.service import AnalysisRunner, EXAMPLES, GraphPresenter, decode_upload


def create_app(runner=None):
    """Create an independent app; no analysis data is held in module globals."""
    from dash import Dash, Input, Output, State, ctx, dcc, html, no_update
    from dash.exceptions import PreventUpdate
    import dash_cytoscape as cyto

    app = Dash(__name__, title='CRNTAnalysis | Network workspace',
               assets_folder=str(Path(__file__).with_name('assets')))
    app.server.config['MAX_CONTENT_LENGTH'] = MAX_REQUEST_BYTES
    analysis = runner or AnalysisRunner()
    presenter = GraphPresenter()

    @app.server.get('/healthz')
    def health():
        return {'status': 'ok'}

    def layout():
        return html.Div([
            dcc.Store(id='result', storage_type='memory'), dcc.Download(id='download'),
            html.Header([html.Div([html.Div('CR / NT', className='brand-mark'),
                                  html.Div([html.H1('CRNTAnalysis'), html.P('A workspace for chemical reaction networks')])], className='brand'),
                         html.Span(f'WEB LAB · v{__version__}', className='badge')]),
            html.Main([
                html.Section([
                    html.P('01 / DEFINE YOUR MODEL', className='eyebrow'),
                    html.H2('From equations to structure.'),
                    html.P('Paste a model or upload a UTF-8 .react / .ode file. Analysis uses the same scientific core as the desktop app.', className='muted'),
                    html.Label('Start with an example'),
                    dcc.Dropdown(id='example', options=[{'label': x[0], 'value': key} for key, x in EXAMPLES.items()],
                                 placeholder='Choose a public example', clearable=False),
                    dcc.Upload(id='upload', children=html.Div(['Drop a model here or ', html.Strong('browse files')]),
                               accept='.react,.ode,.txt', multiple=False, className='upload'),
                    html.Div(id='upload-status', role='status', className='muted'),
                    html.P(f'Maximum model size: {MAX_INPUT_BYTES / 1048576:g} MiB.', className='muted small'),
                    html.Label('Input format'),
                    dcc.Dropdown(id='format', options=[{'label': label, 'value': value} for value, label in
                                 [('auto', 'Detect automatically'), ('react', 'Reaction network'), ('ode', 'ODE system')]],
                                 value='auto', clearable=False),
                    html.Label('Model document'),
                    dcc.Textarea(id='model', value=EXAMPLES['reaction'][3], className='editor',
                                 placeholder='Species:\nx, y\n\nODE Model:\ndx/dt = ...'),
                    dcc.Checklist(id='options', options=[
                        {'label': ' Allow fractional ODE powers (real complexes)', 'value': 'fractional'},
                        {'label': ' Lift rational ODE rates using auxiliary species', 'value': 'lift'}],
                        value=[], className='checks'),
                    html.Label('Unresolved parameters'),
                    dcc.Dropdown(id='unresolved', options=['symbolic', 'strict', 'one'], value='symbolic', clearable=False),
                    html.P('“one” substitutes 1 for unresolved values; symbolic keeps their names.', className='muted small'),
                    html.Button('Analyze network →', id='analyze', n_clicks=0, className='primary'),
                    html.Div(id='status', role='status', **{'aria-live': 'polite'}),
                    html.P('Privacy: models are processed on this server. This app does not write them to disk. Results stay in this tab until refreshed; downloads are explicit.', className='privacy'),
                ], className='card input-panel'),
                html.Section([
                    html.P('02 / EXPLORE THE NETWORK', className='eyebrow'),
                    html.H2('Structure, made visible.'),
                    dcc.Loading(html.Div(id='metrics', className='metrics'), type='circle'),
                    html.Div([
                        html.Div([html.Label('Graph'), dcc.RadioItems(id='mode', options=[{'label': ' Reactions', 'value': 'reaction'},
                                                                                                    {'label': ' Linkage graph', 'value': 'linkage'}], value='reaction', inline=True)]),
                        html.Div([html.Label('Layout'), dcc.Dropdown(id='layout', options=['cose', 'circle', 'breadthfirst', 'grid'], value='cose', clearable=False)]),
                        html.Div([html.Label('Linkage class'), dcc.Dropdown(id='linkage', options=[{'label': 'All classes', 'value': 'all'}], value='all', clearable=False)]),
                    ], className='toolbar'),
                    html.Div([dcc.Input(id='search', placeholder='Highlight a complex or species…', type='search'),
                              dcc.Checklist(id='labels', options=[{'label': ' Show rates', 'value': 'rates'}], value=['rates']),
                              html.Button('Fit graph', id='fit'), html.Button('Download PNG', id='png')], className='graph-actions'),
                    cyto.Cytoscape(id='graph', elements=[], layout={'name': 'cose'}, responsive=True,
                                   style={'width': '100%', 'height': '540px'}, minZoom=0.08, maxZoom=5),
                    html.P('Drag nodes to arrange • scroll to zoom • drag the background to pan • click a node or edge to inspect', className='muted small'),
                    html.Div(id='legend', className='legend'),
                    html.Pre('Select a complex or reaction to inspect it.', id='details', className='details'),
                    html.Details([html.Summary('Linkage-class results'), html.Div(id='classes')], open=True),
                    html.Details([html.Summary('ODEs under consideration'), html.Pre(id='odes', className='report')], open=True),
                    html.Details([html.Summary('Full scientific report & ODEs'), html.Pre(id='report', className='report')], open=True),
                    html.Div([html.Button('Download report (.txt)', id='download-text', disabled=True),
                              html.Button('Download result (.analysis)', id='download-json', disabled=True)], className='graph-actions'),
                ], className='card workspace'),
            ]),
            html.Footer('CRNTAnalysis · Interpret augmented and real-complex realizations using the assumptions recorded in the report.'),
        ], className='shell')

    app.layout = layout

    @app.callback(Output('model', 'value'), Output('format', 'value'), Output('options', 'value'),
                  Output('upload-status', 'children'), Input('example', 'value'), Input('upload', 'contents'),
                  State('upload', 'filename'), prevent_initial_call=True)
    def load_model(example, contents, filename):
        if ctx.triggered_id == 'example' and example in EXAMPLES:
            _, kind, options, text = EXAMPLES[example]
            return text, kind, options, 'Example loaded. Click Analyze network.'
        try:
            text = decode_upload(contents, filename)
            kind = 'ode' if filename.lower().endswith('.ode') else 'react' if filename.lower().endswith('.react') else 'auto'
            return text, kind, [], f'Loaded {filename}. Choose applicable ODE options, then analyze.'
        except ValueError as error:
            return no_update, no_update, no_update, str(error)

    @app.callback(Output('result', 'data'), Output('status', 'children'),
                  Input('analyze', 'n_clicks'), Input('model', 'value'), Input('format', 'value'),
                  Input('options', 'value'), Input('unresolved', 'value'), prevent_initial_call=True,
                  running=[(Output('analyze', 'disabled'), True, False),
                           (Output('analyze', 'children'), 'Analyzing…', 'Analyze network →')])
    def analyze(clicks, text, kind, options, unresolved):
        if ctx.triggered_id != 'analyze':
            return None, 'Input changed. Analyze again to refresh the results.'
        try:
            payload = analysis.run(text, kind, options or [], unresolved)
            return payload, 'Analysis complete. Explore the graph below.'
        except ValueError as error:
            message = (str(error).replace('GUI Model input panel', 'Model input panel')
                       .replace('In the GUI, check', 'In the model panel, check')
                       .replace('at the top of the GUI', 'at the top of the')
                       .replace('Analyze model', 'Analyze network'))
            return None, html.Pre(message, className='error')

    @app.callback(Output('metrics', 'children'), Output('report', 'children'), Output('classes', 'children'),
                  Output('linkage', 'options'), Output('linkage', 'value'), Output('legend', 'children'),
                  Output('download-text', 'disabled'), Output('download-json', 'disabled'), Input('result', 'data'))
    def render_result(payload):
        if not payload:
            return html.P('Your network insights will appear here.', className='muted'), '', '', [{'label': 'All classes', 'value': 'all'}], 'all', [], True, True
        result = payload['outcome']['deficiency']
        metrics = [html.Div([html.Strong(str(result[key])), html.Span(label)], className='metric')
                   for key, label in [('n', 'Complexes'), ('l', 'Linkage classes'), ('s', 'Stoich. rank'), ('deficiency', 'Deficiency δ')]]
        rows = [html.Tr([html.Th(label) for label in ['Class', 'Complexes', 'n', 's', 'δ']])]
        for item in result['linkage_classes']:
            rows.append(html.Tr([html.Td(f'L{item["index"]}'), html.Td(', '.join(f'C{x}' for x in item['complex_indices'])),
                                 html.Td(item['n']), html.Td(item['s']), html.Td(item['deficiency'])]))
        options = [{'label': 'All classes', 'value': 'all'}] + [
            {'label': f'L{x["index"]} · δ={x["deficiency"]}', 'value': str(x['index'])} for x in result['linkage_classes']]
        from web.service import COLORS
        legend = [html.Span(f'L{x["index"]} · δ={x["deficiency"]}', style={'borderColor': COLORS[x['index'] % len(COLORS)]}) for x in result['linkage_classes']]
        return metrics, payload['report'], html.Table(rows), options, 'all', legend, False, False

    @app.callback(Output('odes', 'children'), Input('result', 'data'))
    def render_odes(payload):
        if not payload:
            return 'Analyze a model to display its ODE system.'
        systems = payload.get('equations', {})
        lines = []
        if systems.get('original'):
            lines.append('Original ODE system')
            lines.extend(f'd{name}/dt = {rhs}' for name, rhs in systems['original'].items())
            lines.extend(['', 'Analyzed ODE system (including auxiliary species)'])
        else:
            lines.append('ODE system implied by the reaction network')
        lines.extend(f'd{name}/dt = {rhs}' for name, rhs in systems.get('analyzed', {}).items())
        return '\n'.join(lines).replace('**', '^')

    @app.callback(Output('graph', 'elements'), Input('result', 'data'), Input('mode', 'value'), Input('linkage', 'value'))
    def graph_elements(payload, mode, linkage):
        return presenter.elements(payload, mode, linkage)

    @app.callback(Output('graph', 'layout'), Input('layout', 'value'), Input('fit', 'n_clicks'), Input('graph', 'elements'))
    def graph_layout(name, clicks, elements):
        return {'name': name, 'fit': True, 'padding': 45, 'animate': False, 'nodeRepulsion': 12000}

    @app.callback(Output('graph', 'stylesheet'), Input('mode', 'value'), Input('labels', 'value'), Input('search', 'value'), Input('graph', 'elements'))
    def graph_style(mode, labels, search, elements):
        styles = [
            {'selector': 'node', 'style': {'label': 'data(label)', 'background-color': 'data(color)', 'color': '#143645',
                                           'font-size': 9, 'text-valign': 'bottom', 'text-margin-y': 5, 'width': 28, 'height': 28}},
            {'selector': 'edge', 'style': {'curve-style': 'bezier', 'line-color': '#9babb3', 'target-arrow-color': '#9babb3',
                                           'target-arrow-shape': 'triangle' if mode == 'reaction' else 'none', 'width': 2,
                                           'label': 'data(label)' if 'rates' in (labels or []) else '',
                                           'font-size': 7, 'text-background-color': '#fff', 'text-background-opacity': 0.9,
                                           'text-background-padding': 2, 'text-rotation': 'autorotate'}},
            {'selector': ':selected', 'style': {'border-width': 4, 'border-color': '#e7a84a', 'line-color': '#e7a84a', 'target-arrow-color': '#e7a84a'}},
        ]
        if search:
            for element in elements or []:
                data = element['data']
                if 'source' not in data and search.casefold() in data['label'].casefold():
                    styles.append({'selector': f'node[id = "{data["id"]}"]', 'style': {'border-width': 5, 'border-color': '#e7a84a'}})
        return styles

    @app.callback(Output('details', 'children'), Input('graph', 'tapNodeData'), Input('graph', 'tapEdgeData'), Input('result', 'data'))
    def inspect(node, edge, payload):
        if ctx.triggered_id == 'result':
            return 'Select a complex or reaction to inspect it.'
        data = edge if ctx.triggered[0]['prop_id'].endswith('tapEdgeData') else node
        return data.get('details', '') if data else 'Select a complex or reaction to inspect it.'

    @app.callback(Output('graph', 'generateImage'), Input('png', 'n_clicks'), prevent_initial_call=True)
    def image(clicks):
        return {'type': 'png', 'action': 'download', 'filename': 'crntanalysis-network', 'options': {'bg': '#ffffff', 'scale': 2}}

    @app.callback(Output('download', 'data'), Input('download-text', 'n_clicks'), Input('download-json', 'n_clicks'),
                  State('result', 'data'), prevent_initial_call=True)
    def download(text_clicks, json_clicks, payload):
        if not payload:
            raise PreventUpdate
        if ctx.triggered_id == 'download-text':
            return {'content': payload['report'] + '\n', 'filename': 'network_analysis.txt', 'type': 'text/plain'}
        return {'content': json.dumps(payload['outcome'], indent=2), 'filename': 'network.analysis', 'type': 'application/json'}

    return app


def main():
    parser = argparse.ArgumentParser(description='Run the CRNTAnalysis browser workspace.')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8050)
    args = parser.parse_args()
    create_app().run(host=args.host, port=args.port, debug=False)


if __name__ == '__main__':
    main()
