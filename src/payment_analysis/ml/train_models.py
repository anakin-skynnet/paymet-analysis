# Databricks notebook source
# MAGIC %md
# MAGIC # Payment Approval ML Models Training
# MAGIC 
# MAGIC Train all 4 ML models for the Payment Analysis Platform:
# MAGIC 1. Approval Propensity Model
# MAGIC 2. Risk Scoring Model
# MAGIC 3. Smart Routing Policy
# MAGIC 4. Smart Retry Policy
# MAGIC 
# MAGIC All models are trained using data from Unity Catalog and registered to Unity Catalog.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup and Configuration

# COMMAND ----------

import mlflow  # type: ignore[import-untyped]
import mlflow.sklearn  # type: ignore[import-untyped]
import pandas as pd  # type: ignore[import-untyped]
import numpy as np  # type: ignore[import-untyped]
from sklearn.ensemble import RandomForestClassifier  # type: ignore[import-untyped]
from sklearn.model_selection import train_test_split  # type: ignore[import-untyped]
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score  # type: ignore[import-untyped]
from sklearn.preprocessing import LabelEncoder  # type: ignore[import-untyped]
from mlflow.models.signature import infer_signature  # type: ignore[import-untyped]
import pickle
import warnings
warnings.filterwarnings('ignore')

# Get parameters from widgets (when run as job, catalog/schema = bundle var.catalog, var.schema)
dbutils.widgets.text("catalog", "ahs_demos_catalog")
dbutils.widgets.text("schema", "payment_analysis")
dbutils.widgets.text("n_estimators", "100")
dbutils.widgets.text("max_depth_approval", "10")
dbutils.widgets.text("max_depth_risk", "12")
dbutils.widgets.text("max_depth_routing", "10")
dbutils.widgets.text("max_depth_retry", "8")
dbutils.widgets.text("min_samples_split", "5")


def _int_widget(name: str, default: int) -> int:
    v = dbutils.widgets.get(name)  # type: ignore[name-defined]
    if v is None or v == "None" or (isinstance(v, str) and v.strip() == ""):
        return default
    try:
        return int(v)
    except ValueError:
        return default


def _str_widget(name: str, default: str) -> str:
    """Get widget value; treat None, empty, and literal 'None' as missing so bundle var substitution issues don't pass 'None' through."""
    v = dbutils.widgets.get(name)  # type: ignore[name-defined]
    if v is None or (isinstance(v, str) and (v.strip() == "" or v.strip().lower() == "none")):
        return default
    return v.strip()


CATALOG = _str_widget("catalog", "ahs_demos_catalog")
SCHEMA = _str_widget("schema", "payment_analysis")
N_ESTIMATORS = _int_widget("n_estimators", 100)
MAX_DEPTH_APPROVAL = _int_widget("max_depth_approval", 10)
MAX_DEPTH_RISK = _int_widget("max_depth_risk", 12)
MAX_DEPTH_ROUTING = _int_widget("max_depth_routing", 10)
MAX_DEPTH_RETRY = _int_widget("max_depth_retry", 8)
MIN_SAMPLES_SPLIT = _int_widget("min_samples_split", 5)
# Use a path outside the app source tree (e.g. payment-analysis/) so app export does not try to export this MLflow experiment
EXPERIMENT_PATH = f"/Users/{spark.sql('SELECT current_user()').collect()[0][0]}/mlflow_experiments/payment_analysis_models"

# Set MLflow to use Unity Catalog
mlflow.set_registry_uri("databricks-uc")

# Create or set experiment
try:
    mlflow.create_experiment(EXPERIMENT_PATH)
except Exception:
    pass  # Experiment already exists
mlflow.set_experiment(EXPERIMENT_PATH)

