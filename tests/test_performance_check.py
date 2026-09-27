from scripts import performance_check


def test_performance_summary_calculates_medians():
    results = [
        {
            "category": "simple",
            "first_token_ms": 100.0,
            "total_ms": 500.0,
            "error": None,
        },
        {
            "category": "simple",
            "first_token_ms": 200.0,
            "total_ms": 700.0,
            "error": None,
        },
        {
            "category": "complex",
            "first_token_ms": 1000.0,
            "total_ms": 5000.0,
            "error": None,
        },
        {
            "category": "complex",
            "first_token_ms": None,
            "total_ms": None,
            "error": "failed",
        },
    ]

    summary = (
        performance_check
        .build_summary(
            results
        )
    )

    assert (
        summary["simple"][
            "median_first_token_ms"
        ]
        == 150.0
    )
    assert (
        summary["simple"][
            "median_total_ms"
        ]
        == 600.0
    )
    assert (
        summary["complex"][
            "successful"
        ]
        == 1
    )


def test_benchmark_contains_simple_and_complex_cases():
    categories = {
        case["category"]
        for case in (
            performance_check
            .CASES
        )
    }

    assert categories == {
        "simple",
        "complex",
    }


def test_benchmark_records_first_token_and_total_fields():
    expected = {
        "simple_name",
        "simple_capabilities",
        "complex_pipeline",
        "complex_knowledge",
    }

    names = {
        case["name"]
        for case in (
            performance_check
            .CASES
        )
    }

    assert names == expected
