import unittest

from crntanalysis.crn_models import ReactionNetwork
from crntanalysis.ode_parser import ODEFileParser, ODEParseError, parse_ode_text


VALID_ODE = """ODE Model:
dx/dt = 2 * k1 * X^2 * Y - k2 * X
dy/dt = -k1 * X^2 * Y
Coefficients:
k1 = 0.5
k2 = 0.1
"""


class ODEParserTests(unittest.TestCase):
    def test_sectioned_rational_example_matches_xpp_network(self):
        parser = ODEFileParser(lift_rational=True)
        sectioned = parser.parse_file('Example_Data/rational_auxiliary_sectioned.ode').network
        xpp = parser.parse_file('Example_Data/rational_auxiliary_xpp.ode').network
        self.assertEqual(sectioned.reactions, xpp.reactions)
        self.assertEqual(sectioned.complexes, xpp.complexes)
        self.assertEqual(sectioned.analysis_metadata['transformed_equations'],
                         xpp.analysis_metadata['transformed_equations'])
        self.assertAlmostEqual(sectioned.initial_conditions['s'], 0.25)

    def test_explicit_species_preserve_names_and_zero_derivatives(self):
        parsed = ODEFileParser().parse_text(
            'Species:\nx, y\nODE Model:\ndx/dt=0\ndy/dt=k*y+z*y\nCoefficients:\nk=2\nz=3')
        self.assertEqual(parsed.network.analysis_metadata['species_declaration'], ['x', 'y'])
        self.assertEqual(parsed.network.analysis_metadata['original_equations']['x'], '0')
        self.assertEqual(set(parsed.network.rate_constants), {'k', 'z'})
        self.assertNotIn('z', {name for c in parsed.network.complexes for name in c.species})

    def test_explicit_species_validate_derivatives_and_duplicates(self):
        for text in ('Species:\nx,y\nODE Model:\ndx/dt=x',
                     'Species:\nx\nODE Model:\ndx/dt=x\ndy/dt=y',
                     'Species:\nx,X\nODE Model:\ndx/dt=x',
                     'Species:\nx=1\nODE Model:\ndx/dt=x',
                     'Species:\nx\nODE Model:\ndx/dt=x\nCoefficients:\nx=2'):
            with self.subTest(text=text), self.assertRaises(ODEParseError):
                ODEFileParser().parse_text(text)

    def test_xpp_explicit_species_and_automatic_auxiliary_registration(self):
        parsed = ODEFileParser(lift_rational=True).parse_text(
            "species x,y\nparam z=2\nx'=-x/(1+x+z)\ny'=0\ns=1/(1+x+z)")
        self.assertEqual(parsed.network.analysis_metadata['species_declaration'], ['x', 'y'])
        self.assertEqual(set(parsed.network.analysis_metadata['transformed_equations']), {'x', 'y', 's'})
    def test_xpp_parameters_and_derivative_aliases_match_section_format(self):
        standard = "# Model\nparam k=2, q=0.5\nx' = -k*x\ndy/dt = k*x-q*y\ninit x=99,y=4\n@ total=250,dt=0.1\ndone"
        sectioned = "ODE Model:\ndx/dt = -k*x\ndy/dt = k*x-q*y\nCoefficients:\nk = 2\nq = 0.5"
        expected = parse_ode_text(sectioned)
        actual = parse_ode_text(standard)
        self.assertEqual(actual, expected)
        self.assertEqual(actual["initial_conditions"], {})

    def test_xpp_example_accepts_parameters_and_equations(self):
        parsed = ODEFileParser(lift_rational=True).parse_file("Example_Data/rational_auxiliary_xpp.ode")
        self.assertEqual(parsed.network.rate_constants["k"], 0.4)
        self.assertEqual(parsed.network.rate_constants["q"], 0.2)
        self.assertEqual(len(parsed.network.analysis_metadata["auxiliary_species"]), 1)
        self.assertGreater(len(parsed.network.reactions), 0)

    def test_parallel_ode_rates_are_added_without_merging_reverse_edges(self):
        from sympy import Symbol, simplify
        parsed = ODEFileParser().parse_text(
            'ODE Model:\ndx/dt=-a*x-b*x+c*y+d*y\ndy/dt=a*x+b*x-c*y-d*y\n'
            'Coefficients:\na=1\nb=2\nc=3\nd=4')
        reactions = parsed.network.reactions
        self.assertEqual(len(reactions), 2)
        self.assertEqual([r.index for r in reactions], [0, 1])
        self.assertEqual(sorted(r.rate for r in reactions), [3, 7])
        for r in reactions:
            expected = ((Symbol('a') + Symbol('b')) * Symbol('x')
                        if parsed.network.complexes[r.source].species == {'x': 1}
                        else (Symbol('c') + Symbol('d')) * Symbol('y'))
            self.assertEqual(simplify(ODEFileParser._expression(r.rate_expression, {}, 1) - expected), 0)

    def test_xpp_example_has_unique_directed_edges_and_preserves_vector_field(self):
        from sympy import Symbol, simplify
        from crntanalysis.deficiency_utils import calculate_deficiency
        parsed = ODEFileParser(lift_rational=True).parse_file('Example_Data/rational_auxiliary_xpp.ode')
        network = parsed.network
        endpoints = [(r.source, r.target) for r in network.reactions]
        self.assertEqual(len(endpoints), len(set(endpoints)))
        self.assertEqual(calculate_deficiency(network).deficiency, 1)
        for species, rhs in network.analysis_metadata['transformed_equations'].items():
            reconstructed = 0
            for r in network.reactions:
                change = (network.complexes[r.target].species.get(species, 0)
                          - network.complexes[r.source].species.get(species, 0))
                reconstructed += change * ODEFileParser._expression(r.rate_expression, {}, 1)
            self.assertEqual(simplify(reconstructed - ODEFileParser._expression(rhs, {}, 1)), 0)

    def test_parallel_symbolic_rates_remain_symbolic(self):
        parsed = ODEFileParser().parse_text('ODE Model:\ndx/dt=-a*x-b*x')
        self.assertEqual(len(parsed.network.reactions), 1)
        self.assertEqual(parsed.network.reactions[0].rate_constant, 'a + b')
        self.assertIsNone(parsed.network.reactions[0].rate)

    def test_xpp_named_reciprocal_matches_sectioned_auxiliary(self):
        raw = "param k=2\nx'=-k*x/(1+x)\ns = 1/(1+x)\ndone"
        sectioned = "ODE Model:\ndx/dt=-k*x/(1+x)\nCoefficients:\nk=2\nAuxiliary Species:\ns=1/(1+x)"
        parser = ODEFileParser(lift_rational=True)
        self.assertEqual(parser.parse_text(raw).network.to_dict(),
                         parser.parse_text(sectioned).network.to_dict())
        with self.assertRaisesRegex(ODEParseError, 'lift_rational'):
            ODEFileParser().parse_text(raw)

    def test_option_errors_guide_gui_users_to_checkboxes(self):
        cases = (
            ("ODE Model:\ndx/dt=-x/(1+x)\nAuxiliary Species:\ns=1/(1+x)",
             'Lift rational ODE rates using auxiliary species'),
            ("ODE Model:\ndx/dt=-x^1.4",
             'Allow fractional ODE powers (real complexes)'),
        )
        for text, checkbox in cases:
            with self.subTest(checkbox=checkbox):
                with self.assertRaises(ODEParseError) as caught:
                    ODEFileParser().parse_text(text)
                self.assertIn(checkbox, str(caught.exception))
                self.assertIn('top of the', str(caught.exception))
                self.assertIn('Analyze model again', str(caught.exception))

    def test_xpp_continuations_comments_and_scientific_notation(self):
        text = "par k=2e-3, \\\n q=0.5 # parameters\nx' = -k*x + \\\n q*x\ndone\nignored after done"
        parsed = parse_ode_text(text)
        self.assertEqual(parsed["rate_constants"], {"k": 0.002, "q": 0.5})

    def test_xpp_invalid_parameters_and_unsupported_dynamic_definitions_fail(self):
        for text in ("param k=2,k=3\nx'=k*x", "param k=nope\nx'=k*x",
                     "f(x)=x*x\nx'=f(x)", "par k=2\\"):
            with self.subTest(text=text), self.assertRaises(ODEParseError):
                parse_ode_text(text)

    def test_fractional_mode_is_explicit_and_preserves_real_coefficients(self):
        text = "ODE Model:\ndy/dt = -k*y^1.4\nCoefficients:\nk = 2"
        with self.assertRaisesRegex(ODEParseError, "allow_fractional"):
            parse_ode_text(text)
        parsed = ODEFileParser(allow_fractional=True).parse_text(text)
        reaction = parsed.network.reactions[0]
        self.assertEqual(parsed.network.reactant_complex(reaction).species, {"y": 1.4})
        self.assertEqual(parsed.network.product_complex(reaction).species, {"y": 0.4})
        self.assertEqual(reaction.rate_expression, "k*y**(7/5)")

    def test_fractional_example_recovers_original_odes_and_reconstructs_reaction_vector_field(self):
        from sympy import Rational, Symbol, simplify
        parser = ODEFileParser(allow_fractional=True, lift_rational=True)
        parsed = parser.parse_file("Example_Data/fractional_auxiliary.ode")
        metadata = parsed.network.analysis_metadata
        self.assertEqual(len(metadata["auxiliary_species"]), 1)
        auxiliary = metadata["auxiliary_species"][0]
        self.assertEqual(auxiliary["species"], "s")
        self.assertTrue(auxiliary["chain_rule_verified"])
        self.assertAlmostEqual(parsed.network.initial_conditions["s"], 0.5)
        field = {name: 0 for name in metadata["transformed_equations"]}
        for reaction in parsed.network.reactions:
            source = parsed.network.reactant_complex(reaction).species
            target = parsed.network.product_complex(reaction).species
            rate = parser._expression(reaction.rate_expression, {}, 1)
            for name in field:
                change = Rational(str(target.get(name, 0))) - Rational(str(source.get(name, 0)))
                field[name] += change * rate
        parameters = {Symbol(name): Rational(str(value)) for name, value in
                      {**parsed.network.rate_constants, **parsed.network.stoichiometric_coefficients}.items()}
        for name, expression in metadata["transformed_equations"].items():
            expected = parser._expression(expression, {}, 1)
            self.assertEqual(simplify((field[name] - expected).subs(parameters)), 0)

    def test_lifting_without_initial_values_retains_constraint_and_warns(self):
        result = parse_ode_text("ODE Model:\ndx/dt = -x/(1+x)", lift_rational=True)
        auxiliary = result["analysis_metadata"]["auxiliary_species"][0]
        self.assertIsNone(auxiliary["initial_value"])
        self.assertTrue(any("unresolved" in warning for warning in result["warnings"]))

    def test_singular_and_inconsistent_auxiliary_initial_conditions_are_rejected(self):
        with self.assertRaisesRegex(ODEParseError, "singular|positive"):
            parse_ode_text("ODE Model:\ndx/dt = x/(x-1)\nInitial Conditions:\nx = 1", lift_rational=True)
        with self.assertRaisesRegex(ODEParseError, "violates"):
            parse_ode_text("ODE Model:\ndx/dt = -x/(1+x)\nAuxiliary Species:\ns = 1/(1+x)\nInitial Conditions:\nx = 1\ns = 0.9", lift_rational=True)

    def test_automatic_names_do_not_collide_and_lifting_need_not_be_kinetic(self):
        result = parse_ode_text("ODE Model:\ndx/dt = _aux_s1*x/(1+x)", lift_rational=True)
        self.assertEqual(result["analysis_metadata"]["auxiliary_species"][0]["species"], "_aux_s2")
        with self.assertRaisesRegex(ODEParseError, "consumes"):
            parse_ode_text("ODE Model:\ndx/dt = -y/(1+x)\ndy/dt = 0", lift_rational=True)

    def test_zero_parameter_in_denominator_is_not_treated_as_a_zero_rate(self):
        result = parse_ode_text("ODE Model:\ndx/dt = x/(1+a)\nCoefficients:\na = 0")
        self.assertEqual(result["reactions"][0]["rate"], 1.0)

    def test_shared_multispecies_denominator_uses_full_chain_rule(self):
        from sympy import Symbol, simplify
        text = "ODE Model:\ndx/dt = -x/(1+x+y)\ndy/dt = -y/(1+x+y)\nAuxiliary Species:\ns = 1/(1+x+y)"
        parser = ODEFileParser(lift_rational=True)
        result = parser.parse_text(text)
        records = result.network.analysis_metadata["auxiliary_species"]
        self.assertEqual(len(records), 1)
        actual = parser._expression(records[0]["derivative"], {}, 1)
        x, y, s = Symbol("x"), Symbol("y"), Symbol("s")
        self.assertEqual(simplify(actual - s**3*(x+y)), 0)

    def test_invalid_auxiliary_names_and_definitions_are_rejected(self):
        for definition in ("x = 1/(1+x)", "s = 1/(1+t)"):
            with self.subTest(definition=definition), self.assertRaises(ODEParseError):
                parse_ode_text("ODE Model:\ndx/dt = -x/(1+x)\nAuxiliary Species:\n" + definition, lift_rational=True)

    def test_nested_auxiliaries_add_each_chain_rule_ode(self):
        from sympy import Symbol, simplify
        text = "ODE Model:\ndx/dt = -x*t\nAuxiliary Species:\nt = 1/(1+s)\ns = 1/(1+x)\nInitial Conditions:\nx = 1"
        parsed = ODEFileParser(lift_rational=True).parse_text(text)
        metadata = parsed.network.analysis_metadata
        self.assertEqual(set(metadata['transformed_equations']), {'x', 's', 't'})
        self.assertEqual(len(parsed.equations), 3)
        x, s, t = Symbol('x'), Symbol('s'), Symbol('t')
        self.assertEqual(simplify(ODEFileParser._expression(metadata['transformed_equations']['s'], {}, 1) - x*t*s**2), 0)
        self.assertEqual(simplify(ODEFileParser._expression(metadata['transformed_equations']['t'], {}, 1) + x*s**2*t**3), 0)
        self.assertEqual(parsed.network.initial_conditions['s'], 0.5)
        self.assertAlmostEqual(parsed.network.initial_conditions['t'], 2/3)
        self.assertEqual(metadata['auxiliary_species'][1]['dependencies'], ['s'])

    def test_polynomial_auxiliary_gets_an_ode(self):
        parsed = ODEFileParser(lift_rational=True).parse_text(
            'ODE Model:\ndx/dt=x\nAuxiliary Species:\nu=x*x\nInitial Conditions:\nx=2')
        self.assertEqual(set(parsed.network.analysis_metadata['transformed_equations']), {'x', 'u'})
        self.assertEqual(parsed.network.initial_conditions['u'], 4)

    def test_circular_auxiliaries_are_rejected(self):
        for definitions in ('s=1/(1+s)', 's=1/(1+t)\nt=1/(1+s)'):
            with self.subTest(definitions=definitions), self.assertRaisesRegex(ODEParseError, 'Circular'):
                ODEFileParser(lift_rational=True).parse_text(
                    'ODE Model:\ndx/dt=x\nAuxiliary Species:\n' + definitions)

    def test_equivalent_logistic_forms_have_identical_realizations(self):
        forms = ["x*(1-x/K)", "x-(1/K)*x^2", "x-(1/K)*x*x"]
        networks = [parse_ode_text(f"ODE Model:\ndx/dt = {rhs}") for rhs in forms]
        for result in networks[1:]:
            self.assertEqual(result["complexes"], networks[0]["complexes"])
            self.assertEqual(result["reactions"], networks[0]["reactions"])
        edges = networks[0]["reactions"]
        self.assertEqual({edge["weight"] for edge in edges}, {1.0, "1/K"})
        consuming = next(edge for edge in edges if edge["weight"] == "1/K")
        self.assertEqual(networks[0]["complexes"][consuming["source_complex"]]["species"], {"x": 2})
        self.assertEqual(networks[0]["complexes"][consuming["target_complex"]]["species"], {"x": 1})

    def test_effective_rates_and_implicit_unit_rate_resolve_in_strict_mode(self):
        result = parse_ode_text("ODE Model:\ndx/dt = x*(1-x/K)\nCoefficients:\nK = 8", unresolved="error")
        self.assertEqual({edge["rate"] for edge in result["reactions"]}, {1.0, 0.125})
        self.assertEqual(result["warnings"], [])

    def test_repeated_species_and_multiple_parameter_factors(self):
        result = parse_ode_text("ODE Model:\ndx/dt = -a*b*x*x\nCoefficients:\na = 2\nb = 3")
        edge = result["reactions"][0]
        self.assertEqual(edge["rate"], 6.0)
        self.assertEqual(result["complexes"][edge["source_complex"]]["species"], {"x": 2})

    def test_species_denominator_is_rejected_with_kinetic_explanation(self):
        with self.assertRaisesRegex(ODEParseError, "Species-dependent denominator") as caught:
            parse_ode_text("ODE Model:\ndx/dt = x*(1-x/K)-x*y/(1+x+a*z)\ndy/dt = 0\ndz/dt = 0")
        message = str(caught.exception)
        self.assertIn('Auxiliary Species:\ns = 1/(1+x+a*z)', message)
        self.assertIn('Lift rational ODE rates using auxiliary species', message)
        self.assertIn('standalone assignment', message)
        self.assertIn('not arbitrary non-polynomial', message)
        example = message.split('format:\n\n', 1)[1].split('\n\nAdapt the example', 1)[0]
        result = ODEFileParser(lift_rational=True).parse_text(example)
        self.assertEqual(result.network.analysis_metadata['auxiliary_species'][0]['species'], 's')

    def test_zero_equation_and_decimal_rate(self):
        result = parse_ode_text("ODE Model:\ndx/dt = 0.5*x\ndy/dt = 0")
        self.assertEqual(len(result["reactions"]), 1)
        self.assertEqual(result["reactions"][0]["rate"], 0.5)

    def test_function_calls_are_rejected_without_evaluation(self):
        with self.assertRaises(ODEParseError):
            parse_ode_text("ODE Model:\ndx/dt = __import__('os').getcwd()")

    def test_builds_canonical_reactions(self):
        result = parse_ode_text(VALID_ODE)
        self.assertEqual(len(result["reactions"]), 2)
        reaction = result["reactions"][0]
        self.assertEqual(result["complexes"][reaction["source_complex"]]["species"], {"X": 2, "Y": 1})
        self.assertEqual(result["complexes"][reaction["target_complex"]]["species"], {"X": 4})
        self.assertEqual(result["reactions"][0]["rate"], 0.5)
        self.assertEqual(result["adjacency_matrix"][0][1], 0.5)

    def test_object_api(self):
        parsed = ODEFileParser().parse_text(VALID_ODE)
        self.assertIsInstance(parsed.network, ReactionNetwork)
        self.assertEqual(parsed.equations[0].species, "X")

    def test_symbolic_missing_rate(self):
        result = parse_ode_text("ODE Model:\ndx/dt = k * X")
        self.assertIsNone(result["reactions"][0]["rate"])
        self.assertEqual(result["reactions"][0]["weight"], "k")
        self.assertEqual(result["adjacency_matrix"], [[0, "k"], ["k", 0]])

    def test_rejects_non_mass_action_ode_in_example(self):
        with self.assertRaisesRegex(ODEParseError, "consumes 'X'"):
            ODEFileParser().parse_file("Example_Data/crn2.ode")

    def test_invalid_assignment_uses_ode_error(self):
        with self.assertRaises(ODEParseError):
            parse_ode_text("ODE Model:\ndx/dt = k * X\nCoefficients:\nk = nope")

    def test_warns_about_unused_coefficient(self):
        result = parse_ode_text(VALID_ODE + "unused = 4\n")
        self.assertEqual(result["warnings"], ["Coefficient 'unused' is defined but not used"])


if __name__ == "__main__":
    unittest.main()
