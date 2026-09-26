from tools import cloud_tools


def test_ec2_inventory_is_read_only_and_region_scoped(
    monkeypatch,
):
    captured = {}

    def fake_run(
        command,
        timeout=60,
    ):
        captured["command"] = command
        captured["timeout"] = timeout
        return "ok"

    monkeypatch.setattr(
        cloud_tools,
        "_run_command",
        fake_run,
    )

    result = cloud_tools.aws_ec2_instances(
        region="eu-west-2"
    )

    command = captured["command"]

    assert result == "ok"
    assert command[:3] == [
        "aws",
        "ec2",
        "describe-instances",
    ]
    assert "--region" in command
    assert "eu-west-2" in command
    assert "terminate-instances" not in command


def test_ecs_services_requires_cluster():
    result = cloud_tools.aws_ecs_services(
        cluster=""
    )

    assert (
        "cluster cannot be empty"
        in result
    )


def test_route53_limit_is_bounded(
    monkeypatch,
):
    captured = {}

    def fake_run(
        command,
        timeout=60,
    ):
        captured["command"] = command
        return "ok"

    monkeypatch.setattr(
        cloud_tools,
        "_run_command",
        fake_run,
    )

    cloud_tools.aws_route53_hosted_zones(
        limit=1000
    )

    command = captured["command"]
    index = command.index(
        "--max-items"
    )

    assert (
        command[index + 1]
        == "100"
    )


def test_s3_inventory_uses_list_buckets(
    monkeypatch,
):
    captured = {}

    def fake_run(
        command,
        timeout=60,
    ):
        captured["command"] = command
        return "ok"

    monkeypatch.setattr(
        cloud_tools,
        "_run_command",
        fake_run,
    )

    cloud_tools.aws_s3_buckets()

    assert captured["command"][:3] == [
        "aws",
        "s3api",
        "list-buckets",
    ]
