import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


def _make_dispatch_html() -> str:
    def row(date: str, time: str, message: str) -> str:
        return f"""
        <tr class="toprow">
          <td>{date}</td>
          <td>{time}</td>
          <td style="display:none;">No</td>
          <td>{message}</td>
        </tr>
        """

    msg1 = """
    Automatic R&R Notification: test
    FDID: 62-B
    Call Type: Ambulance V.A.C.
    Address: 10 MAIN ST, LEVITTOWN
    C/S: A / B
    Additional Information: TEST
    CFS Number: 100
    Assigned Station: 290
    Unit: 292
    TX: 1/1/2026 10:00:00
    [2026-00000001 2933]
    """
    msg2 = """
    Automatic R&R Notification: test
    FDID: 69
    Call Type: MVA V.A.C. Calls
    Address: JERUSALEM AVE / TAILOR LN, LEVITTOWN
    C/S: C / D
    Additional Information: TEST
    CFS Number: 101
    Assigned Station: 290
    Unit: 690A
    TX: 1/1/2026 11:00:00
    [2026-00000001 2933]
    """
    msg3 = """
    Automatic R&R Notification: test
    FDID: 62-A
    Call Type: Ambulance V.A.C.
    Address: 55 CHESTNUT LN, LEVITTOWN
    C/S: E / F
    Additional Information: TEST
    CFS Number: 102
    Assigned Station: 290
    Unit: 290
    TX: 1/1/2026 12:00:00
    [2026-00000002 2933]
    """
    return f"""<html><table>{row("01/01/2026", "10:00:01", msg1)}{row("01/01/2026", "11:00:01", msg2)}{row("01/01/2026", "12:00:01", msg3)}</table></html>"""


def _parse_value(summary: str, key: str) -> str:
    m = re.search(rf"^{re.escape(key)}:\s*(.+)$", summary, flags=re.M)
    if not m:
        raise AssertionError(f"Missing key in summary: {key}")
    return m.group(1).strip()


class ParserRegressionTest(unittest.TestCase):
    def test_reused_incident_split_and_missed_outside_logic(self) -> None:
        parser = Path(__file__).resolve().parents[1] / "parse_dispatch_report.py"
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            dispatch = tmp_path / "Report.xls"
            eso = tmp_path / "Responses.csv"
            out = tmp_path / "summary.txt"
            dispatch.write_text(_make_dispatch_html(), encoding="utf-8")
            eso.write_text(
                "Incident Number,Unit,Scene Address 1\n"
                "AAA-1,292,10 MAIN ST\n",
                encoding="utf-8",
            )

            proc = subprocess.run(
                [
                    sys.executable,
                    str(parser),
                    str(dispatch),
                    "--eso-file",
                    str(eso),
                    "--exclude-units",
                    "290,291",
                    "--wlvac-units",
                    "292,293,294",
                    "-o",
                    str(out),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr or proc.stdout)
            summary = out.read_text(encoding="utf-8")

            self.assertEqual(_parse_value(summary, "Unique calls in report"), "3")
            self.assertEqual(_parse_value(summary, "Calls we went to"), "1")
            self.assertEqual(_parse_value(summary, "Calls missed"), "1")
            self.assertEqual(_parse_value(summary, "Calls likely handled by outside agency"), "1")


    def test_second_nines_detection(self) -> None:
        """A missed call during an active response should be flagged as a 2nd 9."""
        parser_script = Path(__file__).resolve().parents[1] / "parse_dispatch_report.py"

        def row(date: str, time: str, message: str) -> str:
            return f'<tr class="toprow"><td>{date}</td><td>{time}</td><td>addr</td><td>{message}</td></tr>'

        # Call 1: dispatched 10:00, unit 292 responds, in district at 11:00
        # Call 2: dispatched 10:30 (during call 1's busy window) — should be 2nd 9
        # Call 3: dispatched 12:00 (after call 1 cleared) — NOT a 2nd 9
        html = "<html><table>"
        html += row("01/05/2026", "10:00:00",
                    "Call Type: Test\nAddress: 10 MAIN ST\nCFS Number: 100\nUnit: 292\nTX: ok\n[2026-00001 X]")
        html += row("01/05/2026", "10:30:00",
                    "Call Type: Test\nAddress: 20 OAK AVE\nCFS Number: 101\nUnit: 292\nTX: ok\n[2026-00002 X]")
        html += row("01/05/2026", "12:00:00",
                    "Call Type: Test\nAddress: 30 ELM ST\nCFS Number: 102\nUnit: 292\nTX: ok\n[2026-00003 X]")
        html += "</table></html>"

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            dispatch = tmp_path / "Report.xls"
            eso = tmp_path / "Responses.csv"
            out = tmp_path / "summary.txt"
            dispatch.write_text(html, encoding="utf-8")
            # Only call 1 has an ESO match (responded). Calls 2 and 3 are missed.
            eso.write_text(
                "Incident Number,Unit,Scene Address 1,In District\n"
                "ESO-1,292,10 MAIN ST,2026-01-05 11:00:00.000\n",
                encoding="utf-8",
            )

            proc = subprocess.run(
                [
                    sys.executable,
                    str(parser_script),
                    str(dispatch),
                    "--eso-file",
                    str(eso),
                    "--exclude-units", "290,291",
                    "--wlvac-units", "292,293,294",
                    "-o", str(out),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr or proc.stdout)
            summary = out.read_text(encoding="utf-8")

            self.assertEqual(_parse_value(summary, "Calls we went to"), "1")
            self.assertEqual(_parse_value(summary, "Calls missed"), "2")
            # Call 2 (10:30) overlaps with call 1's 10:00-11:00 window → 2nd 9
            # Call 3 (12:00) does not overlap → not a 2nd 9
            self.assertEqual(_parse_value(summary, "Missed calls that were 2nd 9s"), "1")

    def test_in_district_parsed_from_eso(self) -> None:
        parser = Path(__file__).resolve().parents[1] / "parse_dispatch_report.py"
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            dispatch = tmp_path / "Report.xls"
            eso = tmp_path / "Responses.csv"
            out = tmp_path / "summary.txt"
            dispatch.write_text(_make_dispatch_html(), encoding="utf-8")
            eso.write_text(
                "Incident Number,Unit,Scene Address 1,In District\n"
                "AAA-1,292,10 MAIN ST,2026-01-01 11:00:00.000\n",
                encoding="utf-8",
            )

            proc = subprocess.run(
                [
                    sys.executable,
                    str(parser),
                    str(dispatch),
                    "--eso-file",
                    str(eso),
                    "--exclude-units",
                    "290,291",
                    "--wlvac-units",
                    "292,293,294",
                    "-o",
                    str(out),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr or proc.stdout)


if __name__ == "__main__":
    unittest.main()
