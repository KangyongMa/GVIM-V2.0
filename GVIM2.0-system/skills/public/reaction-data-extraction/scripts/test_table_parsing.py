#!/usr/bin/env python3
"""Focused tests for MinerU table formats used by reaction extraction."""

from reaction_data_extraction import extract_tables, parse_reaction_table


def test_html_table() -> None:
    source = """
    <table>
      <tr><td>Entry</td><td>Catalyst</td><td>Solvent</td><td>T (°C)</td><td>Yield (%)</td></tr>
      <tr><td>1</td><td>$Cu(im)_2$</td><td>$H_2O$</td><td>50</td><td>80</td></tr>
    </table>
    """
    tables = extract_tables(source)
    assert len(tables) == 1
    reactions = parse_reaction_table(tables[0])
    assert reactions == [
        {
            "reaction_id": "RXN_T00_001",
            "entry": "1",
            "catalyst": "$Cu(im)_2$",
            "solvent": "$H_2O$",
            "temperature": "50",
            "yield_value": 80.0,
            "yield_raw": "80",
        }
    ]


if __name__ == "__main__":
    test_html_table()
    print("ok")
