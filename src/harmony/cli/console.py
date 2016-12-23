
import sys

def write_table(rows, headers = None):
    """
    headers: indexable of strings of length W
    rows: indexable of (indexable of strings of length W)
    """

    spacer = '\t'
    filler = ' '

    out = sys.stdout

    if headers is not None:
        max_column_widths = [len(s) for s in headers]
    else:
        max_column_widths = [len(s) for s in rows[0]]

    for row in rows:
        max_column_widths = [
            max(c, len(s))
            for c, s in zip(max_column_widths, row)
        ]

    def print_row(row):
        for s, w in zip(row, max_column_widths):
            out.write(s + filler * (w - len(s)))
            out.write(spacer)
        out.write('\n')

    if headers is not None:
        print_row(headers)
        out.write("-" * (sum(max_column_widths) + len(spacer) * len(headers)) + '\n')

    for row in rows:
        print_row(row)

def write_list(elements):
    out = sys.stdout

    for e in elements:
        out.write(e + '\n')


