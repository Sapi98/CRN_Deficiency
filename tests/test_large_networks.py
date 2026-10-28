"""Generic regression networks only; no private research models are fixtures."""
import json
import random
import tempfile
import unittest

from sympy import Matrix, Rational
from crntanalysis.crn_models import Complex, Reaction, ReactionGraph, ReactionNetwork
from crntanalysis.deficiency_utils import calculate_deficiency
from crntanalysis.graph_utils import ReactionGraphBuilder
from crntanalysis.orchestrator import AnalysisReportReader, AnalysisReportWriter, CRNAnalysisService
from crntanalysis.reaction_parser import ReactionFileParser
from crntanalysis.sparse_adjacency import SparseAdjacencyMatrix


class LargeNetworkTests(unittest.TestCase):
    def test_sparse_adjacency_matches_dense_parallel_reverse_and_self_edges(self):
        complexes = [Complex(i, str(i), {f'X{i}': 1}) for i in range(3)]
        reactions = [Reaction(0, 0, 1, 'k1'), Reaction(1, 1, 0, 'k2', 2),
                     Reaction(2, 0, 1, 'k3', 3), Reaction(3, 2, 2, 'k4', 4)]
        _, dense = ReactionGraphBuilder().build(complexes, reactions)
        _, sparse = ReactionGraphBuilder(dense_threshold=0).build(complexes, reactions)
        self.assertIsInstance(sparse, SparseAdjacencyMatrix)
        self.assertEqual(sparse.to_dense(), dense)
        self.assertEqual(sparse[-1][-1], 4)
        self.assertEqual(SparseAdjacencyMatrix.from_dict(sparse.to_dict()).to_dense(), dense)
        with self.assertRaises(ValueError):
            sparse.to_dense(max_cells=8)

    def test_sparse_report_round_trip_keeps_indices_and_nonzero_cells(self):
        text = 'Reactions:\n' + '\n'.join(f'X{i} k{i}-> X{i+1}' for i in range(300))
        outcome = CRNAnalysisService().analyze_text(text, input_format='react')
        data = outcome.to_dict()['network']['adjacency_matrix']
        self.assertEqual(data['format'], 'sparse')
        self.assertEqual(data['shape'], [301, 301])
        self.assertEqual(len(data['entries']), 600)
        self.assertLess(len(json.dumps(data)), 50000)
        with tempfile.TemporaryDirectory() as folder:
            for extension in ('analysis', 'output'):
                path = AnalysisReportWriter().write(outcome, folder, extension=extension)
                restored = AnalysisReportReader().read(path)
                self.assertEqual(restored.to_dict(), outcome.to_dict())

    def test_exact_rank_matches_independent_full_reaction_matrix(self):
        randomizer = random.Random(57)
        names = ['A', 'B', 'C', 'D']
        for case in range(25):
            complexes = [Complex(i, str(i), {name: randomizer.randrange(4) / 2
                                            for name in names}) for i in range(8)]
            reactions = [Reaction(i, randomizer.randrange(8), randomizer.randrange(8), f'k{i}')
                         for i in range(16)]
            network = ReactionNetwork(reactions, complexes, ReactionGraph(complexes, reactions), [], {}, {}, {})
            result = calculate_deficiency(network)
            def rank(edges):
                return Matrix([[Rational(str(complexes[r.target].species[name]))
                                - Rational(str(complexes[r.source].species[name]))
                                for name in names] for r in edges]).rank() if edges else 0
            self.assertEqual(result.stoichiometric_rank, rank(reactions), case)
            for linkage in result.linkage_classes:
                self.assertEqual(linkage.stoichiometric_rank,
                                 rank([reactions[i] for i in linkage.reaction_indices]), case)

    def test_shared_stoichiometric_directions_across_classes_are_not_added(self):
        network = ReactionFileParser().parse_text('Reactions:\nA k1-> B\n2 A k2-> A + B')
        result = calculate_deficiency(network)
        self.assertEqual(result.number_of_linkage_classes, 2)
        self.assertEqual([x.stoichiometric_rank for x in result.linkage_classes], [1, 1])
        self.assertEqual(result.stoichiometric_rank, 1)

    def test_invalid_sparse_reports_are_rejected(self):
        for data in ({'format': 'sparse', 'shape': [2, 3], 'entries': []},
                     {'format': 'sparse', 'shape': [2, 2], 'entries': [[2, 0, 1]]},
                     {'format': 'sparse', 'shape': [2, 2], 'entries': [[0, 0, 1], [0, 0, 2]]}):
            with self.subTest(data=data), self.assertRaises(ValueError):
                SparseAdjacencyMatrix.from_dict(data)
