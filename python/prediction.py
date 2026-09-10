import pyodbc
import pandas as pd
import numpy as np

from datetime import datetime

from sklearn.ensemble import RandomForestRegressor
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score

from joblib import dump


# ============================================================
# CONFIGURATION
# ============================================================

SERVER = r".\SQLEXPRESS"
DATABASE = "IndustrialSustainability"

CONNECTION_STRING = (
    "DRIVER={ODBC Driver 18 for SQL Server};"
    f"SERVER={SERVER};"
    f"DATABASE={DATABASE};"
    "Trusted_Connection=yes;"
    "TrustServerCertificate=yes;"
)

MINIMUM_RECORDS = 3000


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection():

    return pyodbc.connect(CONNECTION_STRING)


# ============================================================
# LOAD INDUSTRIAL DATA
# ============================================================

def load_data():

    connection = get_connection()

    query = """
    SELECT
        i.DataID,
        i.MachineID,
        i.DepartmentID,
        i.Timestamp,

        i.EnergyKWH,
        i.WaterLitres,
        i.WasteKG,
        i.CO2Emission,

        i.Temperature,
        i.Humidity,
        i.Vibration,

        i.ProductionUnits,
        i.DowntimeMinutes,

        i.MachineStatus,

        m.DepartmentName,
        m.MachineType,
        m.InstallationYear,
        m.ProductionLine,
        m.RatedPowerKW,

        d.DepartmentType

    FROM IndustrialData i

    INNER JOIN Machines m
        ON i.MachineID = m.MachineID

    INNER JOIN Departments d
        ON i.DepartmentID = d.DepartmentID

    ORDER BY
        i.MachineID,
        i.Timestamp
    """

    df = pd.read_sql(query, connection)

    connection.close()

    return df


# ============================================================
# LOAD DATA
# ============================================================

print("=" * 75)
print("UPGRADED AI INDUSTRIAL SUSTAINABILITY ENGINE")
print("=" * 75)

df = load_data()

print(f"\nTotal industrial records: {len(df)}")


if len(df) < MINIMUM_RECORDS:

    print("\nNot enough data.")

    print(
        f"Minimum required: {MINIMUM_RECORDS}"
    )

    print(
        "Continue running industrial_automation.py"
    )

    raise SystemExit


# ============================================================
# BASIC CLEANING
# ============================================================

df["Timestamp"] = pd.to_datetime(df["Timestamp"])

df = df.sort_values(
    ["MachineID", "Timestamp"]
).reset_index(drop=True)


numeric_columns = [
    "EnergyKWH",
    "WaterLitres",
    "WasteKG",
    "CO2Emission",
    "Temperature",
    "Humidity",
    "Vibration",
    "ProductionUnits",
    "DowntimeMinutes",
    "RatedPowerKW"
]


for column in numeric_columns:

    df[column] = pd.to_numeric(
        df[column],
        errors="coerce"
    )


# ============================================================
# MACHINE AGE
# ============================================================

CURRENT_YEAR = datetime.now().year

df["MachineAge"] = (
    CURRENT_YEAR - df["InstallationYear"]
)

df["MachineAge"] = df["MachineAge"].clip(
    lower=0
)


# ============================================================
# TIME FEATURES
# ============================================================

df["Hour"] = df["Timestamp"].dt.hour

df["Minute"] = df["Timestamp"].dt.minute

df["DayOfWeek"] = df["Timestamp"].dt.dayofweek


# ============================================================
# HISTORICAL FEATURES
#
# IMPORTANT:
# shift(1) ensures we only use PAST data.
# This prevents data leakage.
# ============================================================

grouped = df.groupby("MachineID")


historical_targets = [
    "EnergyKWH",
    "WaterLitres",
    "WasteKG",
    "CO2Emission",
    "DowntimeMinutes"
]


for column in historical_targets:

    df[f"Previous_{column}"] = (
        grouped[column]
        .shift(1)
        .rolling(
            window=10,
            min_periods=1
        )
        .mean()
        .reset_index(level=0, drop=True)
    )


# ============================================================
# PREVIOUS PRODUCTION
# ============================================================

df["PreviousProduction"] = (
    grouped["ProductionUnits"]
    .shift(1)
)


# ============================================================
# PREVIOUS VIBRATION
# ============================================================

df["PreviousVibration"] = (
    grouped["Vibration"]
    .shift(1)
)


# ============================================================
# PREVIOUS TEMPERATURE
# ============================================================

df["PreviousTemperature"] = (
    grouped["Temperature"]
    .shift(1)
)


# ============================================================
# CREATE NEXT-CYCLE TARGETS
#
# Current conditions → NEXT cycle outcome
# ============================================================

for column in historical_targets:

    df[f"Next_{column}"] = (
        grouped[column]
        .shift(-1)
    )


