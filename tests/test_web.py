"""Scientific adapters, process isolation, and optional Dash HTTP integration."""
import base64
from importlib.util import find_spec
import unittest
import runpy
from pathlib import Path
from unittest.mock import patch
import os
from web.limits import MAX_INPUT_BYTES

from web.service import (AnalysisRunner, EXAMPLES, GraphPresenter,
                                     analyze_document, decode_upload, linkage_color, toggle_linkage_selection)


class WebServiceTests(unittest.TestCase):
    def test_multiselect_class_filter_and_toggle_semantics(self):
        payload = analyze_document('Reactions:\nA k1-> B\nC k2-> D\nE k3-> F', 'react')
        selected = toggle_linkage_selection([], '0')
        self.assertEqual(selected, ['0'])
        selected = toggle_linkage_selection(selected, '2')
        self.assertEqual(selected, ['0', '2'])
        elements = GraphPresenter().elements(payload, mode='linkage', linkage=selected)
        colors = {x['data']['color'] for x in elements}
        self.assertEqual(colors, {linkage_color(0), linkage_color(2)})
        self.assertEqual(len([x for x in elements if 'source' not in x['data']]), 4)
        selected = toggle_linkage_selection(selected, '0')
        self.assertEqual(selected, ['2'])
        self.assertEqual(toggle_linkage_selection(selected, '2'), [])
        self.assertEqual(len(GraphPresenter().elements(payload, linkage=[])), 9)

    def test_large_linkage_overview_shows_all_nine_distinct_classes(self):
        text = 'Reactions:\n' + '\n'.join(f'X{i} k{i}-> X{i+1}' for i in range(310))
        text += '\n' + '\n'.join(f'A{i} q{i}-> B{i}' for i in range(8))
        payload = analyze_document(text, 'react')
        self.assertEqual(payload['outcome']['deficiency']['l'], 9)
        overview, message, pages = GraphPresenter().view(payload, mode='linkage')
        self.assertEqual(len(overview), 9)
        self.assertEqual(len({x['data']['color'] for x in overview}), 9)
        self.assertTrue(all(x['data']['kind'] == 'linkage-class' for x in overview))
        self.assertIn('9 of 9 classes', message)
        self.assertIn('NOT one complex', message)
        detail = GraphPresenter().elements(payload, mode='linkage', linkage='1')
        self.assertEqual(len(detail), 3)
        self.assertTrue(all(x['data']['color'] == linkage_color(1) for x in detail))
        self.assertEqual(len(payload['outcome']['network']['complexes']), 327)

    def test_large_network_analysis_is_complete_but_graph_is_paged(self):
        count = 420
        text = 'Reactions:\n' + '\n'.join(f'X{i} k{i}-> X{i+1}' for i in range(count))
        payload = analyze_document(text, 'react')
        self.assertEqual(len(payload['outcome']['network']['reactions']), count)

        self.assertEqual(payload['outcome']['deficiency']['n'], count+1)
        presenter = GraphPresenter()
        first, message, pages = presenter.view(payload)
        self.assertEqual(pages, 2)
        self.assertIn('All reactions remain', message)
        self.assertEqual(len([x for x in first if 'source' not in x['data']]), 300)
        last = presenter.elements(payload, page=2)
        self.assertEqual(len([x for x in last if 'source' not in x['data']]), 121)
        focused = presenter.elements(payload, focus='C310')
        self.assertEqual({x['data']['id'] for x in focused if 'source' not in x['data']},
                         {'C309', 'C310', 'C311'})
        self.assertEqual(len(payload['outcome']['network']['reactions']), count)
    def test_graph_edge_cap_is_explicit_and_does_not_mutate_network(self):
        payload = analyze_document('Reactions:\nA k-> B', 'react')
        reaction = payload['outcome']['network']['reactions'][0]
        payload['outcome']['network']['reactions'] = [dict(reaction, index=i) for i in range(1200)]
        elements, message, pages = GraphPresenter().view(payload)
        self.assertEqual(sum('source' in x['data'] for x in elements), 1000)
        self.assertIn('1000 of 1200', message)
        self.assertEqual(len(payload['outcome']['network']['reactions']), 1200)

    def test_reaction_input_report_includes_its_ode_system(self):
        payload = analyze_document(EXAMPLES['reaction'][3], 'react')
        self.assertIn('ODE system implied by the reaction network', payload['report'])
        self.assertIn('dA/dt = -A*k1 + B*k2', payload['report'])
        self.assertEqual(set(payload['equations']['analyzed']), {'A', 'B'})

    def test_pip_package_excludes_web_app_and_dependencies(self):
        root = Path(__file__).resolve().parents[1]
        with patch('setuptools.setup') as setup:
            runpy.run_path(str(root / 'setup.py'))
        metadata = setup.call_args.kwargs
        self.assertFalse(any(name == 'web' or name.startswith(('web.', 'crntanalysis.web'))
                             for name in metadata['packages']))
        self.assertNotIn('web', metadata['extras_require'])
        self.assertFalse(any('dash' in item.lower() for item in metadata['install_requires']))
        self.assertFalse(any('crntanalysis-web' in item
                             for entries in metadata['entry_points'].values() for item in entries))

    def test_public_examples_use_existing_analysis_and_reports(self):
        for key, (_, kind, options, text) in EXAMPLES.items():
            with self.subTest(example=key):
                payload = analyze_document(text, kind, options)
                self.assertIn('Whole network', payload['report'])
                self.assertIn('Indexed complexes', payload['report'])
                elements = GraphPresenter().elements(payload)
                nodes = [x for x in elements if 'source' not in x['data']]
                self.assertEqual(len(nodes), payload['outcome']['deficiency']['n'])

    def test_parallel_reactions_and_reverse_paths_remain_inspectable(self):
        payload = analyze_document('Reactions:\nA k1-> B\nA k2-> B\nB k3-> A', 'react')
        directed = GraphPresenter().elements(payload)
        edges = [x['data'] for x in directed if 'source' in x['data']]
        self.assertEqual(len(edges), 3)
        self.assertEqual(len({x['id'] for x in edges}), 3)
        linkage = [x['data'] for x in GraphPresenter().elements(payload, 'linkage') if 'source' in x['data']]
        self.assertEqual(len(linkage), 1)
        self.assertIn('k1', linkage[0]['label'])
        self.assertIn('k3', linkage[0]['label'])

    def test_linkage_filter_retains_only_its_endpoints(self):
        payload = analyze_document('Reactions:\nA k1-> B\nC k2-> D', 'react')
        elements = GraphPresenter().elements(payload, linkage='0')
        nodes = {x['data']['id'] for x in elements if 'source' not in x['data']}
        self.assertEqual(len(nodes), 2)
        self.assertTrue(all(x['data']['source'] in nodes and x['data']['target'] in nodes
                            for x in elements if 'source' in x['data']))

    def test_upload_validation_and_size_limits(self):
        text = 'Reactions:\nA k-> B'
        encoded = 'data:text/plain;base64,' + base64.b64encode(text.encode()).decode()
        self.assertEqual(decode_upload(encoded, 'model.react'), text)
        for content, filename in ((encoded, 'model.exe'), ('bad', 'a.ode'),
                                  ('x'*64001, 'a.ode')):
            with self.subTest(filename=filename), self.assertRaises(ValueError):
                decode_upload(content, filename)
        with self.assertRaises(ValueError):
            analyze_document('x'*(MAX_INPUT_BYTES + 1))
        with self.assertRaises(ValueError):
            analyze_document('')

    def test_valid_model_larger_than_old_32kb_limit(self):
        text = 'Reactions:\nA k-> B\n#' + 'example padding ' * 3000
        self.assertGreater(len(text.encode()), 32_000)
        encoded = 'data:text/plain;base64,' + base64.b64encode(text.encode()).decode()
        self.assertEqual(decode_upload(encoded, 'large.txt'), text)
        payload = AnalysisRunner(timeout=10).run(text, 'react', [], 'symbolic')
        self.assertEqual(payload['outcome']['deficiency']['n'], 2)

    def test_oversize_upload_counts_utf8_bytes(self):
        text = '#' + '\u03b1' * (MAX_INPUT_BYTES // 2 + 1)
        encoded = 'data:text/plain;base64,' + base64.b64encode(text.encode()).decode()
        with self.assertRaisesRegex(ValueError, 'MiB'):
            decode_upload(encoded, 'large.txt')

    def test_configurable_limits_and_http_overhead(self):
        path = Path(__file__).resolve().parents[1] / 'web' / 'limits.py'
        environment = {'CRNT_WEB_MAX_INPUT_BYTES': '2097152',
                       'CRNT_WEB_MAX_RESULT_BYTES': '16777216',
                       'CRNT_WEB_MAX_COMPLEXES': '1000', 'CRNT_WEB_MAX_REACTIONS': '3000',
                       'CRNT_WEB_TIMEOUT_SECONDS': '60'}
        with patch.dict(os.environ, environment, clear=True):
            limits = runpy.run_path(str(path))
        self.assertEqual(limits['MAX_INPUT_BYTES'], 2097152)
        self.assertEqual(limits['MAX_REQUEST_BYTES'], 3 * 16777216)
        self.assertEqual(limits['ANALYSIS_TIMEOUT'], 60)
        for values in ({'CRNT_WEB_MAX_INPUT_BYTES': 'bad'},
                       {'CRNT_WEB_MAX_INPUT_BYTES': '0'},
                       {'CRNT_WEB_MAX_REQUEST_BYTES': '10'}):
            with self.subTest(values=values), patch.dict(os.environ, values, clear=True), self.assertRaises(ValueError):
                runpy.run_path(str(path))

    def test_worker_result_and_errors_cross_process_boundary(self):
        runner = AnalysisRunner(timeout=10)
        payload = runner.run(EXAMPLES['reaction'][3], 'react', [], 'symbolic')
        self.assertEqual(payload['outcome']['deficiency']['deficiency'], 0)
        with self.assertRaisesRegex(ValueError, 'ParseError'):
            runner.run('not a reaction', 'react', [], 'symbolic')

    def test_timeout_terminates_analysis(self):
        with self.assertRaisesRegex(ValueError, 'limit'):
            AnalysisRunner(timeout=0).run(EXAMPLES['reaction'][3], 'react', [], 'symbolic')


@unittest.skipUnless(find_spec('dash') and find_spec('dash_cytoscape'), 'optional web dependencies')
class WebAppTests(unittest.TestCase):
    def test_clickable_legend_add_remove_and_reset_http_callbacks(self):
        import json
        pattern = json.dumps({'index': ['ALL'], 'type': 'linkage-toggle'}, separators=(',', ':'), sort_keys=True)
        target = json.dumps({'index': '2', 'type': 'linkage-toggle'}, separators=(',', ':'), sort_keys=True)
        values = {pattern + '.n_clicks': [0, 0, 1], 'linkage.value': ['0'], 'mode.value': 'linkage'}
        response = self.post_callback('linkage.value@', values, target + '.n_clicks')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['response']['linkage']['value'], ['0', '2'])
        values['linkage.value'] = ['0', '2']
        response = self.post_callback('linkage.value@', values, target + '.n_clicks')
        self.assertEqual(response.get_json()['response']['linkage']['value'], ['0'])
        response = self.post_callback('linkage.value@', {'linkage-all.n_clicks': 1}, 'linkage-all.n_clicks')
        self.assertEqual(response.get_json()['response']['linkage']['value'], [])
        payload = analyze_document('Reactions:\nA k1-> B\nC k2-> D', 'react')
        response = self.post_callback('legend.children', {'result.data': payload, 'linkage.value': ['1']}, 'linkage.value')
        buttons = response.get_json()['response']['legend']['children']
        self.assertEqual(buttons[0]['props']['aria-pressed'], 'false')
        self.assertEqual(buttons[1]['props']['aria-pressed'], 'true')

    def test_linkage_class_click_and_color_styles(self):
        response = self.post_callback('linkage.value@', {
            'graph.tapNodeData': {'kind': 'linkage-class', 'linkage_index': '8'},
            'mode.value': 'linkage'}, 'graph.tapNodeData')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['response']['linkage']['value'], ['8'])
        response = self.post_callback('graph.stylesheet', {
            'mode.value': 'linkage', 'labels.value': [], 'search.value': '',
            'graph.elements': []}, 'mode.value')
        styles = {x['selector']: x['style'] for x in response.get_json()['response']['graph']['stylesheet']}
        self.assertEqual(styles['edge']['line-color'], 'data(color)')
        response = self.post_callback('graph.layout', {
            'layout.value': 'cose', 'fit.n_clicks': 0,
            'graph.elements': [{'data': {'kind': 'linkage-class', 'id': 'LC0'}}]}, 'graph.elements')
        self.assertEqual(response.get_json()['response']['graph']['layout']['name'], 'grid')

    def test_graph_labels_use_compact_fonts(self):
        response = self.post_callback('graph.stylesheet', {
            'mode.value': 'reaction', 'labels.value': ['rates'],
            'search.value': '', 'graph.elements': [],
        }, 'mode.value')
        self.assertEqual(response.status_code, 200)
        styles = response.get_json()['response']['graph']['stylesheet']
        by_selector = {item['selector']: item['style'] for item in styles}
        self.assertEqual(by_selector['node']['font-size'], 9)
        self.assertEqual(by_selector['edge']['font-size'], 7)

    def setUp(self):
        from web.app import create_app
        self.app = create_app()
        self.client = self.app.server.test_client()

    def post_callback(self, marker, values, triggered):
        key = next(key for key in self.app.callback_map if marker in key)
        callback = self.app.callback_map[key]
        outputs = callback['output']
        if isinstance(outputs, list):
            outputs = [{'id': output.component_id, 'property': output.component_property} for output in outputs]
        else:
            outputs = {'id': outputs.component_id, 'property': outputs.component_property}
        inputs = [dict(item, value=values.get(f'{item["id"]}.{item["property"]}')) for item in callback['inputs']]
        states = [dict(item, value=values.get(f'{item["id"]}.{item["property"]}')) for item in callback['state']]
        return self.client.post('/_dash-update-component', json={
            'output': key, 'outputs': outputs, 'changedPropIds': [triggered], 'inputs': inputs, 'state': states})

    def test_routes_layout_assets_and_callbacks(self):
        self.assertEqual(self.client.get('/').status_code, 200)
        self.assertEqual(self.client.get('/healthz').get_json(), {'status': 'ok'})
        layout = self.client.get('/_dash-layout')
        self.assertEqual(layout.status_code, 200)
        self.assertIn(b'CRNTAnalysis', layout.data)
        self.assertIn(b'cytoscape', layout.data.lower())
        with self.client.get('/assets/workspace.css') as response:
            self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get('/_dash-dependencies').status_code, 200)
        self.assertGreaterEqual(len(self.app.callback_map), 8)

    def test_http_analysis_callback(self):
        key = next(key for key in self.app.callback_map if 'result.data' in key)
        response = self.client.post('/_dash-update-component', json={
            'output': key,
            'outputs': [{'id': 'result', 'property': 'data'}, {'id': 'status', 'property': 'children'}],
            'changedPropIds': ['analyze.n_clicks'],
            'inputs': [
                {'id': 'analyze', 'property': 'n_clicks', 'value': 1},
                {'id': 'model', 'property': 'value', 'value': EXAMPLES['reaction'][3]},
                {'id': 'format', 'property': 'value', 'value': 'react'},
                {'id': 'options', 'property': 'value', 'value': []},
                {'id': 'unresolved', 'property': 'value', 'value': 'symbolic'},
            ], 'state': [],
        })
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()['response']['result']['data']
        self.assertEqual(payload['outcome']['deficiency']['n'], 2)
        self.assertIn('Whole network', payload['report'])

    def test_result_render_graph_inspection_and_download_callbacks(self):
        payload = analyze_document(EXAMPLES['rational'][3], 'ode', ['lift'])
        response = self.post_callback('metrics.children', {'result.data': payload}, 'result.data')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.get_json()['response']['download-text']['disabled'])
        self.assertIn('ds/dt', response.get_json()['response']['report']['children'])
        ode_response = self.post_callback('odes.children', {'result.data': payload}, 'result.data')
        ode_text = ode_response.get_json()['response']['odes']['children']
        self.assertIn('Original ODE system', ode_text)
        self.assertIn('Analyzed ODE system', ode_text)
        self.assertIn('ds/dt', ode_text)
        self.assertNotIn('**', ode_text)
        response = self.post_callback('graph.elements', {
            'result.data': payload, 'mode.value': 'reaction', 'linkage.value': 'all'}, 'result.data')
        self.assertEqual(response.status_code, 200)
        elements = response.get_json()['response']['graph']['elements']
        self.assertGreater(len(elements), 0)
        response = self.post_callback('details.children', {
            'result.data': payload, 'graph.tapNodeData': elements[0]['data'],
            'graph.tapEdgeData': None}, 'graph.tapNodeData')
        self.assertIn('Composition', response.get_json()['response']['details']['children'])
        for trigger, extension in (('download-text.n_clicks', '.txt'), ('download-json.n_clicks', '.analysis')):
            response = self.post_callback('download.data', {'result.data': payload, trigger: 1}, trigger)
            data = response.get_json()['response']['download']['data']
            self.assertTrue(data['filename'].endswith(extension))
            if extension == '.analysis':
                import json
                self.assertEqual(json.loads(data['content']), payload['outcome'])

    def test_editing_input_clears_stale_result_and_invalid_input_reports_error(self):
        values = {'analyze.n_clicks': 1, 'model.value': 'bad input', 'format.value': 'react',
                  'options.value': [], 'unresolved.value': 'symbolic'}
        response = self.post_callback('result.data', values, 'model.value')
        self.assertIsNone(response.get_json()['response']['result']['data'])
        response = self.post_callback('result.data', values, 'analyze.n_clicks')
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.get_json()['response']['result']['data'])
        self.assertIn('ParseError', str(response.get_json()['response']['status']['children']))

    def test_uploads_and_examples_populate_editor_without_server_files(self):
        response = self.post_callback('model.value', {'example.value': 'rational'}, 'example.value')
        data = response.get_json()['response']
        self.assertEqual(data['model']['value'], EXAMPLES['rational'][3])
        self.assertEqual(data['options']['value'], ['lift'])
        encoded = 'data:text/plain;base64,' + base64.b64encode(b"species x\nx'=x").decode()
        response = self.post_callback('model.value', {'upload.contents': encoded, 'upload.filename': 'model.ode'}, 'upload.contents')
        self.assertEqual(response.get_json()['response']['format']['value'], 'ode')
        self.assertEqual(response.get_json()['response']['options']['value'], [])
