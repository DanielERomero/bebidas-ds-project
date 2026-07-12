import os
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
import json
# Configuración
MODULE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(MODULE_DIR / ".env")

SNAPSHOT_DATE = "2025-06-30"
EXPECTED_CLIENTS = 498

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    raise ValueError(
        "Faltan SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY en el archivo .env."
    )

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


# Lectura desde Silver
response = (
    supabase.schema("silver")
    .table("client_lrfmv_features")
    .select("*")
    .eq("snapshot_date", SNAPSHOT_DATE)
    .execute()
)

clients_features = pd.DataFrame(response.data)

required_columns = [
    "client_id",
    "snapshot_date",
    "first_purchase_date",
    "last_purchase_date",
    "length_days",
    "recency_days",
    "frequency",
    "monetary",
    "volume",
    "n_transactions_total",
    "frequency_last_3_months",
    "frequency_previous_3_months",
    "delta_frequency",
    "es_nuevo",
    "churn_eligible",
    "is_churn_risk",
    "score_lrfmv_0_100",
]

missing_columns = [
    column
    for column in required_columns
    if column not in clients_features.columns
]

if missing_columns:
    raise ValueError(
        f"Faltan columnas requeridas en Silver: {missing_columns}"
    )

if len(clients_features) != EXPECTED_CLIENTS:
    raise ValueError(
        f"Se esperaban {EXPECTED_CLIENTS} clientes para el snapshot "
        f"{SNAPSHOT_DATE}, pero se obtuvieron {len(clients_features)}."
    )

print("Conexión a Supabase correcta.")
print(f"Snapshot leído: {SNAPSHOT_DATE}")
print(f"Clientes recibidos desde Silver: {len(clients_features)}")
print("\nColumnas disponibles:")
print(clients_features.columns.tolist())

# Separación por regla de negocio
if clients_features["es_nuevo"].isna().any():
    raise ValueError("La columna es_nuevo contiene valores nulos.")

clients_features["es_nuevo"] = clients_features["es_nuevo"].astype(bool)

new_clients = clients_features[
    clients_features["es_nuevo"]
].copy()

mature_clients = clients_features[
    ~clients_features["es_nuevo"]
].copy()

if len(new_clients) != 84 or len(mature_clients) != 414:
    raise ValueError(
        "La separación Nuevo/Maduro no coincide con la validación de Silver. "
        f"Nuevos: {len(new_clients)} | Maduros: {len(mature_clients)}"
    )

print("\nSeparación para clustering:")
print(f"Clientes nuevos — regla de negocio: {len(new_clients)}")
print(f"Clientes maduros — entran a K-Means: {len(mature_clients)}")


# Variables para clustering
# No usamos score_lrfmv_0_100 porque ya es una combinación de LRFMV.
# K-Means debe trabajar directamente con las variables que describen al cliente.
mature_clients["recency_log"] = np.log1p(mature_clients["recency_days"])
mature_clients["monetary_log"] = np.log1p(mature_clients["monetary"])

clustering_features = [
    "length_days",
    "recency_log",
    "frequency",
    "monetary_log",
    "volume",
]

if mature_clients[clustering_features].isna().any().any():
    raise ValueError("Existen valores nulos en las variables de clustering.")

X = mature_clients[clustering_features].copy()

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

X_scaled_df = pd.DataFrame(
    X_scaled,
    columns=clustering_features,
    index=mature_clients.index,
)

print("\nVariables usadas por K-Means:")
print(clustering_features)

print("\nPromedio y desviación estándar después de StandardScaler:")
print(
    X_scaled_df.agg(["mean", "std"])
    .round(3)
)
# Validación simple de k mediante silhouette
silhouette_results = []

for k in range(2, 7):
    model = KMeans(
        n_clusters=k,
        random_state=42,
        n_init=10,
    )
    labels = model.fit_predict(X_scaled)

    silhouette_results.append(
        {
            "k": k,
            "silhouette_score": silhouette_score(X_scaled, labels),
        }
    )

silhouette_df = pd.DataFrame(silhouette_results)

print("\nValidación de silhouette:")
print(silhouette_df.round(4).to_string(index=False))


# Modelo definitivo: decisión de negocio ya definida
KMEANS_K = 4

kmeans = KMeans(
    n_clusters=KMEANS_K,
    random_state=42,
    n_init=10,
)

mature_clients["cluster_id"] = kmeans.fit_predict(X_scaled)

silhouette_k4 = silhouette_score(
    X_scaled,
    mature_clients["cluster_id"],
)

print(f"\nK-Means ajustado con k={KMEANS_K}.")
print(f"Silhouette para k=4: {silhouette_k4:.4f}")