# ============================================================
# REMOVE LAST RECORD OF EACH MACHINE
#
# Last record has no future target.
# ============================================================

df = df.dropna(
    subset=[
        "Next_EnergyKWH",
        "Next_WaterLitres",
        "Next_WasteKG",
        "Next_CO2Emission",
        "Next_DowntimeMinutes"
    ]
)


# ============================================================
# FILL HISTORICAL FEATURE MISSING VALUES
# ============================================================

historical_features = [
    "Previous_EnergyKWH",
    "Previous_WaterLitres",
    "Previous_WasteKG",
    "Previous_CO2Emission",
    "Previous_DowntimeMinutes",
    "PreviousProduction",
    "PreviousVibration",
    "PreviousTemperature"
]


for column in historical_features:

    df[column] = df[column].fillna(
        df[column].median()
    )


# ============================================================
# FEATURES
# ============================================================

features = [
    "MachineID",
    "DepartmentID",

    "DepartmentType",
    "DepartmentName",

    "MachineType",
    "ProductionLine",

    "RatedPowerKW",
    "MachineAge",

    "Temperature",
    "Humidity",
    "Vibration",

    "ProductionUnits",

    "Previous_EnergyKWH",
    "Previous_WaterLitres",
    "Previous_WasteKG",
    "Previous_CO2Emission",
    "Previous_DowntimeMinutes",

    "PreviousProduction",
    "PreviousVibration",
    "PreviousTemperature",

    "Hour",
    "Minute",
    "DayOfWeek"
]


targets = [
    "Next_EnergyKWH",
    "Next_WaterLitres",
    "Next_WasteKG",
    "Next_CO2Emission",
    "Next_DowntimeMinutes"
]


df = df.dropna(
    subset=features + targets
)


print(
    f"Usable training records: {len(df)}"
)


# ============================================================
# X AND Y
# ============================================================

X = df[features]

y = df[targets]


# ============================================================
# CATEGORICAL FEATURES
# ============================================================

categorical_features = [
    "DepartmentType",
    "DepartmentName",
    "MachineType",
    "ProductionLine"
]


# ============================================================
# NUMERICAL FEATURES
# ============================================================

numerical_features = [
    column
    for column in features
    if column not in categorical_features
]


# ============================================================
# PREPROCESSING
# ============================================================

preprocessor = ColumnTransformer(

    transformers=[

        (
            "categorical",

            OneHotEncoder(
                handle_unknown="ignore"
            ),

            categorical_features
        ),

        (
            "numerical",

            "passthrough",

            numerical_features
        )
    ]
)


# ============================================================
# RANDOM FOREST
# ============================================================

model = RandomForestRegressor(

    n_estimators=300,

    max_depth=25,

    min_samples_leaf=2,

    random_state=42,

    n_jobs=-1
)


# ============================================================
# COMPLETE AI PIPELINE
# ============================================================

pipeline = Pipeline(

    steps=[

        (
            "preprocessing",
            preprocessor
        ),

        (
            "model",
            model
        )
    ]
)


# ============================================================
# TRAIN / TEST
# ============================================================

X_train, X_test, y_train, y_test = train_test_split(

    X,
    y,

    test_size=0.20,

    random_state=42
)


print("\nTraining AI model...")

pipeline.fit(
    X_train,
    y_train
)

print("Training completed.")


# ============================================================
# TEST MODEL
# ============================================================

test_predictions = pipeline.predict(
    X_test
)


# ============================================================
# MODEL PERFORMANCE
# ============================================================

print("\n")
print("=" * 75)
print("MODEL PERFORMANCE")
print("=" * 75)


for index, target in enumerate(targets):

    actual = y_test.iloc[:, index]

    predicted = test_predictions[:, index]

    mae = mean_absolute_error(
        actual,
        predicted
    )

    r2 = r2_score(
        actual,
        predicted
    )

    clean_name = target.replace(
        "Next_",
        ""
    )

    print(
        f"{clean_name:<25}"
        f" MAE: {mae:>8.2f}"
        f" | R²: {r2:>7.3f}"
    )


# ============================================================
# SAVE MODEL
# ============================================================

dump(
    pipeline,
    "industrial_sustainability_upgraded_model.pkl"
)


print(
    "\nAI model saved successfully."
)


# ============================================================
# GET LATEST RECORD FOR EACH MACHINE
# ============================================================

