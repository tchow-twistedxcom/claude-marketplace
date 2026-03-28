#!/usr/bin/env python3
"""
MongoDB Atlas Admin API v2 CLI

Execute Atlas API operations for monitoring alerts, clusters, and performance metrics.
Uses HTTP Digest Authentication with Atlas API keys.

Environment Variables:
  ATLAS_PUBLIC_KEY  - Atlas API public key
  ATLAS_PRIVATE_KEY - Atlas API private key
  ATLAS_PROJECT_ID  - Default project ID (optional)

Usage:
  python3 atlas_api.py alerts list [--since DAYS] [--limit N] [--all]
  python3 atlas_api.py alerts list --status open
  python3 atlas_api.py alerts get ALERT_ID [--project PROJECT_ID]
  python3 atlas_api.py alerts ack ALERT_ID [--comment COMMENT] [--project PROJECT_ID]
  python3 atlas_api.py clusters list [--project PROJECT_ID]
  python3 atlas_api.py clusters status CLUSTER_NAME [--project PROJECT_ID]
  python3 atlas_api.py metrics --cluster CLUSTER_NAME [--project PROJECT_ID]
  python3 atlas_api.py projects list
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from collections import Counter

try:
    import requests
    from requests.auth import HTTPDigestAuth
except ImportError:
    print("ERROR: 'requests' library required. Install with: pip install requests")
    sys.exit(1)

# API Configuration
BASE_URL = "https://cloud.mongodb.com/api/atlas/v2"
API_VERSION = "2024-08-05"

# Default credentials from environment
DEFAULT_PUBLIC_KEY = os.environ.get("ATLAS_PUBLIC_KEY", "")
DEFAULT_PRIVATE_KEY = os.environ.get("ATLAS_PRIVATE_KEY", "")
DEFAULT_PROJECT_ID = os.environ.get("ATLAS_PROJECT_ID", "")


def parse_timestamp(ts: str) -> Optional[datetime]:
    """Parse ISO timestamp to datetime object"""
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except:
        return None


class AtlasClient:
    """MongoDB Atlas Admin API Client"""

    def __init__(self, public_key: str, private_key: str, project_id: str = ""):
        self.public_key = public_key
        self.private_key = private_key
        self.project_id = project_id
        self.auth = HTTPDigestAuth(public_key, private_key)
        self.headers = {
            "Accept": f"application/vnd.atlas.{API_VERSION}+json",
            "Content-Type": "application/json"
        }

    def _request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        """Make authenticated API request"""
        url = f"{BASE_URL}{endpoint}"

        try:
            response = requests.request(
                method=method,
                url=url,
                auth=self.auth,
                headers=self.headers,
                json=data,
                timeout=30
            )

            if response.status_code == 401:
                raise Exception("Authentication failed - check API key credentials")
            elif response.status_code == 403:
                raise Exception("Access forbidden - verify IP is in Atlas access list")
            elif response.status_code == 404:
                raise Exception(f"Resource not found: {endpoint}")
            elif response.status_code >= 400:
                error_msg = response.json().get("detail", response.text)
                raise Exception(f"API Error ({response.status_code}): {error_msg}")

            return response.json() if response.text else {}

        except requests.exceptions.Timeout:
            raise Exception("Request timed out - try again")
        except requests.exceptions.ConnectionError:
            raise Exception("Connection failed - check network connectivity")

    def get(self, endpoint: str) -> Dict:
        return self._request("GET", endpoint)

    def patch(self, endpoint: str, data: Dict) -> Dict:
        return self._request("PATCH", endpoint, data)

    # ============ Projects ============

    def list_projects(self) -> List[Dict]:
        """List all accessible projects"""
        result = self.get("/groups")
        return result.get("results", [])

    # ============ Alerts ============

    def list_alerts(self, project_id: str = None, status: str = None,
                    limit: int = 100) -> List[Dict]:
        """List alerts for a project with optional filtering"""
        pid = project_id or self.project_id
        if not pid:
            raise Exception("Project ID required - use --project or set ATLAS_PROJECT_ID")

        params = []
        if status:
            params.append(f"status={status.upper()}")
        if limit:
            params.append(f"itemsPerPage={limit}")

        endpoint = f"/groups/{pid}/alerts"
        if params:
            endpoint += "?" + "&".join(params)

        result = self.get(endpoint)
        return result.get("results", [])

    def get_alert(self, alert_id: str, project_id: str = None) -> Dict:
        """Get specific alert details"""
        pid = project_id or self.project_id
        if not pid:
            raise Exception("Project ID required")

        return self.get(f"/groups/{pid}/alerts/{alert_id}")

    def acknowledge_alert(self, alert_id: str, comment: str = None,
                          project_id: str = None) -> Dict:
        """Acknowledge an alert"""
        pid = project_id or self.project_id
        if not pid:
            raise Exception("Project ID required")

        data = {
            "acknowledgedUntil": "2099-12-31T23:59:59Z",  # Acknowledge indefinitely
        }
        if comment:
            data["acknowledgementComment"] = comment

        return self.patch(f"/groups/{pid}/alerts/{alert_id}", data)

    # ============ Clusters ============

    def list_clusters(self, project_id: str = None) -> List[Dict]:
        """List all clusters in a project"""
        pid = project_id or self.project_id
        if not pid:
            raise Exception("Project ID required")

        result = self.get(f"/groups/{pid}/clusters")
        return result.get("results", [])

    def get_cluster(self, cluster_name: str, project_id: str = None) -> Dict:
        """Get cluster details"""
        pid = project_id or self.project_id
        if not pid:
            raise Exception("Project ID required")

        return self.get(f"/groups/{pid}/clusters/{cluster_name}")

    # ============ Metrics ============

    def list_processes(self, project_id: str = None) -> List[Dict]:
        """List all processes (for metrics)"""
        pid = project_id or self.project_id
        if not pid:
            raise Exception("Project ID required")

        result = self.get(f"/groups/{pid}/processes")
        return result.get("results", [])

    def get_process_metrics(self, process_id: str, project_id: str = None,
                           period: str = "PT1H", granularity: str = "PT5M") -> Dict:
        """Get process metrics"""
        pid = project_id or self.project_id
        if not pid:
            raise Exception("Project ID required")

        # Common metrics
        metrics = [
            "SYSTEM_CPU_USER",
            "SYSTEM_MEMORY_USED",
            "CONNECTIONS",
            "OPCOUNTER_CMD",
            "OPCOUNTER_QUERY",
            "OPCOUNTER_INSERT",
            "OPCOUNTER_UPDATE",
            "OPCOUNTER_DELETE"
        ]

        endpoint = (f"/groups/{pid}/processes/{process_id}/measurements"
                   f"?granularity={granularity}&period={period}"
                   f"&m={'&m='.join(metrics)}")

        return self.get(endpoint)


# ============ Output Formatting ============

def format_timestamp(ts: str) -> str:
    """Format ISO timestamp to readable format"""
    if not ts:
        return "N/A"
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except:
        return ts


def print_alerts_summary(alerts: List[Dict]):
    """Print summary statistics for alerts"""
    if not alerts:
        return

    by_status = Counter(a.get('status') for a in alerts)
    by_type = Counter(a.get('eventTypeName') for a in alerts)

    dates = [parse_timestamp(a.get('created', '')) for a in alerts]
    dates = [d for d in dates if d]  # Filter None values

    if dates:
        min_date = min(dates).strftime("%Y-%m-%d")
        max_date = max(dates).strftime("%Y-%m-%d")
        date_range = f"{min_date} to {max_date}"
    else:
        date_range = "N/A"

    print(f"\n{'─'*60}")
    print(f"Summary:")
    print(f"  Total:      {len(alerts)} alerts")
    print(f"  Open:       {by_status.get('OPEN', 0)}")
    print(f"  Closed:     {by_status.get('CLOSED', 0)}")
    print(f"  Date Range: {date_range}")
    print(f"\n  Top Alert Types:")
    for alert_type, count in by_type.most_common(5):
        print(f"    {alert_type}: {count}")


def print_alerts(alerts: List[Dict], format_type: str = "table", show_summary: bool = True):
    """Print alerts in specified format"""
    if format_type == "json":
        print(json.dumps(alerts, indent=2))
        return

    if not alerts:
        print("No alerts found.")
        return

    print(f"\n{'='*80}")
    print(f"{'ALERT ID':<26} {'TYPE':<25} {'STATUS':<12} {'CREATED':<20}")
    print(f"{'='*80}")

    for alert in alerts:
        print(f"{alert.get('id', 'N/A'):<26} "
              f"{alert.get('eventTypeName', 'N/A')[:24]:<25} "
              f"{alert.get('status', 'N/A'):<12} "
              f"{format_timestamp(alert.get('created', '')):<20}")

        # Show metric if available
        if alert.get('currentValue'):
            metric = alert['currentValue']
            print(f"  └─ Value: {metric.get('number', 'N/A')} {metric.get('units', '')}")

    print(f"\nTotal: {len(alerts)} alert(s)")

    if show_summary:
        print_alerts_summary(alerts)


def print_clusters(clusters: List[Dict], format_type: str = "table"):
    """Print clusters in specified format"""
    if format_type == "json":
        print(json.dumps(clusters, indent=2))
        return

    if not clusters:
        print("No clusters found.")
        return

    print(f"\n{'='*90}")
    print(f"{'NAME':<25} {'STATE':<15} {'TYPE':<15} {'VERSION':<10} {'REGION':<20}")
    print(f"{'='*90}")

    for cluster in clusters:
        # Get region from first provider settings
        region = "N/A"
        if cluster.get('providerSettings'):
            region = cluster['providerSettings'].get('regionName', 'N/A')
        elif cluster.get('replicationSpecs'):
            specs = cluster['replicationSpecs']
            if specs and specs[0].get('regionConfigs'):
                region = specs[0]['regionConfigs'][0].get('regionName', 'N/A')

        print(f"{cluster.get('name', 'N/A'):<25} "
              f"{cluster.get('stateName', 'N/A'):<15} "
              f"{cluster.get('clusterType', 'N/A'):<15} "
              f"{cluster.get('mongoDBVersion', 'N/A'):<10} "
              f"{region:<20}")

    print(f"\nTotal: {len(clusters)} cluster(s)")


def print_cluster_status(cluster: Dict, format_type: str = "table"):
    """Print detailed cluster status"""
    if format_type == "json":
        print(json.dumps(cluster, indent=2))
        return

    print(f"\n{'='*60}")
    print(f"Cluster: {cluster.get('name', 'N/A')}")
    print(f"{'='*60}")
    print(f"State:           {cluster.get('stateName', 'N/A')}")
    print(f"Type:            {cluster.get('clusterType', 'N/A')}")
    print(f"MongoDB Version: {cluster.get('mongoDBVersion', 'N/A')}")
    print(f"Paused:          {cluster.get('paused', False)}")
    print(f"Backup Enabled:  {cluster.get('backupEnabled', False)}")
    print(f"Encryption:      {cluster.get('encryptionAtRestProvider', 'NONE')}")

    # Connection strings
    if cluster.get('connectionStrings'):
        cs = cluster['connectionStrings']
        print(f"\nConnection Strings:")
        if cs.get('standardSrv'):
            print(f"  Standard SRV: {cs['standardSrv']}")
        if cs.get('privateSrv'):
            print(f"  Private SRV:  {cs['privateSrv']}")


def print_projects(projects: List[Dict], format_type: str = "table"):
    """Print projects in specified format"""
    if format_type == "json":
        print(json.dumps(projects, indent=2))
        return

    if not projects:
        print("No projects found.")
        return

    print(f"\n{'='*70}")
    print(f"{'PROJECT ID':<26} {'NAME':<30} {'CLUSTER COUNT':<12}")
    print(f"{'='*70}")

    for project in projects:
        print(f"{project.get('id', 'N/A'):<26} "
              f"{project.get('name', 'N/A')[:29]:<30} "
              f"{project.get('clusterCount', 0):<12}")

    print(f"\nTotal: {len(projects)} project(s)")


def print_metrics(metrics: Dict, format_type: str = "table"):
    """Print process metrics"""
    if format_type == "json":
        print(json.dumps(metrics, indent=2))
        return

    measurements = metrics.get('measurements', [])
    if not measurements:
        print("No metrics available.")
        return

    print(f"\n{'='*60}")
    print("Process Metrics")
    print(f"{'='*60}")

    for m in measurements:
        name = m.get('name', 'Unknown')
        units = m.get('units', '')
        data_points = m.get('dataPoints', [])

        if data_points:
            # Get the latest non-null value
            latest = None
            for dp in reversed(data_points):
                if dp.get('value') is not None:
                    latest = dp
                    break

            if latest:
                value = latest.get('value', 'N/A')
                timestamp = format_timestamp(latest.get('timestamp', ''))
                print(f"{name}: {value} {units} (at {timestamp})")


# ============ CLI Commands ============

def cmd_alerts_list(client: AtlasClient, args):
    """Handle 'alerts list' command"""
    # Get alerts from API
    alerts = client.list_alerts(
        args.project,
        getattr(args, 'status', None),
        limit=getattr(args, 'limit', 100)
    )

    # Filter by date unless --all is specified
    if not getattr(args, 'all', False):
        since_days = getattr(args, 'since', 7)
        if since_days:
            cutoff = datetime.now(timezone.utc) - timedelta(days=since_days)
            filtered = []
            for alert in alerts:
                alert_date = parse_timestamp(alert.get('created', ''))
                if alert_date and alert_date >= cutoff:
                    filtered.append(alert)
            alerts = filtered

            if not alerts:
                print(f"No alerts found in the last {since_days} days.")
                print(f"Use --all to see all alerts, or --since N for a different time range.")
                return

    print_alerts(alerts, args.format)


def cmd_alerts_get(client: AtlasClient, args):
    """Handle 'alerts get' command"""
    alert = client.get_alert(args.alert_id, args.project)
    if args.format == "json":
        print(json.dumps(alert, indent=2))
    else:
        print(f"\nAlert: {alert.get('id')}")
        print(f"Type:    {alert.get('eventTypeName')}")
        print(f"Status:  {alert.get('status')}")
        print(f"Created: {format_timestamp(alert.get('created'))}")
        if alert.get('acknowledgedUntil'):
            print(f"Acknowledged Until: {format_timestamp(alert.get('acknowledgedUntil'))}")
        if alert.get('currentValue'):
            cv = alert['currentValue']
            print(f"Current Value: {cv.get('number')} {cv.get('units', '')}")


def cmd_alerts_ack(client: AtlasClient, args):
    """Handle 'alerts ack' command"""
    result = client.acknowledge_alert(args.alert_id, args.comment, args.project)
    print(f"Alert {args.alert_id} acknowledged successfully.")
    if args.comment:
        print(f"Comment: {args.comment}")


def cmd_clusters_list(client: AtlasClient, args):
    """Handle 'clusters list' command"""
    clusters = client.list_clusters(args.project)
    print_clusters(clusters, args.format)


def cmd_clusters_status(client: AtlasClient, args):
    """Handle 'clusters status' command"""
    cluster = client.get_cluster(args.cluster_name, args.project)
    print_cluster_status(cluster, args.format)


def cmd_metrics(client: AtlasClient, args):
    """Handle 'metrics' command"""
    # First get processes to find the right one
    processes = client.list_processes(args.project)

    # Filter by cluster name if provided
    target_processes = processes
    if args.cluster:
        target_processes = [p for p in processes
                          if args.cluster.lower() in p.get('userAlias', '').lower()
                          or args.cluster.lower() in p.get('hostname', '').lower()]

    if not target_processes:
        print(f"No processes found for cluster '{args.cluster}'")
        return

    # Get metrics for first matching process
    process = target_processes[0]
    process_id = f"{process['hostname']}:{process['port']}"

    print(f"Getting metrics for: {process.get('userAlias', process_id)}")

    metrics = client.get_process_metrics(
        process_id,
        args.project,
        period=args.period
    )
    print_metrics(metrics, args.format)


def cmd_projects_list(client: AtlasClient, args):
    """Handle 'projects list' command"""
    projects = client.list_projects()
    print_projects(projects, args.format)


# ============ Main ============

def main():
    parser = argparse.ArgumentParser(
        description="MongoDB Atlas Admin API CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Global options
    parser.add_argument("--project", "-p", default=DEFAULT_PROJECT_ID,
                       help="Project ID (default: ATLAS_PROJECT_ID env var)")
    parser.add_argument("--format", "-f", choices=["table", "json"], default="table",
                       help="Output format (default: table)")
    parser.add_argument("--public-key", default=DEFAULT_PUBLIC_KEY,
                       help="Atlas API public key (default: ATLAS_PUBLIC_KEY env var)")
    parser.add_argument("--private-key", default=DEFAULT_PRIVATE_KEY,
                       help="Atlas API private key (default: ATLAS_PRIVATE_KEY env var)")

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # ---- alerts ----
    alerts_parser = subparsers.add_parser("alerts", help="Alert operations")
    alerts_sub = alerts_parser.add_subparsers(dest="subcommand")

    # alerts list
    alerts_list = alerts_sub.add_parser("list", help="List alerts")
    alerts_list.add_argument("--status", choices=["open", "closed"],
                            help="Filter by status")
    alerts_list.add_argument("--since", type=int, default=7,
                            help="Show alerts from last N days (default: 7)")
    alerts_list.add_argument("--limit", type=int, default=100,
                            help="Maximum alerts to fetch from API (default: 100)")
    alerts_list.add_argument("--all", action="store_true",
                            help="Show all alerts (ignore --since filter)")
    alerts_list.set_defaults(func=cmd_alerts_list)

    # alerts get
    alerts_get = alerts_sub.add_parser("get", help="Get alert details")
    alerts_get.add_argument("alert_id", help="Alert ID")
    alerts_get.set_defaults(func=cmd_alerts_get)

    # alerts ack
    alerts_ack = alerts_sub.add_parser("ack", help="Acknowledge alert")
    alerts_ack.add_argument("alert_id", help="Alert ID")
    alerts_ack.add_argument("--comment", "-c", help="Acknowledgement comment")
    alerts_ack.set_defaults(func=cmd_alerts_ack)

    # ---- clusters ----
    clusters_parser = subparsers.add_parser("clusters", help="Cluster operations")
    clusters_sub = clusters_parser.add_subparsers(dest="subcommand")

    # clusters list
    clusters_list = clusters_sub.add_parser("list", help="List clusters")
    clusters_list.set_defaults(func=cmd_clusters_list)

    # clusters status
    clusters_status = clusters_sub.add_parser("status", help="Get cluster status")
    clusters_status.add_argument("cluster_name", help="Cluster name")
    clusters_status.set_defaults(func=cmd_clusters_status)

    # ---- metrics ----
    metrics_parser = subparsers.add_parser("metrics", help="Get metrics")
    metrics_parser.add_argument("--cluster", "-c", required=True,
                               help="Cluster name")
    metrics_parser.add_argument("--period", default="PT1H",
                               help="Time period (default: PT1H)")
    metrics_parser.set_defaults(func=cmd_metrics)

    # ---- projects ----
    projects_parser = subparsers.add_parser("projects", help="Project operations")
    projects_sub = projects_parser.add_subparsers(dest="subcommand")

    # projects list
    projects_list = projects_sub.add_parser("list", help="List projects")
    projects_list.set_defaults(func=cmd_projects_list)

    # Parse and execute
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    # Validate credentials
    if not args.public_key or not args.private_key:
        print("ERROR: Atlas API credentials required.")
        print("Set ATLAS_PUBLIC_KEY and ATLAS_PRIVATE_KEY environment variables,")
        print("or use --public-key and --private-key flags.")
        sys.exit(1)

    # Create client
    client = AtlasClient(args.public_key, args.private_key, args.project)

    # Execute command
    try:
        if hasattr(args, 'func'):
            args.func(client, args)
        else:
            # Handle subcommand parsers without func
            if args.command == "alerts":
                alerts_parser.print_help()
            elif args.command == "clusters":
                clusters_parser.print_help()
            elif args.command == "projects":
                projects_parser.print_help()
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
