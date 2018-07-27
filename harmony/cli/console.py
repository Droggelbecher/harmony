
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
        max_column_widths = [len(str(s)) for s in headers]
    elif rows:
        max_column_widths = [len(str(s)) for s in rows[0]]
    else:
        # No headers, no rows, there is really nothing to print for us.
        return

    for row in rows:
        max_column_widths = [
            max(c, len(str(s)))
            for c, s in zip(max_column_widths, row)
        ]

    def print_row(row):
        for s, w in zip(row, max_column_widths):
            ss = str(s)
            out.write(ss + filler * (w - len(ss)))
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


