# Scientific Methods

This document specifies the Chemical Reaction Network Theory conventions used
by `crntanalysis`. It describes how reaction and ODE inputs become complexes,
graphs, stoichiometric subspaces, linkage classes, and deficiencies.

## Contents

- [Chemical reaction networks](#chemical-reaction-networks)
- [Complex indexing and reaction graph](#complex-indexing-and-reaction-graph)
- [Weighted undirected adjacency](#weighted-undirected-adjacency)
- [Deterministic mass-action kinetics](#deterministic-mass-action-kinetics)
- [Canonical realization of ODE input](#canonical-realization-of-ode-input)
- [Stoichiometric subspace](#stoichiometric-subspace)
- [Linkage classes](#linkage-classes)
- [Whole-network deficiency](#whole-network-deficiency)
- [Linkage-class deficiency](#linkage-class-deficiency)
- [Symbolic coefficients](#symbolic-coefficients)
- [Example calculation](#example-calculation)
- [Reference](#reference)

## Method overview

```mermaid
flowchart LR
    A[Reaction or ODE input] --> B[Complexes and reactions]
    B --> C[Undirected complex graph]
    B --> D[Reaction vectors]
    C --> E[Linkage classes l]
    D --> F[Stoichiometric rank s]
    B --> G[Number of complexes n]
    E --> H[Deficiency delta = n - s - l]
    F --> H
    G --> H
```

## Chemical reaction networks

A chemical reaction network consists of a finite species set, a finite set of
complexes, and directed reactions between complexes. A complex is a formal
nonnegative linear combination of species. For example,

```text
2X + 3Y
```

has complex vector `(2, 3)` in species order `(X, Y)`. The zero complex `0` is
represented by the empty species mapping and is a valid graph node.

A reaction $y \rightarrow y'$ has reaction vector

$$
v = y' - y,\ where\ y,y'\in\mathbb{Z}_{\ge 0}^{|S|}.
$$

Here, $|S|$ is the number of species the network contains. The reaction vector is a signed integer vector in the stoichiometric subspace.

Complex identity is determined by species and resolved stoichiometric
coefficients, not by formatting or the order in which terms were written.

## Complex indexing and reaction graph

Distinct complexes receive zero-based indices in first-appearance order. A
reaction stores the source and target indices rather than copying the complex
vectors.

The reaction graph is directed: every reaction is an edge from its reactant
complex to its product complex. Rate constants are edge weights for reporting
and kinetic interpretation, but they do not affect deficiency.

## Weighted undirected adjacency

Linkage is based on the underlying undirected complex graph. The returned
weighted adjacency matrix is symmetric and uses:

- `0` when no reaction connects two complexes;
- a positive number when one path has a resolved rate value;
- a symbol such as `"k1"` when one path has an unresolved rate;
- a list when parallel or oppositely directed paths connect the same pair.

Direction is retained in the reaction list, not in this symmetric matrix.
Deficiency calculation derives connectivity from reaction endpoints, so it does
not depend on matrix value types.

## Deterministic mass-action kinetics

For reaction $\rho$ with reactant vector $r_\rho$, product vector
$p_\rho$, and positive rate constant $k_\rho$, deterministic mass action
assigns the rate

$$
R_\rho(x)=k_\rho\prod_{i=1}^{m}x_i^{r_{\rho i}}.
$$

The species dynamics are

$$
\frac{dx}{dt}
=\sum_{\rho\in\mathcal R}(p_\rho-r_\rho)R_\rho(x).
$$

Therefore, a rate monomial determines a reactant complex, while its signed
coefficients across species equations determine the reaction vector.

## Canonical realization of ODE input

Recovering a reaction network from ODEs is not unique in general. This project
uses a deterministic canonical convention:

1. Parse every signed `rate_constant * concentration_monomial` contribution.
2. Treat monomial exponents as the reactant complex.
3. Group contributions having the same rate constant and reactant monomial.
4. Combine their signed integer multipliers into one reaction vector.
5. Add the reaction vector to the reactant to obtain the product complex.
6. Reject the realization if a product coefficient becomes negative.

Mass-action exponents must be nonnegative integers after supplied coefficient
values are resolved. A negative term for species `X` is admissible only if its
reactant monomial contains enough `X` to support that consumption.

For example,

$$
\begin{aligned}
\frac{dx}{dt} &= k_1 x^2y, \\
\frac{dy}{dt} &= -k_1 x^2y.
\end{aligned}
$$

is canonically realized as

$$
2X+Y \xrightarrow{k_1} 3X.
$$

The reaction label displays the rate constant $k_1$ above the arrow.

The provided `Example_Data/crn2.ode` does not pass ordinary mass-action
validation. Its `k2 * A^3 * B^2` contribution consumes `X`, although `X` is
absent from that reactant monomial. The parser rejects this rather than silently
constructing a generalized-kinetics network.

## Stoichiometric subspace

Let the reaction vectors be

$$
v_\rho=y'_\rho-y_\rho.
$$

The stoichiometric subspace is their linear span. Its dimension `s` is the rank
of the matrix whose rows are the reaction vectors in a consistent species
ordering.

The calculation uses exact SymPy rationals for numerical coefficients. It does
not use floating-point tolerance to determine rank.

## Linkage classes

A linkage class is a connected component of the underlying undirected complex
graph. Reaction direction and rate values are ignored when determining these
components. An isolated complex is one linkage class by itself.

The implementation finds linkage classes using union-find over complex indices
and reaction endpoints.

## Whole-network deficiency

The standard network deficiency is

$$
\delta=n-s-l,
$$

where:

- `n` is the number of distinct complexes;
- `s` is the dimension of the global stoichiometric subspace;
- `l` is the number of linkage classes.

The global rank is calculated from all reaction vectors together.

## Linkage-class deficiency

For linkage class $i$, the project restricts attention to its complexes and
reactions and calculates

$$
\delta_i=n_i-s_i-1.
$$

Here, `n_i` is the number of complexes in that class and `s_i` is the rank of
the reaction vectors belonging to the class. The linkage count is one by
construction.

The global stoichiometric rank must not be replaced by the sum of the class
ranks. Stoichiometric subspaces belonging to different linkage classes can
overlap. Consequently, the global deficiency need not equal the sum of the
linkage-class deficiencies.

## Symbolic coefficients

### ODE expression normalization

Before extracting monomials, the ODE parser constructs symbolic arithmetic
through a restricted Python AST and expands products and parentheses. Function
calls, attributes, and other executable Python syntax are rejected. Both `^`
and `**` denote powers. Repeated species factors add their exponents.

For example,

$$
x(1-x/K)=x-K^{-1}x^2
$$

has the same realization whether the quadratic factor is written as `x^2` or
`x*x`. Its implicit positive coefficient is one. Parameter-only expressions
such as `1/K` and `a*b` become effective rate labels and are evaluated when all
their parameters are defined. Unresolved expressions retain symbolic labels;
resolved effective rates must be finite and positive. Explicit integer
multipliers attached to symbolic rates retain the existing stoichiometric
contribution convention. Numeric-only terms use their magnitude as the rate.

Species are identified from derivative left-hand sides. Include a zero
derivative for unchanged species; other identifiers are parameters.
Species-dependent denominators and noninteger exponents are rejected in the
default mode. Opt-in extensions are described below.

### Real complexes and independent kinetic orders

`allow_fractional=True` permits nonnegative real ODE powers and adopts the
same source-monomial realization convention as the integer mode. The reaction
`1.4 Y -> 0.4 Y` reproduces `dy/dt = -k*y^1.4`. Nonnegative product coefficients
remain required. Stoichiometric rank and structural deficiency are computed on
the resulting real complex vectors; no classical integer mass-action theorem
is inferred from the numerical deficiency alone.

Explicit `.react` networks may use `Kinetic Orders` or `Rate Laws` to decouple
stoichiometry from kinetics. Kinetic orders are represented separately when
declared; `None` means the ordinary source-complex convention. A full rate law
is stored separately and takes precedence as the authoritative kinetic
expression. Arbitrary rate laws require the model author to establish their
admissible domain and nonnegativity. This distinction follows generalized
mass-action theory's separation of stoichiometric and kinetic complexes;
kinetic-order deficiency is not yet calculated here.
[Müller and Regensburger, 2014](https://arxiv.org/abs/1406.6587).

### Reciprocal auxiliary species

For a species-dependent polynomial denominator $D(x)$ with constant parameters,
introduce $s=D(x)^{-1}$. The chain rule gives

$$
\dot{s}=-s^2\sum_i\frac{\partial D}{\partial x_i}\dot{x}_i.
$$

`lift_rational=True` identifies negative integer powers of such denominators,
replaces them with positive powers of shared auxiliary species, and constructs
their derivatives from the original coupled ODEs. Parameter-only denominators
remain effective rate expressions. Names are collision-checked, including
explicit definitions in `Auxiliary Species`. The supported scope is autonomous
ODEs with polynomial species denominators, optionally with nonnegative real
monomial powers in numerators. Unsupported transformations raise errors.

For AFmodel, $D=1+x+az$ and

$$
\dot{s}=-s^2\dot{x}=-xs^2+K^{-1}x^2s^2+xys^3.
$$

The original dynamics are recovered on $sD=1$ in the domain $D>0$. The
implementation verifies symbolic pullback identities for the original and
auxiliary equations. It derives initial values from original concentrations
and parameter values, rejects inconsistent or singular supplied initial
conditions, and retains unresolved initial expressions as warnings. Positivity
of the denominator over an entire trajectory is a domain assumption, not a
property established by checking its initial value.

The augmented equations still undergo the nonnegative-complex kinetic
realizability check. Fractional powers are permitted only if separately enabled.
The calculated $n$, $s$, $l$, and deficiency refer to the augmented network,
including auxiliary complexes and reaction vectors, rather than being intrinsic
invariants of the original rational ODE. Here the auxiliary symbol $s$ is a
species name; the $s$ in the deficiency formula denotes stoichiometric rank.

Missing rate constants do not affect structural deficiency and may remain
symbolic.

Missing stoichiometric coefficients affect complex identity and reaction-vector
rank. Three parser policies are available:

- `symbolic`: retain the unresolved symbol;
- `error`: reject any unresolved value;
- `one`: substitute `1.0` explicitly.

With symbolic stoichiometry, SymPy calculates a generic symbolic rank. The
result is marked with `symbolic_rank=True`. Special parameter values or
relations between parameters can reduce the rank, merge complexes, or change
the deficiency. Use resolved values when a parameter-specific deficiency is
required.

## Example calculation

For `Example_Data/crn1.react`, the implementation obtains

$$
n=11, \qquad s=4, \qquad l=5, \qquad \delta=2.
$$

The five linkage-class deficiencies are:

```text
[0, 0, 0, 1, 0]
```

This example also demonstrates why class deficiencies should be reported
alongside, but not substituted for, the whole-network deficiency.

## Reference

The deterministic mass-action convention follows the CRN semantics summarized
in Section 2 of:

X. Huang, T. H. Klinge, J. I. Lathrop, X. Li, and J. H. Lutz,
“Real-Time Computability of Real Numbers by Chemical Reaction Networks,”
[arXiv:1803.10267](https://arxiv.org/abs/1803.10267).