latest_query = """

WITH RankedData AS
(
    SELECT

        i.DataID,
        i.MachineID,
        i.DepartmentID,
        i.Timestamp,

        i.EnergyKWH,
        i.WaterLitres,
        i.WasteKG,
        i.CO2Emission,

        i.Temperature,
        i.Humidity,
        i.Vibration,

        i.ProductionUnits,
        i.DowntimeMinutes,

        i.MachineStatus,

        m.DepartmentName,
        m.MachineType,
        m.InstallationYear,
        m.ProductionLine,
        m.RatedPowerKW,

        d.DepartmentType,

        ROW_NUMBER() OVER
        (
            PARTITION BY i.MachineID
            ORDER BY i.Timestamp DESC
        ) AS rn

    FROM IndustrialData i

    INNER JOIN Machines m
        ON i.MachineID = m.MachineID

    INNER JOIN Departments d
        ON i.DepartmentID = d.DepartmentID
)

SELECT *

FROM RankedData

WHERE rn = 1

ORDER BY MachineID;

"""


connection = get_connection()

latest_df = pd.read_sql(
    latest_query,
    connection
)

connection.close()


print(
    f"\nLatest machines found: {len(latest_df)}"
)


# ============================================================
# CREATE SAME FEATURES FOR LATEST DATA
# ============================================================

latest_df["MachineAge"] = (
    CURRENT_YEAR -
    latest_df["InstallationYear"]
)


latest_df["Hour"] = (
    latest_df["Timestamp"].dt.hour
)

latest_df["Minute"] = (
    latest_df["Timestamp"].dt.minute
)

latest_df["DayOfWeek"] = (
    latest_df["Timestamp"].dt.dayofweek
)


# ============================================================
# GET HISTORICAL AVERAGES FOR LATEST MACHINES
# ============================================================

historical_query = """

SELECT

    MachineID,

    AVG(EnergyKWH) AS Previous_EnergyKWH,

    AVG(WaterLitres) AS Previous_WaterLitres,

    AVG(WasteKG) AS Previous_WasteKG,

    AVG(CO2Emission) AS Previous_CO2Emission,

    AVG(DowntimeMinutes)
        AS Previous_DowntimeMinutes,

    AVG(ProductionUnits)
        AS PreviousProduction,

    AVG(Vibration)
        AS PreviousVibration,

    AVG(Temperature)
        AS PreviousTemperature

FROM
(
    SELECT

        MachineID,
        EnergyKWH,
        WaterLitres,
        WasteKG,
        CO2Emission,
        DowntimeMinutes,
        ProductionUnits,
        Vibration,
        Temperature,

        ROW_NUMBER() OVER
        (
            PARTITION BY MachineID
            ORDER BY Timestamp DESC
        ) AS rn

    FROM IndustrialData

) x

WHERE rn <= 10

GROUP BY MachineID;

"""


connection = get_connection()

history_df = pd.read_sql(
    historical_query,
    connection
)

connection.close()


# ============================================================
# MERGE HISTORICAL FEATURES
# ============================================================

latest_df = latest_df.merge(

    history_df,

    on="MachineID",

    how="left"
)


# ============================================================
# PREDICTION FEATURES
# ============================================================

X_latest = latest_df[features]


# ============================================================
# NEXT-CYCLE PREDICTION
# ============================================================

future_predictions = pipeline.predict(
    X_latest
)


# ============================================================
# CREATE RESULT DATAFRAME
# ============================================================

prediction_df = pd.DataFrame(

    future_predictions,

    columns=[
        "PredictedEnergyKWH",
        "PredictedWaterLitres",
        "PredictedWasteKG",
        "PredictedCO2Emission",
        "PredictedDowntimeMinutes"
    ]
)


prediction_df["MachineID"] = (
    latest_df["MachineID"].values
)


prediction_df["DepartmentID"] = (
    latest_df["DepartmentID"].values
)


prediction_df["MachineStatus"] = (
    latest_df["MachineStatus"].values
)


# ============================================================
# ENSURE NON-NEGATIVE PREDICTIONS
# ============================================================

prediction_columns = [
    "PredictedEnergyKWH",
    "PredictedWaterLitres",
    "PredictedWasteKG",
    "PredictedCO2Emission",
    "PredictedDowntimeMinutes"
]


for column in prediction_columns:

    prediction_df[column] = (
        prediction_df[column].clip(lower=0)
    )


# ============================================================
# SUSTAINABILITY SCORE
#
# Score is based on comparison with historical machine
# performance instead of arbitrary fixed thresholds.
# ============================================================

baseline = history_df.copy()


prediction_df = prediction_df.merge(

    baseline[
        [
            "MachineID",
            "Previous_EnergyKWH",
            "Previous_WaterLitres",
            "Previous_WasteKG",
            "Previous_CO2Emission",
            "Previous_DowntimeMinutes"
        ]
    ],

    on="MachineID",

    how="left"
)


def performance_score(
    predicted,
    baseline_value
):

    if pd.isna(baseline_value) or baseline_value <= 0:

        return 50

    ratio = predicted / baseline_value

    score = 100 - ((ratio - 1) * 100)

    return max(
        0,
        min(100, score)
    )