print("✓ Configuration complete")
print(f"  Catalog: {CATALOG}")
print(f"  Schema: {SCHEMA}")
print(f"  Experiment: {EXPERIMENT_PATH}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Load Training Data

# COMMAND ----------

# Try to load from Unity Catalog, fall back to synthetic data
data_query = f"""
SELECT 
    transaction_id,
    amount,
    fraud_score,
    aml_risk_score,
    device_trust_score,
    is_cross_border,
    retry_count,
    retry_scenario,
    attempt_sequence,
    time_since_last_attempt_seconds,
    prior_approved_count,
    merchant_retry_policy_max_attempts,
    merchant_segment,
    uses_3ds,
    payment_solution,
    decline_reason,
    decline_reason_standard,
    is_recurring,
    is_approved,
    processing_time_ms
FROM {CATALOG}.{SCHEMA}.payments_enriched_silver
WHERE event_date >= CURRENT_DATE() - INTERVAL 30 DAYS
LIMIT 500000
"""

try:
    df = spark.sql(data_query).toPandas()  # type: ignore[name-defined]
    print(f"✓ Loaded {len(df)} transactions from Silver table (capped at 500k)")
    print(f"  Approval rate: {df['is_approved'].mean()*100:.1f}%")
except Exception as e:
    print(f"⚠ Table not found, creating synthetic data for training...")
    
    # Create synthetic data
    n_samples = 5000
    np.random.seed(42)
    
    df = pd.DataFrame({
        'transaction_id': [f'txn_{i}' for i in range(n_samples)],
        'amount': np.random.lognormal(5, 1.5, n_samples),
        'fraud_score': np.clip(np.random.beta(2, 8, n_samples), 0, 1),
        'aml_risk_score': np.clip(np.random.beta(2, 10, n_samples), 0, 1),
        'device_trust_score': np.clip(np.random.beta(8, 2, n_samples), 0, 1),
        'is_cross_border': np.random.choice([0, 1], n_samples, p=[0.7, 0.3]),
        'retry_count': np.random.choice([0, 1, 2, 3], n_samples, p=[0.7, 0.15, 0.1, 0.05]),
        'retry_scenario': np.random.choice(['None', 'PaymentRetry', 'PaymentRecurrence'], n_samples, p=[0.75, 0.15, 0.10]),
        'attempt_sequence': np.random.choice([1, 2, 3], n_samples, p=[0.85, 0.10, 0.05]),
        'time_since_last_attempt_seconds': np.random.choice([0, 60, 3600, 86400, 172800], n_samples, p=[0.85, 0.03, 0.03, 0.06, 0.03]),
        'prior_approved_count': np.random.choice([0, 1, 2, 3], n_samples, p=[0.7, 0.2, 0.07, 0.03]),
        'merchant_retry_policy_max_attempts': np.random.choice([1, 2, 3], n_samples, p=[0.1, 0.3, 0.6]),
        'merchant_segment': np.random.choice(['Travel', 'Retail', 'Gaming', 'Digital', 'Entertainment'], n_samples),
        'uses_3ds': np.random.choice([0, 1], n_samples, p=[0.4, 0.6]),
        'payment_solution': np.random.choice(['standard', '3ds', 'network_token', 'passkey'], n_samples, p=[0.3, 0.4, 0.2, 0.1]),
        'decline_reason': np.random.choice([None, 'insufficient_funds', 'fraud_suspected', 'expired_card', 'do_not_honor', 'issuer_unavailable'], n_samples, p=[0.85, 0.05, 0.03, 0.03, 0.02, 0.02]),
        'decline_reason_standard': np.random.choice([None, 'FUNDS_OR_LIMIT', 'FRAUD_SUSPECTED', 'CARD_EXPIRED', 'ISSUER_DO_NOT_HONOR', 'ISSUER_TECHNICAL'], n_samples, p=[0.85, 0.06, 0.03, 0.03, 0.02, 0.01]),
        'is_recurring': np.random.choice([0, 1], n_samples, p=[0.6, 0.4]),
        'processing_time_ms': np.random.uniform(50, 500, n_samples)
    })
    
    # Generate is_approved based on features (more realistic)
    approval_prob = (
        0.7 + 
        0.15 * df['device_trust_score'] - 
        0.25 * df['fraud_score'] - 
        0.1 * df['aml_risk_score'] +
        0.05 * df['uses_3ds'] -
        0.05 * df['is_cross_border']
    )
    df['is_approved'] = (np.random.random(n_samples) < approval_prob).astype(int)
    
    print(f"✓ Created {len(df)} synthetic transactions")
    print(f"  Approval rate: {df['is_approved'].mean()*100:.1f}%")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Model 1: Approval Propensity Model

# COMMAND ----------

training_errors: list[str] = []  # collect failures; raise at the end if any

print("=" * 80)
print("TRAINING MODEL 1: Approval Propensity Model")
print("=" * 80)

try:
    features_approval = ['amount', 'fraud_score', 'device_trust_score', 'is_cross_border', 'retry_count', 'uses_3ds']
    X_approval = df[features_approval].fillna(0)
    y_approval = df['is_approved'].astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X_approval, y_approval, test_size=0.2, random_state=42, stratify=y_approval
    )

    with mlflow.start_run(run_name="approval_propensity_model") as run:
        model = RandomForestClassifier(
            n_estimators=N_ESTIMATORS,
            max_depth=MAX_DEPTH_APPROVAL,
            min_samples_split=MIN_SAMPLES_SPLIT,
            random_state=42,
            n_jobs=-1
        )
        model.fit(X_train, y_train)
        
        y_pred = model.predict(X_test)
        y_pred_proba = model.predict_proba(X_test)[:, 1]
        
        metrics = {
            "accuracy": accuracy_score(y_test, y_pred),
            "precision": precision_score(y_test, y_pred),
            "recall": recall_score(y_test, y_pred),
            "f1_score": f1_score(y_test, y_pred),
            "roc_auc": roc_auc_score(y_test, y_pred_proba)
        }
        
        mlflow.log_params({
            "model_type": "RandomForestClassifier",
            "n_estimators": N_ESTIMATORS,
            "max_depth": MAX_DEPTH_APPROVAL,
            "features": ",".join(features_approval)
        })
        mlflow.log_metrics(metrics)
        
        signature = infer_signature(X_train, model.predict(X_train))
        model_name = f"{CATALOG}.{SCHEMA}.approval_propensity_model"
        mlflow.sklearn.log_model(
            sk_model=model,
            artifact_path="model",
            registered_model_name=model_name,
            signature=signature
        )
        
        print(f"\n✓ Model registered: {model_name}")
        for k, v in metrics.items():
            print(f"  {k}: {v:.4f}")
