[![codecov](https://codecov.io/gh/cern-sis/workflows/branch/main/graph/badge.svg?token=00LZLXO5OD)](https://codecov.io/gh/cern-sis/workflows)

# workflows



## Run with docker-compose

The easiest way to run the project is run in with docker compose.
For it docker-compose has to be installed.After just run in it the command bellow:

```
docker-compose up --build
```

Currently the docker-compose performance isn't very good. Thus, for local dev, it is advised to run it locally.

## Run it locally

We need to install airflow.

1. First, we should create virtual environment with pyenv:

```
    export PYTHON_VERSION=3.8.13
    pyenv install $PYTHON_VERSION
    pyenv global $PYTHON_VERSION
    pyenv virtualenv $PYTHON_VERSION workflows
    pyenv activate workflows
```

3. Set airflow home directory:

```
export AIRFLOW_HOME=/path/to/cloned/repo
```

4. Install all required dependencies for a project. We need 3 requirements files, when we're running the project locally. First file (requirements.py) has all additional dependencies required to run the tasks correctly (connecting to ftputil, boto3 and etc.), the second one installs requirememnts for testing, such as pytest, the third- (requirements_airflow.py) installs Airflow itself and constraints needed for it. The the third file is not needed when we're running the procject on Docker, because we're using Apache Airflow Docker image:
   `pip install -r requirements.txt -r requirements-test.txt -r requirements-airflow.txt`
5. Run Airflow. Airflow comes with the `standalone` command. This should not be used as it seems to use the SequentialExecutor by default. To have our local config being use, we must run all services together :

```
    airflow webserver
    airflow triggerer
    airflow scheduler
```

### Script

A Makefile has been created to ease this process. The available targets are the following :

- `make init` : Inits the pyenv version and virtual env.
- `make start` : Starts all processes needed.
- `make stop` : Stops all processes needed.

## Access UI

Airflow UI will be rinning on localhost:8080.
More details about Airflow installation and running can be found [here](https://airflow.apache.org/docs/apache-airflow/stable/start/local.html)