# Energy
prediction_df["EnergyScore"] = prediction_df.apply(

    lambda row:
    performance_score(
        row["PredictedEnergyKWH"],
        row["Previous_EnergyKWH"]
    ),

    axis=1
)


# Water
prediction_df["WaterScore"] = prediction_df.apply(

    lambda row:
    performance_score(
        row["PredictedWaterLitres"],
        row["Previous_WaterLitres"]
    ),

    axis=1
)


# Waste
prediction_df["WasteScore"] = prediction_df.apply(

    lambda row:
    performance_score(
        row["PredictedWasteKG"],
        row["Previous_WasteKG"]
    ),

    axis=1
)


# CO2
prediction_df["CarbonScore"] = prediction_df.apply(

    lambda row:
    performance_score(
        row["PredictedCO2Emission"],
        row["Previous_CO2Emission"]
    ),

    axis=1
)


# Downtime
prediction_df["DowntimeScore"] = prediction_df.apply(

    lambda row:
    performance_score(
        row["PredictedDowntimeMinutes"],
        row["Previous_DowntimeMinutes"]
    ),

    axis=1
)


# ============================================================
# FINAL SUSTAINABILITY SCORE
# ============================================================

prediction_df["SustainabilityScore"] = (

    prediction_df["EnergyScore"] * 0.25 +

    prediction_df["WaterScore"] * 0.15 +

    prediction_df["WasteScore"] * 0.20 +

    prediction_df["CarbonScore"] * 0.25 +

    prediction_df["DowntimeScore"] * 0.15

)


prediction_df[
    "SustainabilityScore"
] = prediction_df[
    "SustainabilityScore"
].clip(0, 100).round(2)


# ============================================================
# AI RECOMMENDATION
# ============================================================

def recommendation(row):

    score = row["SustainabilityScore"]

    if score >= 85:

        return (
            "Excellent performance. "
            "Maintain current operating conditions."
        )

    elif score >= 70:

        return (
            "Good performance. "
            "Monitor energy and waste efficiency."
        )

    elif score >= 55:

        return (
            "Moderate performance. "
            "Optimize energy, water and production efficiency."
        )

    elif score >= 40:

        return (
            "Poor performance. "
            "Inspect machine efficiency and operating conditions."
        )

    else:

        return (
            "Critical condition. "
            "Immediate machine inspection recommended."
        )


prediction_df["AIRecommendation"] = (
    prediction_df.apply(
        recommendation,
        axis=1
    )
)


# ============================================================
# ROUND VALUES
# ============================================================

prediction_df[
    prediction_columns
] = prediction_df[
    prediction_columns
].round(2)


# ============================================================
# INSERT PREDICTIONS INTO SQL SERVER
# ============================================================

connection = get_connection()

cursor = connection.cursor()


insert_query = """

INSERT INTO Predictions
(
    MachineID,
    DepartmentID,
    PredictionTimestamp,

    PredictedEnergyKWH,
    PredictedWaterLitres,
    PredictedWasteKG,
    PredictedCO2Emission,
    PredictedDowntimeMinutes,

    SustainabilityScore,

    MachineStatus,
    AIRecommendation
)

VALUES
(
    ?, ?, GETDATE(),

    ?, ?, ?, ?, ?,

    ?,

    ?, ?
)

"""


for _, row in prediction_df.iterrows():

    cursor.execute(

        insert_query,

        int(row["MachineID"]),

        int(row["DepartmentID"]),

        float(
            row["PredictedEnergyKWH"]
        ),

        float(
            row["PredictedWaterLitres"]
        ),

        float(
            row["PredictedWasteKG"]
        ),

        float(
            row["PredictedCO2Emission"]
        ),

        float(
            row["PredictedDowntimeMinutes"]
        ),

        float(
            row["SustainabilityScore"]
        ),

        row["MachineStatus"],

        row["AIRecommendation"]
    )


connection.commit()

cursor.close()

connection.close()


# ============================================================
# DISPLAY RESULTS
# ============================================================

print("\n")
print("=" * 75)
print("NEXT-CYCLE AI PREDICTIONS")
print("=" * 75)


print(

    prediction_df[
        [
            "MachineID",
            "DepartmentID",
            "PredictedEnergyKWH",
            "PredictedWaterLitres",
            "PredictedWasteKG",
            "PredictedCO2Emission",
            "PredictedDowntimeMinutes",
            "SustainabilityScore"
        ]
    ].head(15).to_string(index=False)

)


print("\n")
print("=" * 75)

print(
    f"Predictions generated: "
    f"{len(prediction_df)}"
)

print(
    "Predictions inserted into SQL Server."
)

print("=" * 75)