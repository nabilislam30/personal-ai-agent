from pathlib import Path


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)


def test_google_style_home_ui_markers_present():
    html = (
        PROJECT_ROOT
        / "templates"
        / "index.html"
    ).read_text(
        encoding="utf-8"
    )

    assert (
        "What can I help with?"
        in html
    )
    assert (
        'placeholder="Ask anything"'
        in html
    )
    assert (
        "Search conversations"
        in html
    )
    assert (
        "quick-action"
        in html
    )


def test_performance_details_are_collapsed_by_default():
    html = (
        PROJECT_ROOT
        / "templates"
        / "index.html"
    ).read_text(
        encoding="utf-8"
    )

    assert (
        'document.createElement("details")'
        in html
    )
    assert (
        'summary.textContent =\n        "Details";'
        in html
    )
