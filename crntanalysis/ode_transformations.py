"""Symbolic reciprocal embeddings of rational ODEs into augmented systems."""

from dataclasses import dataclass
from math import isfinite
from typing import Dict, List, Mapping, Optional

from sympy import Expr, Pow, Rational, Symbol, diff, expand, preorder_traversal, simplify

__all__ = ["ReciprocalLiftResult", "ReciprocalODETransformer"]


@dataclass
class ReciprocalLiftResult:
    equations: Dict[str, Expr]
    initial_conditions: Dict[str, float]
    auxiliaries: List[dict]
    warnings: List[str]


class ReciprocalODETransformer:
    """Introduce s=1/D and derive s'=-s² sum_i (dD/dx_i) x_i'.

    Parameters are constant. Denominators must be polynomial in the original
    species; positive denominators define the admissible positive-state domain.
    This embedding does not guarantee that a nonnegative-complex CRN exists.
    """

    def lift(
        self, equations: Mapping[str, Expr], values: Mapping[str, float],
        initial_conditions: Mapping[str, float],
        requested: Optional[Mapping[str, Expr]] = None,
    ) -> ReciprocalLiftResult:
        requested = requested or {}
        auxiliary_symbols = {Symbol(name) for name in requested}
        if requested and (
            any(expr.free_symbols & auxiliary_symbols for expr in equations.values())
            or any(expr.free_symbols & auxiliary_symbols for expr in requested.values())
            or any(expand(1 / expr) not in {
                expand(node.base) for rhs in equations.values()
                for node in preorder_traversal(rhs)
                if isinstance(node, Pow) and node.exp.is_number and node.exp < 0
            } for expr in requested.values())
        ):
            return self.lift_definitions(equations, values, initial_conditions, requested)
        species = {Symbol(name) for name in equations}
        occupied = {str(s).casefold() for expression in equations.values() for s in expression.free_symbols}
        occupied.update(name.casefold() for name in equations)
        occupied.update(name.casefold() for name in values)
        denominators = set()
        for expression in equations.values():
            for node in preorder_traversal(expression):
                if isinstance(node, Pow) and node.exp.is_number and node.exp < 0 and node.base.free_symbols & species:
                    if not node.exp.is_Integer:
                        raise ValueError("Reciprocal lifting supports integer denominator powers only")
                    denominator = expand(node.base)
                    if not denominator.is_polynomial(*species):
                        raise ValueError(f"Denominator {denominator} is not polynomial in the original species")
                    denominators.add(denominator)
        if len(denominators) > 32:
            raise ValueError("At most 32 distinct reciprocal auxiliary species are supported")
        chosen = {}
        for name, definition in (requested or {}).items():
            if name.casefold() in occupied or name.casefold() in {n.casefold() for n in chosen.values()}:
                raise ValueError(f"Auxiliary species {name!r} conflicts with an existing identifier")
            denominator = expand(1 / definition)
            if simplify(definition * denominator - 1) != 0 or denominator not in denominators:
                raise ValueError(f"Auxiliary {name!r} must equal the reciprocal of a species-dependent denominator in the ODEs")
            if denominator in chosen:
                raise ValueError("A denominator may have only one auxiliary species")
            chosen[denominator] = name
        counter = 1
        for denominator in sorted(denominators, key=str):
            if denominator in chosen:
                continue
            while f"_aux_s{counter}".casefold() in occupied:
                counter += 1
            chosen[denominator] = f"_aux_s{counter}"
            occupied.add(f"_aux_s{counter}".casefold())
            counter += 1

        def rewrite(expression):
            replacements = {}
            for node in preorder_traversal(expression):
                if isinstance(node, Pow) and node.exp.is_Integer and node.exp < 0:
                    denominator = expand(node.base)
                    if denominator in chosen:
                        replacements[node] = Symbol(chosen[denominator]) ** (-node.exp)
            return expand(expression.xreplace(replacements))

        transformed = {name: rewrite(rhs) for name, rhs in equations.items()}
        initials = dict(initial_conditions)
        records, warnings = [], []
        initial_substitutions = {Symbol(name): Rational(str(value)) for name, value in {**values, **initials}.items()}
        pullback = {Symbol(name): 1 / denominator for denominator, name in chosen.items()}
        for denominator, name in sorted(chosen.items(), key=lambda item: item[1]):
            auxiliary = Symbol(name)
            total_derivative = sum(diff(denominator, Symbol(state)) * rhs for state, rhs in equations.items())
            rhs = expand(-auxiliary ** 2 * rewrite(total_derivative))
            transformed[name] = rhs
            expected = -total_derivative / denominator ** 2
            if simplify(rhs.subs(pullback, simultaneous=True) - expected) != 0:
                raise ValueError(f"Could not verify the chain-rule embedding for {name}")
            initial_expression = (1 / denominator).subs(initial_substitutions)
            initial = None
            if not initial_expression.free_symbols:
                try:
                    initial = float(initial_expression)
                except (TypeError, ValueError):
                    raise ValueError(f"Denominator for {name} is singular at the initial state") from None
                if not isfinite(initial) or initial <= 0:
                    raise ValueError(f"Denominator for {name} must be positive and finite at the initial state")
                if name in initials and abs(initials[name] - initial) > 1e-10 * max(1, abs(initial)):
                    raise ValueError(f"Initial condition for {name} violates its reciprocal constraint")
                initials[name] = initial
            else:
                warnings.append(f"Initial condition for {name} is unresolved: {initial_expression}; supply all original initial values and denominator parameters")
            records.append({
                "species": name, "definition": str(1 / denominator),
                "constraint": f"{name}*({denominator}) = 1",
                "domain": f"{denominator} > 0",
                "derivative": str(rhs), "initial_expression": str(initial_expression),
                "initial_value": initial, "chain_rule_verified": True,
            })
        for name, rhs in equations.items():
            if simplify(transformed[name].subs(pullback, simultaneous=True) - rhs) != 0:
                raise ValueError(f"Could not verify original-equation recovery for {name}")
        return ReciprocalLiftResult(transformed, initials, records, warnings)

    def lift_definitions(self, equations, values, initial_conditions, definitions):
        """Differentiate acyclic explicit definitions in dependency order.

        Polynomial definitions and reciprocal polynomial definitions are
        supported. Cycles require an implicit/DAE formulation and are rejected.
        """
        names = set(definitions)
        if len(names) > 32:
            raise ValueError('At most 32 explicit auxiliary species are supported')
        occupied = {name.casefold() for name in equations} | {name.casefold() for name in values}
        if len({name.casefold() for name in names}) != len(names) or any(name.casefold() in occupied for name in names):
            raise ValueError('Auxiliary species names must be unique and distinct from species and parameters')
        remaining, ordered = dict(definitions), []
        while remaining:
            ready = sorted(name for name, expr in remaining.items()
                           if not ({str(symbol) for symbol in expr.free_symbols} & set(remaining)))
            if not ready:
                raise ValueError('Circular auxiliary definitions: ' + ', '.join(sorted(remaining)) +
                                 '. Use acyclic explicit definitions; implicit/DAE systems are not supported.')
            for name in ready:
                ordered.append((name, remaining.pop(name)))
        all_states = {Symbol(name) for name in equations} | {Symbol(name) for name in names}
        known = all_states | {Symbol(name) for name in values}
        for name, definition in ordered:
            unknown = definition.free_symbols - known
            if unknown:
                raise ValueError(f'Auxiliary {name!r} references undeclared identifiers: {sorted(map(str, unknown))}')
        transformed = dict(equations)
        pullback, records, warnings = {}, [], []
        initials = dict(initial_conditions)
        substitutions = {Symbol(name): Rational(str(value)) for name, value in {**values, **initials}.items()}
        for name, definition in ordered:
            state = Symbol(name)
            reciprocal = expand(1 / definition)
            is_reciprocal = reciprocal.is_polynomial(*all_states) and bool(reciprocal.free_symbols & all_states)
            if not is_reciprocal and not definition.is_polynomial(*all_states):
                raise ValueError(f'Auxiliary {name!r} must be polynomial or the reciprocal of a polynomial in species')
            resolved = simplify(definition.subs(pullback, simultaneous=True))
            pullback[state] = resolved
            dependencies = sorted(str(symbol) for symbol in definition.free_symbols if str(symbol) in names)
            derivatives = dict(transformed)
            if is_reciprocal:
                total = sum(diff(reciprocal, Symbol(other)) * rhs for other, rhs in derivatives.items())
                rhs = -state**2 * total
                # Replace reciprocal occurrences in all equations, keeping
                # auxiliary definitions themselves as recorded constraints.
                def rewrite(expr):
                    swaps = {}
                    for node in preorder_traversal(expr):
                        if isinstance(node, Pow) and node.exp.is_Integer and node.exp < 0 and expand(node.base) == reciprocal:
                            swaps[node] = state**(-node.exp)
                    return expand(expr.xreplace(swaps))
                transformed = {other: rewrite(expr) for other, expr in transformed.items()}
                rhs = rewrite(rhs)
            else:
                rhs = expand(sum(diff(definition, Symbol(other)) * derivative for other, derivative in derivatives.items()))
            transformed[name] = rhs
            original_rhs = {other: expr.subs(pullback, simultaneous=True) for other, expr in equations.items()}
            expected = sum(diff(resolved, Symbol(other)) * expr for other, expr in original_rhs.items())
            if simplify(rhs.subs(pullback, simultaneous=True) - expected) != 0:
                raise ValueError(f'Could not verify the chain-rule embedding for {name}')
            initial_expression = resolved.subs(substitutions)
            initial = None
            if not initial_expression.free_symbols:
                try:
                    initial = float(initial_expression)
                except (TypeError, ValueError):
                    raise ValueError(f'Auxiliary {name} is singular at the initial state') from None
                if not isfinite(initial) or initial < 0 or (is_reciprocal and initial == 0):
                    raise ValueError(f'Auxiliary {name} must have a finite nonnegative admissible initial value')
                if name in initials and abs(initials[name] - initial) > 1e-10 * max(1, abs(initial)):
                    raise ValueError(f'Initial condition for {name} violates its auxiliary constraint')
                initials[name] = initial
            else:
                warnings.append(f'Initial condition for {name} is unresolved: {initial_expression}')
            records.append(dict(species=name, definition=str(definition), resolved_definition=str(resolved),
                                dependencies=dependencies, constraint=f'{name} = {definition}',
                                domain=f'{reciprocal} > 0' if is_reciprocal else f'{definition} >= 0',
                                derivative=str(rhs), initial_expression=str(initial_expression),
                                initial_value=initial, chain_rule_verified=True))
        original_rhs = {other: expr.subs(pullback, simultaneous=True) for other, expr in equations.items()}
        for name, rhs in transformed.items():
            expected = (original_rhs[name] if name in equations else
                        sum(diff(pullback[Symbol(name)], Symbol(other)) * expr
                            for other, expr in original_rhs.items()))
            if simplify(rhs.subs(pullback, simultaneous=True) - expected) != 0:
                raise ValueError(f'Could not verify complete auxiliary-system recovery for {name}')
        # Close any remaining reciprocal denominators in the augmented system.
        lifted = self.lift(transformed, values, initials)
        if len(records) + len(lifted.auxiliaries) > 32:
            raise ValueError('At most 32 total auxiliary species are supported')
        for record in records:
            record['derivative'] = str(lifted.equations[record['species']])
        return ReciprocalLiftResult(lifted.equations, lifted.initial_conditions,
                                   records + lifted.auxiliaries, warnings + lifted.warnings)
