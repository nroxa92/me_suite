"""
ME17Suite — Map Differ
Usporedba dvaju firmware fajlova na razini poznatih mapa.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .engine import ME17Engine
    from .map_finder import FoundMap


@dataclass
class CellDiff:
    row:     int
    col:     int
    raw1:    int
    raw2:    int
    disp1:   float
    disp2:   float

    @property
    def delta(self) -> float:
        return self.disp2 - self.disp1

    @property
    def delta_pct(self) -> float:
        if self.disp1 == 0:
            return 0.0 if self.disp2 == 0 else float("inf")
        return (self.disp2 - self.disp1) / abs(self.disp1) * 100.0


@dataclass
class MapDiff:
    name:      str
    category:  str
    address:   int
    rows:      int
    cols:      int
    unit:      str
    cells:     list[CellDiff] = field(default_factory=list)

    @property
    def changed_count(self) -> int:
        return len(self.cells)

    @property
    def total_cells(self) -> int:
        return self.rows * self.cols

    @property
    def changed_pct(self) -> float:
        if self.total_cells == 0: return 0.0
        return self.changed_count / self.total_cells * 100.0

    @property
    def max_delta(self) -> float:
        if not self.cells: return 0.0
        return max(abs(c.delta) for c in self.cells)

    @property
    def avg_delta(self) -> float:
        if not self.cells: return 0.0
        return sum(c.delta for c in self.cells) / len(self.cells)


class MapDiffer:
    """
    Uspoređuje dvije firmware binarne slike na razini poznatih ECU mapa.

    Upotreba:
        differ = MapDiffer(eng1, eng2)
        diffs  = differ.compare_all_maps()
        report = differ.generate_diff_report()
    """

    def __init__(self, eng1: "ME17Engine", eng2: "ME17Engine"):
        self._eng1 = eng1
        self._eng2 = eng2
        self._maps1: list["FoundMap"] = []
        self._maps2: list["FoundMap"] = []
        self._diffs: list[MapDiff] | None = None

    def _ensure_scanned(self):
        if self._maps1 and self._maps2:
            return
        from core.map_finder import MapFinder
        self._maps1 = MapFinder(self._eng1).scan_all()
        self._maps2 = MapFinder(self._eng2).scan_all()

    def compare_all_maps(self) -> list[MapDiff]:
        """
        Usporedi sve poznate mape između dva firmware fajla.
        Vraća listu MapDiff objekata (samo za mape s razlikama).
        """
        if self._diffs is not None:
            return self._diffs

        self._ensure_scanned()

        # Mapiraj fajl-2 mape po imenu
        fm2_by_name: dict[str, "FoundMap"] = {fm.defn.name: fm for fm in self._maps2}

        results: list[MapDiff] = []
        for fm1 in self._maps1:
            defn = fm1.defn
            fm2  = fm2_by_name.get(defn.name)
            if fm2 is None:
                continue

            d1 = fm1.display_values
            d2 = fm2.display_values
            r1 = fm1.raw_values
            r2 = fm2.raw_values

            if len(d1) != len(d2):
                continue

            cells = []
            for idx in range(len(d1)):
                if r1[idx] != r2[idx]:
                    row = idx // defn.cols
                    col = idx %  defn.cols
                    cells.append(CellDiff(
                        row=row, col=col,
                        raw1=r1[idx], raw2=r2[idx],
                        disp1=d1[idx], disp2=d2[idx],
                    ))

            if cells:
                results.append(MapDiff(
                    name=defn.name,
                    category=defn.category,
                    address=defn.address,
                    rows=defn.rows,
                    cols=defn.cols,
                    unit=defn.unit,
                    cells=cells,
                ))

        results.sort(key=lambda x: (-x.changed_count, x.name))
        self._diffs = results
        return results

    def generate_diff_report(self) -> str:
        """Generira Markdown diff report."""
        diffs = self.compare_all_maps()

        info1 = self._eng1.get_info() if hasattr(self._eng1, "get_info") else None
        info2 = self._eng2.get_info() if hasattr(self._eng2, "get_info") else None

        sw1 = info1.sw_id if info1 else Path(getattr(self._eng1, "path", "?")).name
        sw2 = info2.sw_id if info2 else Path(getattr(self._eng2, "path", "?")).name

        lines = [
            "# ME17Suite — Map Diff Report",
            "",
            f"**Datum**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"**Fajl 1**: {sw1}",
            f"**Fajl 2**: {sw2}",
            "",
            f"**Promijenjene mape**: {len(diffs)}",
            "",
            "---",
            "",
            "## Sažetak promjena",
            "",
            "| Mapa | Kat. | Adresa | Promijenjeno | Maks Δ | Prosj. Δ |",
            "|------|------|--------|-------------|--------|---------|",
        ]

        for d in diffs:
            lines.append(
                f"| {d.name} | {d.category} | 0x{d.address:06X} "
                f"| {d.changed_count}/{d.total_cells} ({d.changed_pct:.0f}%) "
                f"| {d.max_delta:+.3f} {d.unit} "
                f"| {d.avg_delta:+.3f} {d.unit} |"
            )

        lines += ["", "---", "", "## Detalji po mapi", ""]

        for d in diffs:
            lines += [
                f"### {d.name}",
                f"- **Adresa**: 0x{d.address:06X}",
                f"- **Dimenzije**: {d.rows}×{d.cols}",
                f"- **Promijenjenih ćelija**: {d.changed_count}/{d.total_cells}",
                f"- **Jedinica**: {d.unit}",
                "",
                "| Red | Kol | Fajl 1 | Fajl 2 | Δ |",
                "|-----|-----|--------|--------|---|",
            ]
            # Maks 20 ćelija u reportu
            for c in sorted(d.cells, key=lambda x: abs(x.delta), reverse=True)[:20]:
                lines.append(
                    f"| {c.row} | {c.col} "
                    f"| {c.disp1:.4g} | {c.disp2:.4g} "
                    f"| {c.delta:+.4g} |"
                )
            if len(d.cells) > 20:
                lines.append(f"| *...i još {len(d.cells)-20} ćelija* | | | | |")
            lines.append("")

        return "\n".join(lines)

    def get_values_for_map(self, map_name: str) -> tuple[list[float], list[float]] | None:
        """
        Vraća (display_values_1, display_values_2) za zadanu mapu.
        None ako mapa nije pronađena u oba fajla.
        """
        self._ensure_scanned()
        fm1 = next((fm for fm in self._maps1 if fm.defn.name == map_name), None)
        fm2 = next((fm for fm in self._maps2 if fm.defn.name == map_name), None)
        if fm1 is None or fm2 is None:
            return None
        return fm1.display_values, fm2.display_values
