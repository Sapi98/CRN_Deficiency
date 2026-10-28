"""Lossless sparse weighted adjacency with lazy matrix-style indexing."""
from collections.abc import Sequence


class _SparseRow(Sequence):
    def __init__(self, matrix, row):
        self.matrix, self.row = matrix, row

    def __len__(self):
        return self.matrix.size

    def __getitem__(self, column):
        if isinstance(column, slice):
            return [self[index] for index in range(*column.indices(len(self)))]
        if column < 0:
            column += len(self)
        if not 0 <= column < len(self):
            raise IndexError(column)
        return self.matrix.entries.get((self.row, column), 0)


class SparseAdjacencyMatrix(Sequence):
    """Store nonzero cells only; accessing matrix[i][j] never densifies it."""

    def __init__(self, size, entries=None):
        self.size = size
        self.entries = dict(entries or {})

    def __len__(self):
        return self.size

    def __getitem__(self, row):
        if isinstance(row, slice):
            return [self[index] for index in range(*row.indices(self.size))]
        if row < 0:
            row += self.size
        if not 0 <= row < self.size:
            raise IndexError(row)
        return _SparseRow(self, row)

    def to_dict(self):
        """Serialize COO-style nonzero cells without allocating a dense array."""
        return {'format': 'sparse', 'shape': [self.size, self.size],
                'entries': [[row, column, value[:] if isinstance(value, list) else value]
                            for (row, column), value in sorted(self.entries.items())]}

    @classmethod
    def from_dict(cls, data):
        shape = data.get('shape', [])
        if (data.get('format') != 'sparse' or len(shape) != 2 or shape[0] != shape[1]
                or type(shape[0]) is not int or shape[0] < 0):
            raise ValueError('Invalid sparse adjacency shape')
        entries = {}
        for row, column, value in data['entries']:
            if (type(row) is not int or type(column) is not int
                    or not 0 <= row < shape[0] or not 0 <= column < shape[1]
                    or (row, column) in entries):
                raise ValueError('Invalid or duplicate sparse adjacency cell')
            entries[row, column] = value
        return cls(shape[0], entries)

    def to_dense(self, max_cells=1_000_000):
        """Explicit opt-in conversion, guarded against accidental huge allocation."""
        if self.size**2 > max_cells:
            raise ValueError('Dense adjacency exceeds max_cells; use sparse entries instead')
        return [list(row) for row in self]
