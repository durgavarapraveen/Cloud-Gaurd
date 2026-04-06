import logging

from scanners.AWS.utils import safe_call, paginate

logger = logging.getLogger(__name__)


def scan_ecs(session, region):

    logger.info(f"Scanning ECS in {region}...")

    client = session.client("ecs", region_name=region)

    results = []


# ──────────────────────────────────────────────
# CLUSTER SCAN
# ──────────────────────────────────────────────

    cluster_arns = paginate(
        client,
        "list_clusters",
        "clusterArns"
    )

    if cluster_arns:

        clusters_resp = safe_call(
            client.describe_clusters,
            clusters=cluster_arns,
            include=["SETTINGS", "STATISTICS", "TAGS"]
        )

        for cluster in clusters_resp.get("clusters", []) if clusters_resp else []:

            findings = []

            exec_config = cluster.get(
                "executeCommandConfiguration",
                {}
            )

            # Security checks

            if exec_config:

                if exec_config.get("logging") == "NONE":
                    findings.append({
                        "severity": "MEDIUM",
                        "issue": "ECS execute command logging disabled"
                    })

            else:

                findings.append({
                    "severity": "LOW",
                    "issue": "Execute command not configured"
                })


            # Container insights check

            insights_enabled = False

            for setting in cluster.get("settings", []):

                if setting.get("name") == "containerInsights":

                    if setting.get("value") == "enabled":
                        insights_enabled = True

            if not insights_enabled:

                findings.append({
                    "severity": "LOW",
                    "issue": "Container insights disabled"
                })


            results.append({

                "resource_type": "ecs_cluster",

                "resource_id":
                    cluster.get("clusterArn"),

                "resource_name":
                    cluster.get("clusterName"),

                "region":
                    region,


# Configuration block

                "configuration": {

                    "status":
                        cluster.get("status"),

                    "active_services":
                        cluster.get("activeServicesCount"),

                    "running_tasks":
                        cluster.get("runningTasksCount"),

                    "pending_tasks":
                        cluster.get("pendingTasksCount"),

                    "registered_instances":
                        cluster.get(
                            "registeredContainerInstancesCount"
                        ),

                    "settings":
                        cluster.get("settings", []),

                    "capacity_providers":
                        cluster.get("capacityProviders", []),

                    "execute_command_configuration":
                        exec_config

                },

                "tags":
                    cluster.get("tags", []),


# Security block

                "security": {

                    "status":
                        "PASS" if not findings else "FAIL",

                    "findings":
                        findings

                }

            })


# ──────────────────────────────────────────────
# TASK DEFINITIONS
# ──────────────────────────────────────────────


    task_def_arns = paginate(
        client,
        "list_task_definitions",
        "taskDefinitionArns",
        status="ACTIVE",
        sort="DESC"
    )


# keep latest revision per family

    seen_families = set()

    unique_arns = []

    for arn in task_def_arns:

        family = arn.rsplit(":", 1)[0]

        if family not in seen_families:

            seen_families.add(family)

            unique_arns.append(arn)



# configurable cap

    MAX_TASK_DEFS = 200


    for arn in unique_arns[:MAX_TASK_DEFS]:

        td_resp = safe_call(

            client.describe_task_definition,

            taskDefinition=arn,

            include=["TAGS"]

        )

        if not td_resp:

            continue


        td = td_resp.get("taskDefinition", {})

        findings = []


# Container security checks

        for container in td.get("containerDefinitions", []):

            cname = container.get("name")


            if container.get("privileged"):

                findings.append({

                    "severity": "HIGH",

                    "issue":
                        f"{cname} runs privileged container"

                })


            if container.get("user") == "root":

                findings.append({

                    "severity": "MEDIUM",

                    "issue":
                        f"{cname} runs as root user"

                })


            if not container.get(
                "readonlyRootFilesystem",
                False
            ):

                findings.append({

                    "severity": "LOW",

                    "issue":
                        f"{cname} root filesystem writable"

                })


            image = container.get("image", "")


            if ":latest" in image:

                findings.append({

                    "severity": "LOW",

                    "issue":
                        f"{cname} uses latest tag"

                })


            if container.get("environment"):

                findings.append({

                    "severity": "LOW",

                    "issue":
                        f"{cname} has environment variables (check secrets)"

                })


            if container.get("secrets"):

                findings.append({

                    "severity": "INFO",

                    "issue":
                        f"{cname} uses secrets manager"

                })


        results.append({

            "resource_type":
                "ecs_task_definition",

            "resource_id":
                td.get("taskDefinitionArn"),

            "resource_name":
                f"{td.get('family')}:{td.get('revision')}",

            "region":
                region,


# Configuration block

            "configuration": {

                "family":
                    td.get("family"),

                "revision":
                    td.get("revision"),

                "status":
                    td.get("status"),

                "network_mode":
                    td.get("networkMode"),

                "requires_compatibilities":
                    td.get(
                        "requiresCompatibilities",
                        []
                    ),

                "cpu":
                    td.get("cpu"),

                "memory":
                    td.get("memory"),

                "task_role_arn":
                    td.get("taskRoleArn"),

                "execution_role_arn":
                    td.get("executionRoleArn"),

                "container_definitions":
                    td.get(
                        "containerDefinitions",
                        []
                    ),

                "volumes":
                    td.get("volumes", [])

            },


            "tags":
                td_resp.get("tags", []),


# Security block

            "security": {

                "status":
                    "PASS" if not findings else "FAIL",

                "findings":
                    findings

            }

        })


    logger.info(
        f"  ECS ({region}): {len(results)} resources"
    )

    return results