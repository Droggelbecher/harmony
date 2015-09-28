

class Grid:

    class Row:
        def __init__(self, grid):
            self.grid = grid
            self.data = None
            self.offset = None

        def __getitem__(self, i):
            if self.offset is None or i < self.offset or i >= self.offset + len(self.data):
                return ' '
            return self.data[i - self.offset]

        def __setitem__(self, i, value):
            if self.data is None:
                self.data = [value]
                self.offset = i

            elif i < self.offset:
                self.data = [value] + ([' '] * (i - self.offset - 1)) + self.data
                self.offset = i

            elif i >= self.offset + len(self.data):
                self.data += [' '] * (i - (self.offset + len(self.data))) + [value]

            else:
                self.data[i - self.offset] = value

        def insert_column(self, i):
            if self.data is None: return

            if i <= self.offset:
                self.offset += 1

            elif i <= self.offset + len(self.data):
                self.data = self.data[:i - self.offset] + [' '] + self.data[i - self.offset:]

            # else, i is right of our data so we dont care

        def find_free_index(self):
            if self.data is None:
                return 0

            try:
                return self.data.index(' ')
            except ValueError:
                return self.offset + len(self.data)


    def __init__(self):
        self.rows = []

    def add_row(self):
        row = Grid.Row(self)
        self.rows.append(row)
        return row

    def insert_column(self, index):
        for row in self.rows:
            row.insert_column(index)

    def render(self):
        min_offset = min(r.offset for r in self.rows)
        for i, row in enumerate(self.rows[::-1]):
            nodename = ''
            if hasattr(row, 'nodename'):
                nodename = row.nodename

            print('  ' * (row.offset - min_offset) + ' ' + ' '.join(row.data) + '\t\t'
                    + nodename)
                


class HistoryGraph:

    def compute(self, nodes):
        """
        @param nodes nodes ordered by date, descending
        """
        

        g = Grid()

        # target => index
        open_connections = []

        for node in nodes:
            # add a new row on top
            row = g.add_row()

            # first place the new node if it is referenced
            # Also resolve all additional references to this node

            node_pos = None
            delete_indices = []
            for i, (open_index, open_node) in enumerate(open_connections):
                print(node, i, open_index, open_node)
                # Is currently added node referenced from here?
                if open_node is node:
                    # Is current node not yet placed?
                    if node_pos is None:
                        # Great! Just place it directly above referencer
                        node_pos = open_index
                        row[node_pos] = '*'
                        delete_indices.append(i)
                        #del open_connections[i]
                    else:
                        # Its placed already, this might get tricky
                        # TODO: what do we do here?
                        # (a) draw a horizontal line straight to the node.
                        #     What if multiple referencers want this node? -->
                        #       we can join the lines
                        #     What if a vertical line already blocks the path?
                        #       we could simulate a crossing, but that would
                        #       make things complicated
                        # (b) insert additional helper lines/columns, again,
                        #     we'll have to handle crossings and things WILL
                        #     get ugly...
                        # (c) be a lazy ass SOB and just invent a new symbol
                        #     for it, effectively drawing this DAG as a tree.
                        row[open_index] = '+'
                        #del open_connections[i]
                        delete_indices.append(i)

            # Now delete all the connections we just handled

            # sort delete indices reverse, this way no deletion messes
            # up the index of any future one
            delete_indices.sort(key = lambda v: -v)
            for i in delete_indices:
                del open_connections[i]

            # extend all open connections
            open_connections_new = []
            insert_positions = []

            print("node_pos=", node_pos, "open_connections=", open_connections)

            for index, target in open_connections:
                print("conn (",target, ",",index,") row[idx]=", row[index])
                if row[index] == ' ':
                    row[index] = '|'
                    open_connections_new.append((index, target))

                else:
                    if row[index - 1] == ' ':
                        row[index - 1] = '\\'
                        open_connections_new.append((index - 1, target))
                    elif row[index + 1] == ' ':
                        row[index + 1] = '\\'
                        open_connections_new.append((index + 1, target))
                    else:
                        # Insert a new column left of index,
                        # that should repair the problem.
                        # This call also fixes indices in row

                        g.insert_column(index)

                        # Fix indices in open_connections

                        for i in range(len(open_connections)):
                            if open_connections[i][0] >= index:
                                open_connections[i] = (open_connections[i][0] + 1, open_connections[i][1])

                        row[index - 1] = '\\'
                        open_connections_new.append(index - 1, target)

            open_connections = open_connections_new

            if node_pos is None:
                node_pos = row.find_free_index()
                row[node_pos] = '*'

            row.nodename = node.name

            for parent in node.parents:
                open_connections.append((node_pos, parent))
            print("open_connections'=", open_connections)

        g.render()



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
        def __init__(self, name, t):
            self.name = name
            self.t = t
            self.parents = []

        def __str__(self):
            return self.name

        def __repr__(self):
            return self.name

    nodes = {}
    def add_node(n, t):
        nodes[n] = Node(n, t)

    add_node('a',   0)
    add_node('b',  10)
    add_node('c',  20)
    add_node('f',  30)
    add_node('d',  40)
    add_node('e',  50)
    add_node('g',  60)
    add_node('h',  70)
    add_node('i',  80)


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

    ordered_nodes = sorted(nodes.values(), key=lambda v: -v.t)
    print(ordered_nodes)


    g = hg.compute(ordered_nodes)
    print(g)