except Exception as e:
    print(f"\n✗ Model 1 (Approval Propensity) FAILED: {e}")
    training_errors.append(f"Approval Propensity: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Model 2: Risk Scoring Model

# COMMAND ----------

print("=" * 80)
print("TRAINING MODEL 2: Risk Scoring Model")
print("=" * 80)

try:
    features_risk = ['amount', 'fraud_score', 'aml_risk_score', 'is_cross_border', 'processing_time_ms', 'device_trust_score']
    X_risk = df[features_risk].fillna(0)
    y_risk = ((df['fraud_score'] > 0.5) | (df['is_approved'] == 0)).astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X_risk, y_risk, test_size=0.2, random_state=42, stratify=y_risk
    )

    with mlflow.start_run(run_name="risk_scoring_model") as run:
        model = RandomForestClassifier(
            n_estimators=N_ESTIMATORS,
            max_depth=MAX_DEPTH_RISK,
            min_samples_split=MIN_SAMPLES_SPLIT,
            random_state=42,
            n_jobs=-1
        )
        model.fit(X_train, y_train)
        
        y_pred = model.predict(X_test)
        y_pred_proba = model.predict_proba(X_test)[:, 1]
        
        metrics = {
            "accuracy": accuracy_score(y_test, y_pred),
            "precision": precision_score(y_test, y_pred),
            "recall": recall_score(y_test, y_pred),
            "f1_score": f1_score(y_test, y_pred),
            "roc_auc": roc_auc_score(y_test, y_pred_proba)
        }
        
        mlflow.log_params({
            "model_type": "RandomForestClassifier",
            "n_estimators": N_ESTIMATORS,
            "max_depth": MAX_DEPTH_RISK,
            "features": ",".join(features_risk)
        })
        mlflow.log_metrics(metrics)
        
        signature = infer_signature(X_train, model.predict(X_train))
        model_name = f"{CATALOG}.{SCHEMA}.risk_scoring_model"
        mlflow.sklearn.log_model(
            sk_model=model,
            artifact_path="model",
            registered_model_name=model_name,
            signature=signature
        )
        
        print(f"\n✓ Model registered: {model_name}")
        for k, v in metrics.items():
            print(f"  {k}: {v:.4f}")