print("\nClientes por cluster técnico:")
print(
    mature_clients["cluster_id"]
    .value_counts()
    .sort_index()
)

# Perfil comercial de cada cluster técnico
cluster_profile = (
    mature_clients
    .groupby("cluster_id", as_index=False)
    .agg(
        clientes=("client_id", "count"),
        score_promedio=("score_lrfmv_0_100", "mean"),
        length_promedio=("length_days", "mean"),
        recency_promedio=("recency_days", "mean"),
        frequency_promedio=("frequency", "mean"),
        monetary_promedio=("monetary", "mean"),
        volume_promedio=("volume", "mean"),
        tasa_churn=("is_churn_risk", "mean"),
    )
    .sort_values("score_promedio", ascending=False)
    .reset_index(drop=True)
)

commercial_labels = ["Diamante", "Oro", "Plata", "Bronce"]

cluster_profile["cluster_label"] = commercial_labels
cluster_profile["tasa_churn_pct"] = (
    100 * cluster_profile["tasa_churn"]
)

cluster_label_map = (
    cluster_profile
    .set_index("cluster_id")["cluster_label"]
    .to_dict()
)

mature_clients["cluster_label"] = (
    mature_clients["cluster_id"]
    .map(cluster_label_map)
)

mature_clients["cluster_source"] = "kmeans"

print("\nPerfil de clusters con etiquetas comerciales:")
print(
    cluster_profile[
        [
            "cluster_id",
            "cluster_label",
            "clientes",
            "score_promedio",
            "recency_promedio",
            "frequency_promedio",
            "monetary_promedio",
            "volume_promedio",
            "tasa_churn_pct",
        ]
    ]
    .round(2)
    .to_string(index=False)
)

# Clientes nuevos: no reciben cluster técnico
new_clients["cluster_id"] = pd.NA
new_clients["cluster_label"] = "Nuevo"
new_clients["cluster_source"] = "business_rule"

# Unión de clientes maduros clusterizados y clientes nuevos
clients_clustered = pd.concat(
    [mature_clients, new_clients],
    ignore_index=True,
)

gold_columns = [
    "client_id",
    "snapshot_date",
    "first_purchase_date",
    "last_purchase_date",
    "length_days",
    "recency_days",
    "frequency",
    "monetary",
    "volume",
    "n_transactions_total",
    "frequency_last_3_months",
    "frequency_previous_3_months",
    "delta_frequency",
    "es_nuevo",
    "churn_eligible",
    "is_churn_risk",
    "score_lrfmv_0_100",
    "cluster_id",
    "cluster_label",
    "cluster_source",
]

clients_clustered = clients_clustered[gold_columns].copy()

expected_segment_counts = {
    "Diamante": 196,
    "Oro": 84,
    "Plata": 34,
    "Bronce": 100,
    "Nuevo": 84,
}

actual_segment_counts = (
    clients_clustered["cluster_label"]
    .value_counts()
    .to_dict()
)

if len(clients_clustered) != 498:
    raise ValueError("Gold debe contener exactamente 498 clientes.")

if actual_segment_counts != expected_segment_counts:
    raise ValueError(
        "La distribución de segmentos no coincide con el resultado esperado: "
        f"{actual_segment_counts}"
    )

print("\nDataset Gold preparado:")
print(f"Filas: {len(clients_clustered)}")
print("\nClientes por segmento:")
print(clients_clustered["cluster_label"].value_counts())

# Preparar datos para enviar a Supabase
# Int64 permite conservar enteros y representar los cluster_id de Nuevo como null.
clients_clustered["cluster_id"] = (
    clients_clustered["cluster_id"]
    .astype("Int64")
)

gold_records = json.loads(
    clients_clustered.to_json(
        orient="records",
        date_format="iso",
    )
)

# Upsert: inserta la primera vez y actualiza si se vuelve a ejecutar
# para el mismo (client_id, snapshot_date).
response = (
    supabase.schema("gold")
    .table("clients_clustered")
    .upsert(
        gold_records,
        on_conflict="client_id,snapshot_date",
    )
    .execute()
)

print(
    f"\nFilas insertadas o actualizadas en Gold: {len(response.data)}"
)

# Verificación posterior a la escritura
verification_response = (
    supabase.schema("gold")
    .table("clients_clustered")
    .select("client_id, cluster_label, cluster_source")
    .eq("snapshot_date", SNAPSHOT_DATE)
    .execute()
)

gold_verification = pd.DataFrame(verification_response.data)

if len(gold_verification) != 498:
    raise ValueError(
        f"Gold debería tener 498 clientes, pero tiene "
        f"{len(gold_verification)}."
    )

print("\nGold validada correctamente.")
print(
    gold_verification["cluster_label"]
    .value_counts()
)