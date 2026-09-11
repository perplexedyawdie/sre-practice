from __future__ import annotations

import os
from pathlib import Path

from streamlit.testing.v1 import AppTest


APP_DIR = Path(__file__).resolve().parents[1]


def test_app_starts_in_study_mode(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("SRE_LAB_FLAG_API_URL", "http://127.0.0.1:1/feature/api")
    monkeypatch.setenv("SRE_LAB_STATE_DIR", str(tmp_path / "state"))
    old_cwd = Path.cwd()
    try:
        os.chdir(APP_DIR)
        app = AppTest.from_file(str(APP_DIR / "app.py"), default_timeout=10).run()
    finally:
        os.chdir(old_cwd)

    assert not app.exception
    assert app.title[0].value == "E-Commerce SRE Learning Lab"
    assert any("Study mode" in warning.value for warning in app.warning)

    next_button = next(button for button in app.sidebar.button if button.label == "Pick another incomplete exercise")
    app = next_button.click().run()
    assert not app.exception
