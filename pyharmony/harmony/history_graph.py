

class Grid:

    def place(self, obj, row, column):
        # TODO

    def place_sequence(self, seq, row, column):
        for i, e in enumerate(seq):
            self.place(e, row + i, column)

class HistoryGraph:

    class Sequence:
        def __init__(self):
            self.nodes = []

        def append(self, node):
            self.nodes.append(node)
            node.sequence = self

        def get_paths(self):
            paths = set()
            for c in self.nodes:
                paths.update(((c, other) for other in c.references))
            return paths

        def get_dependencies(self):
            paths = set()
            for c in self.nodes:
                paths.update([node.sequence for node in c.references])
            return paths

        def top(self):
            return self.nodes[-1]

        def height(self):
            return len(self.nodes)

        def __repr__(self):
            return 'seq' + repr(list(reversed(self.nodes)))

    def compute(self, node):

        # Compute logical sequences of commits displayed together
        sequences = self.compute_sequences(node)

        # Order them topologically
        ordered_sequences = iter(self.topological_sort(sequences))

        grid = Grid()

        s0 = next(ordered_sequences)
        grid.place_sequence(s0, 0, 0)
        prev = s0

        for s in ordered_sequences:
            references_todo = s.get_references()

            placed = False

            # Align with previous sequence if that makes sense
            if prev.bottom() in s.top().references:
                grid.place_sequence_below(prev.bottom(), s)
                references_todo.remove( (s.top(), prev.bottom()) )
                placed = True

            if not placed:
                # For now, always create a new column
                grid.place_sequence_below_new_column(prev.bottom())
                placed = True

            for from_, to in references_todo:

                # XXX: idea:
                # - start left of from_ (we wont the '*' symbols to be right
                # - use A*
                # - Treat commits as obstacles, paths not (sometimes we can
                # not avoid crossings)
                # - Can we modify the heuristic in A* to avoid path fields?
                #
                grid.add_path(from_, to)
            


            prev = s
            


    def topological_sort(self, elements):
        r = []

        def insert(element):
            parents = element.get_dependencies()
            for p in parents:
                if p not in r:
                    insert(p)
            r.append(element)

        for e in elements:
            if e not in r:
                insert(e)

        return r

    def compute_sequences(self, node):
        sequences = []

        def add(node, sequence):
            if node.sequence is not None:
                return

            sequence.append(node)

            parents = tuple(node.get_parents())

            if len(parents) > 1:
                sequence = None

            for p in parents:
                if sequence is None:
                    sequence = HistoryGraph.Sequence()
                    sequences.append(sequence)

                add(p, sequence)

                # If p has been added to a different sequence, add a reference
                if p.sequence is not node.sequence:
                    node.add_reference(p)

                sequence = None

        sequence = HistoryGraph.Sequence()
        sequences.append(sequence)
        add(node, sequence)

        return sequences




if __name__ == '__main__':

    class Node:
        def __init__(self, name):
            self.name = name
            self.references = []
            self.position = None
            self.column = None
            self.sequence = None
            self.parents = []

        def get_parents(self):
            return self.parents

        def add_reference(self, pos):
            self.references.append(pos)

        def __str__(self):
            return self.name

        def __repr__(self):
            return self.name

    nodes = {}
    for n in 'abcdefghi':
        nodes[n] = Node(n)

    def p(a, b):
        nodes[a].parents.append(nodes[b])

    p('b', 'a')
    p('c', 'b')
    p('d', 'c')
    p('e', 'd')

    p('f', 'b')
    p('g', 'f')

    p('h', 'e')
    p('h', 'g')
    p('i', 'h')

    hg = HistoryGraph()

    g = hg.compute(nodes['i'])
    print(g)





