from router import (
    history_limit_for_route,
    route_request,
)


def test_simple_question_uses_fast_path():
    route = route_request(
        "What is your name?"
    )

    assert (
        route.name
        == "simple_chat"
    )


def test_latest_failed_pipeline_is_deterministic():
    route = route_request(
        "Investigate the most recent failed GitHub Actions run."
    )

    assert (
        route.name
        == "pipeline_latest_failure"
    )


def test_knowledge_question_routes_to_knowledge():
    route = route_request(
        "What does my knowledge base say about Kubernetes?"
    )

    assert (
        route.name
        == "knowledge"
    )


def test_aws_question_routes_to_aws():
    route = route_request(
        "Show my EC2 instances in eu-west-2."
    )

    assert route.name == "aws"


def test_simple_history_window_is_smaller_than_tool_window():
    simple = route_request(
        "Hello"
    )
    aws = route_request(
        "Show my AWS EC2 instances"
    )

    assert (
        history_limit_for_route(
            simple
        )
        < history_limit_for_route(
            aws
        )
    )
