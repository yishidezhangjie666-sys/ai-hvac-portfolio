#!/usr/bin/env python3
"""Insert or replace the Mermaid workflow diagram near the top of README.md."""

from __future__ import annotations

from pathlib import Path
import re


README = Path(__file__).resolve().parents[1] / "README.md"
START = "<!-- FLOWCHART:START -->"
END = "<!-- FLOWCHART:END -->"
BLOCK = f"""{START}
```mermaid
flowchart LR
  E[\"数据输入<br/>electricity_cleaned.csv\"] --> F[\"特征提取<br/>feature_extract.py\"]
  F --> C[\"规则分类<br/>classify_profile.py\"]
  C --> V[\"可视化<br/>visualize.py\"]
  V --> R[\"报告<br/>report.md\"]
  CW[\"数据输入<br/>chilledwater_cleaned.csv\"] --> X[\"交叉验证<br/>chilledwater_check.py\"]
  C --> X
```
{END}"""


def main() -> None:
    content = README.read_text(encoding="utf-8")
    starts = content.count(START)
    ends = content.count(END)
    if starts != ends or starts > 1:
        raise ValueError("README.md must contain at most one balanced FLOWCHART marker block.")

    if starts == 1:
        pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), flags=re.DOTALL)
        updated, replacements = pattern.subn(BLOCK, content, count=1)
        if replacements != 1:
            raise ValueError("Could not replace the README flowchart marker block.")
    else:
        heading = re.search(r"^# .+$", content, flags=re.MULTILINE)
        if heading:
            position = heading.end()
            updated = content[:position] + "\n\n" + BLOCK + content[position:]
        else:
            updated = BLOCK + "\n\n" + content

    if updated != content:
        README.write_text(updated, encoding="utf-8")
    print(f"Inserted or refreshed Mermaid flowchart in {README}")


if __name__ == "__main__":
    main()
