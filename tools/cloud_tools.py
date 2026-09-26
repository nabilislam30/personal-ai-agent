import shutil
import subprocess


MAX_OUTPUT = 20_000


def _run_command(
    command: list[str],
    timeout: int = 60,
) -> str:
    executable = command[0]

    if shutil.which(executable) is None:
        return (
            f"Error: {executable} CLI is not installed "
            "or is not available in PATH."
        )

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return f"Error: {executable} command timed out."

    output = result.stdout.strip()

    if result.stderr.strip():
        if output:
            output += "\n"
        output += result.stderr.strip()

    if not output:
        output = "(No output)"

    if len(output) > MAX_OUTPUT:
        output = (
            output[:MAX_OUTPUT]
            + "\n[Output truncated]"
        )

    return (
        f"Exit code: {result.returncode}\n"
        f"{output}"
    )


def _region_args(
    region: str,
) -> list[str]:
    cleaned = region.strip()

    if not cleaned:
        return []

    return [
        "--region",
        cleaned,
    ]


def _bounded_limit(
    limit: int,
    maximum: int = 100,
) -> int:
    return max(
        1,
        min(int(limit), maximum),
    )


def aws_identity() -> str:
    """
    Show the current AWS CLI identity without changing resources.
    """

    return _run_command(
        [
            "aws",
            "sts",
            "get-caller-identity",
            "--output",
            "json",
        ]
    )


def aws_region() -> str:
    """
    Show the AWS CLI configured default region.

    This is read-only.
    """

    return _run_command(
        [
            "aws",
            "configure",
            "get",
            "region",
        ]
    )


def aws_ec2_instances(
    region: str = "",
) -> str:
    """
    List selected EC2 instance metadata.

    This is read-only and excludes user data and credentials.
    """

    command = [
        "aws",
        "ec2",
        "describe-instances",
        "--query",
        (
            "Reservations[].Instances[].{"
            "InstanceId:InstanceId,"
            "State:State.Name,"
            "Type:InstanceType,"
            "AvailabilityZone:Placement.AvailabilityZone,"
            "VpcId:VpcId,"
            "SubnetId:SubnetId,"
            "PrivateIp:PrivateIpAddress,"
            "PublicIp:PublicIpAddress"
            "}"
        ),
        "--output",
        "json",
    ]

    command.extend(
        _region_args(region)
    )

    return _run_command(command)


def aws_ecs_clusters(
    region: str = "",
) -> str:
    """
    List ECS cluster ARNs.

    This is read-only.
    """

    command = [
        "aws",
        "ecs",
        "list-clusters",
        "--output",
        "json",
    ]

    command.extend(
        _region_args(region)
    )

    return _run_command(command)


def aws_ecs_services(
    cluster: str,
    region: str = "",
    limit: int = 20,
) -> str:
    """
    List ECS services for one cluster.

    This is read-only.
    """

    if not cluster.strip():
        return "Error: ECS cluster cannot be empty."

    safe_limit = _bounded_limit(
        limit,
        maximum=100,
    )

    command = [
        "aws",
        "ecs",
        "list-services",
        "--cluster",
        cluster.strip(),
        "--max-results",
        str(safe_limit),
        "--output",
        "json",
    ]

    command.extend(
        _region_args(region)
    )

    return _run_command(command)


def aws_eks_clusters(
    region: str = "",
) -> str:
    """
    List EKS cluster names.

    This is read-only.
    """

    command = [
        "aws",
        "eks",
        "list-clusters",
        "--output",
        "json",
    ]

    command.extend(
        _region_args(region)
    )

    return _run_command(command)


def aws_cloudwatch_alarms(
    region: str = "",
    limit: int = 50,
) -> str:
    """
    List selected CloudWatch metric alarm metadata.

    This is read-only.
    """

    safe_limit = _bounded_limit(
        limit,
        maximum=100,
    )

    command = [
        "aws",
        "cloudwatch",
        "describe-alarms",
        "--max-records",
        str(safe_limit),
        "--query",
        (
            "MetricAlarms[].{"
            "AlarmName:AlarmName,"
            "State:StateValue,"
            "Namespace:Namespace,"
            "MetricName:MetricName,"
            "Updated:StateUpdatedTimestamp"
            "}"
        ),
        "--output",
        "json",
    ]

    command.extend(
        _region_args(region)
    )

    return _run_command(command)


def aws_route53_hosted_zones(
    limit: int = 50,
) -> str:
    """
    List Route 53 hosted zones.

    Route 53 is global, so no region is required.
    """

    safe_limit = _bounded_limit(
        limit,
        maximum=100,
    )

    return _run_command(
        [
            "aws",
            "route53",
            "list-hosted-zones",
            "--max-items",
            str(safe_limit),
            "--query",
            (
                "HostedZones[].{"
                "Id:Id,"
                "Name:Name,"
                "PrivateZone:Config.PrivateZone,"
                "RecordCount:ResourceRecordSetCount"
                "}"
            ),
            "--output",
            "json",
        ]
    )


def aws_s3_buckets() -> str:
    """
    List S3 bucket names and creation dates.

    This is read-only.
    """

    return _run_command(
        [
            "aws",
            "s3api",
            "list-buckets",
            "--query",
            "Buckets[].{Name:Name,CreationDate:CreationDate}",
            "--output",
            "json",
        ]
    )