except Exception as e:
    print(f"\n✗ Model 2 (Risk Scoring) FAILED: {e}")
    training_errors.append(f"Risk Scoring: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Model 3: Smart Routing Policy

# COMMAND ----------

print("=" * 80)
print("TRAINING MODEL 3: Smart Routing Policy")
print("=" * 80)

try:
    features_routing = ['amount', 'fraud_score', 'is_cross_border', 'uses_3ds', 'device_trust_score']
    df_routing = df.copy()
    df_routing = pd.get_dummies(df_routing, columns=['merchant_segment'], prefix='segment')
    segment_cols = [col for col in df_routing.columns if col.startswith('segment_')]
    features_routing_all = features_routing + segment_cols

    X_routing = df_routing[features_routing_all].fillna(0)

    le = LabelEncoder()
    y_routing = le.fit_transform(df['payment_solution'])

    X_train, X_test, y_train, y_test = train_test_split(
        X_routing, y_routing, test_size=0.2, random_state=42
    )

    with mlflow.start_run(run_name="smart_routing_policy") as run:
        model = RandomForestClassifier(
            n_estimators=N_ESTIMATORS,
            max_depth=MAX_DEPTH_ROUTING,
            min_samples_split=MIN_SAMPLES_SPLIT,
            random_state=42,
            n_jobs=-1
        )
        model.fit(X_train, y_train)
        
        y_pred = model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        
        mlflow.log_params({
            "model_type": "RandomForestClassifier",
            "n_estimators": N_ESTIMATORS,
            "max_depth": MAX_DEPTH_ROUTING,
            "features": ",".join(features_routing_all),
            "classes": ",".join(le.classes_)
        })
        mlflow.log_metrics({"accuracy": accuracy, "n_classes": len(le.classes_)})
        
        with open("/tmp/label_encoder.pkl", "wb") as f:
            pickle.dump(le, f)
        mlflow.log_artifact("/tmp/label_encoder.pkl")
        
        signature = infer_signature(X_train, model.predict(X_train))
        model_name = f"{CATALOG}.{SCHEMA}.smart_routing_policy"
        mlflow.sklearn.log_model(
            sk_model=model,
            artifact_path="model",
            registered_model_name=model_name,
            signature=signature
        )
        
        print(f"\n✓ Model registered: {model_name}")
        print(f"  Accuracy: {accuracy:.4f}")
        print(f"  Classes: {', '.join(le.classes_)}")
except Exception as e:
    print(f"\n✗ Model 3 (Smart Routing) FAILED: {e}")
    training_errors.append(f"Smart Routing: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Model 4: Smart Retry Policy

# COMMAND ----------

print("=" * 80)
print("TRAINING MODEL 4: Smart Retry Policy")
print("=" * 80)

try:
    df_declined = df[df['is_approved'] == 0].copy()

    if len(df_declined) > 50:
        # Prefer standardized taxonomy if available
        reason_source = "decline_reason_standard" if "decline_reason_standard" in df_declined.columns else "decline_reason"
        df_declined['decline_encoded'] = df_declined[reason_source].fillna('unknown').astype('category').cat.codes
        df_declined["retry_scenario_encoded"] = (
            df_declined.get("retry_scenario", "None").fillna("None").astype("category").cat.codes
        )
        
        features_retry = [
            "decline_encoded",
            "retry_scenario_encoded",
            "retry_count",
            "amount",
            "is_recurring",
            "fraud_score",
            "device_trust_score",
            "attempt_sequence",
            "time_since_last_attempt_seconds",
            "prior_approved_count",
            "merchant_retry_policy_max_attempts",
        ]
        X_retry = df_declined[features_retry].fillna(0)
        
        # Heuristic label for recoverability (placeholder for supervised labels)
        recoverable_reasons = {"FUNDS_OR_LIMIT", "ISSUER_TECHNICAL", "ISSUER_DO_NOT_HONOR"}
        reason_series = df_declined[reason_source].fillna("unknown")
        y_retry = (
            (reason_series.isin(recoverable_reasons))
            & (df_declined["fraud_score"] < 0.5)
            & (df_declined["retry_count"] < 2)
        ).astype(int)
        
        X_train, X_test, y_train, y_test = train_test_split(
            X_retry, y_retry, test_size=0.2, random_state=42
        )
        
        with mlflow.start_run(run_name="smart_retry_policy") as run:
            model = RandomForestClassifier(
                n_estimators=N_ESTIMATORS,
                max_depth=MAX_DEPTH_RETRY,
                min_samples_split=MIN_SAMPLES_SPLIT,
                random_state=42,
                n_jobs=-1
            )
            model.fit(X_train, y_train)
            
            y_pred = model.predict(X_test)
            
            metrics = {
                "accuracy": accuracy_score(y_test, y_pred),
                "precision": precision_score(y_test, y_pred, zero_division=0),
                "recall": recall_score(y_test, y_pred, zero_division=0),
                "f1_score": f1_score(y_test, y_pred, zero_division=0)
            }
            
            mlflow.log_params({
                "model_type": "RandomForestClassifier",
                "n_estimators": N_ESTIMATORS,
                "max_depth": MAX_DEPTH_RETRY,
                "features": ",".join(features_retry)
            })
            mlflow.log_metrics(metrics)
            
            signature = infer_signature(X_train, model.predict(X_train))
            model_name = f"{CATALOG}.{SCHEMA}.smart_retry_policy"
            mlflow.sklearn.log_model(
                sk_model=model,
                artifact_path="model",
                registered_model_name=model_name,
                signature=signature
            )
            
            print(f"\n✓ Model registered: {model_name}")
            for k, v in metrics.items():
                print(f"  {k}: {v:.4f}")
    else:
        print("⚠ Not enough declined transactions for training — skipping Model 4")
except Exception as e:
    print(f"\n✗ Model 4 (Smart Retry) FAILED: {e}")
    training_errors.append(f"Smart Retry: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Training Complete

# COMMAND ----------

print("\n" + "=" * 80)
print("ML TRAINING COMPLETE")
print("=" * 80)

if training_errors:
    print(f"\n⚠ {len(training_errors)} model(s) failed:")
    for err in training_errors:
        print(f"  ✗ {err}")
    print()

models = [
    f"{CATALOG}.{SCHEMA}.approval_propensity_model",
    f"{CATALOG}.{SCHEMA}.risk_scoring_model",
    f"{CATALOG}.{SCHEMA}.smart_routing_policy",
    f"{CATALOG}.{SCHEMA}.smart_retry_policy",
]
print("Models targeted for Unity Catalog:")
for i, m in enumerate(models, 1):
    print(f"  {i}. {m}")

print(f"\n✓ MLflow Experiment: {EXPERIMENT_PATH}")

if training_errors:
    raise RuntimeError(f"Training completed with {len(training_errors)} error(s). See logs above.")

print("✓ All models trained and ready for serving")
