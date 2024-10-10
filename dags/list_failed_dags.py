import requests
from base64 import b64encode
from datetime import datetime, timedelta, timezone

def list_failed_dag_runs_last_24_hours():
    base_url = "http://localhost:8080/api/v1"
    airflow_username = "admin"
    airflow_password = "admin"
    base64_bytes = b64encode(f"{airflow_username}:{airflow_password}".encode("ascii")).decode("ascii")
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Basic {base64_bytes}'
    }

    url = f"{base_url}/dags?only_active=true"
    dag_response = requests.get(url, headers=headers)
    
    if dag_response.status_code != 200:
        print(f"Error fetching DAGs: {dag_response.status_code}, {dag_response.text}")
        return

    dags = dag_response.json().get('dags', [])

    now = datetime.now(timezone.utc)
    time_24_hours_ago = now - timedelta(hours=24)

    for dag in dags:
        dag_id = dag['dag_id']
        dag_runs_url = f"{base_url}/dags/{dag_id}/dagRuns"

        dag_runs_response = requests.get(dag_runs_url, headers=headers)
        
        if dag_runs_response.status_code != 200:
            print(f"Error fetching DAG runs for {dag_id}: {dag_runs_response.status_code}, {dag_runs_response.text}")
            continue

        dag_runs = dag_runs_response.json().get('dag_runs', [])
        
        failed_runs = []
        for run in dag_runs:
            if run['state'] == 'failed':
                start_date = datetime.strptime(run['start_date'], "%Y-%m-%dT%H:%M:%S.%f%z")
                end_date = datetime.strptime(run['end_date'], "%Y-%m-%dT%H:%M:%S.%f%z") if run['end_date'] else None

                if start_date >= time_24_hours_ago or (end_date and end_date >= time_24_hours_ago):
                    failed_runs.append(run)

        if failed_runs:
            print(f"\nDAG '{dag_id}' has {len(failed_runs)} failed run(s) in the last 24 hours:")
            for run in failed_runs:
                print(f"- Run ID: {run['dag_run_id']}, Start Date: {run['start_date']}, End Date: {run['end_date']}")

list_failed_dag_runs_last_24_hours()
