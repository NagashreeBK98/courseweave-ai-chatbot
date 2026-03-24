import os
import mlflow
import dagshub
from dotenv import load_dotenv

load_dotenv()

# Here, we are trying to initialize the DagsHub + MLFlow
dagshub.init(
    repo_owner="SIDDHARTH107",
    repo_name="courseweave-ai",
    mlflow=True
)

# Here, we are trying to test the MLflow
with mlflow.start_run(run_name="hello-mlflow"):
    mlflow.log_param("test_param", "It works!")
    mlflow.log_metric("test_metric", 1.0)
    print("MLflow connection test successful!")

print("Done! Please check the MLflow UI at: https://dagshub.com/SIDDHARTH107/courseweave-ai.mlflow")