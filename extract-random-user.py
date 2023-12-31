from airflow import DAG

from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.providers.http.sensors.http import HttpSensor
from airflow.providers.http.operators.http import SimpleHttpOperator
from airflow.operators.dummy_operator import EmptyOperator

from datetime import datetime, timedelta

import json

default_args={
    'email': ['airflow@example.com'],
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
}

def transform_user(**kwargs):
    ti = kwargs['ti']
    return_value = ti.xcom_pull(task_ids='extract_user')

    return_value = json.loads(return_value)
    user = return_value["results"][0]

    transformed_user = {
        "first_name": user["name"]["first"],
        "last_name": user["name"]["last"],
        "gender": user["gender"],
        "country": user["location"]["country"],
        "age": user["dob"]["age"],
        "email": user["email"]
    }
    
    return transformed_user

def check_user_age(**kwargs):
    ti = kwargs['ti']
    return_value = ti.xcom_pull(task_ids='transform_user')

    age = return_value["age"]

    if age >= 30:
        return "store_user_group_a"
    else:
        return "store_user_group_b"

with DAG(
    'extract_random_user',
    default_args=default_args,
    description='Extract random user using Airflow',
    schedule="@daily",  # Use the 'schedule' parameter
    start_date=datetime(2023, 10, 24), # 0 0 * * *
    tags=['random-user'],
) as dag:

    is_api_available = HttpSensor(
        task_id='is_api_available',
        http_conn_id='user_api',
        endpoint='api/',
        dag=dag,
    )

    extract_user = SimpleHttpOperator(
        task_id='extract_user',
        method='GET',
        http_conn_id='user_api',
        endpoint='api/',
        dag=dag,
    )

    transform_user = PythonOperator(
        task_id="transform_user",
        python_callable=transform_user,
        provide_context=True,
        dag=dag
    )

    check_user_age = BranchPythonOperator(
        task_id="check_user_age",
        python_callable=check_user_age,
        provide_context=True,
        dag=dag
    )

    store_user_group_a = EmptyOperator(
        task_id="store_user_group_a",
        dag=dag
    )

    store_user_group_b = EmptyOperator(
        task_id="store_user_group_b",
        dag=dag
    )

is_api_available >> extract_user >> transform_user
transform_user >> check_user_age
check_user_age >> [store_user_group_a, store_user_group_b]
