"""Guards the README's terms-of-service caution and honest wording.

Run with: python -m pytest test_readme_copy.py
"""

import re
from pathlib import Path

README = (Path(__file__).parent / "README.md").read_text(encoding="utf-8")


def test_tos_caution_comes_before_feature_list():
    caution = re.search(r"terms of service", README, re.IGNORECASE)
    first_feature = README.find("## What's New")
    assert caution is not None, "README needs a terms-of-service caution"
    assert caution.start() < first_feature, "caution must appear before the feature list"


def test_no_evasion_framing():
    assert "anti-detection" not in README.lower()
    assert "avoid detection" not in README.lower()
