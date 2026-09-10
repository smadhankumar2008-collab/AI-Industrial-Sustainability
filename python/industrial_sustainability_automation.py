import pyodbc
import pandas as pd
import numpy as np
import time
import traceback

from datetime import datetime
from joblib import load


# ============================================================
# CONFIGURATION
# ============================================================

SERVER = r".\SQLEXPRESS"
DATABASE = "IndustrialSustainability"

INTERVAL_SECONDS = 10

MODEL_FILE = "industrial_sustainability_upgraded_model.pkl"


CONNECTION_STRING = (
    "DRIVER={ODBC Driver 18 for SQL Server};"
    f"SERVER={SERVER};"
    f"DATABASE={DATABASE};"
    "Trusted_Connection=yes;"
    "TrustServerCertificate=yes;"
)


# ============================================================
# LOAD AI MODEL
# ============================================================

print("=" * 75)
print("AI-POWERED INDUSTRIAL SUSTAINABILITY PLATFORM")
print("PHASE 4 - REAL-TIME AI AUTOMATION")
print("=" * 75)


print("\nLoading AI model...")

try:

    model = load(MODEL_FILE)

    print("AI model loaded successfully.")

except Exception as e:

    print("\nERROR: AI model could not be loaded.")

    print(e)

    print(
        "\nMake sure this file exists:"
    )

    print(MODEL_FILE)

    raise SystemExit


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection():

    return pyodbc.connect(
        CONNECTION_STRING
    )


# ============================================================
# GET MACHINES
# ============================================================

def get_machines():

    connection = get_connection()

    query = """

    SELECT

        MachineID,
        DepartmentID,
        MachineName,
        MachineType,
        MachineStatus,
        RatedPowerKW

    FROM Machines

    ORDER BY MachineID;

    """

    df = pd.read_sql(
        query,
        connection
    )

    connection.close()

    return df


# ============================================================
# GENERATE MACHINE DATA
# ============================================================

def generate_machine_data(machine):

    machine_id = int(
        machine["MachineID"]
    )

    department_id = int(
        machine["DepartmentID"]
    )

    machine_type = str(
        machine["MachineType"]
    )

    status = str(
        machine["MachineStatus"]
    )

    rated_power = float(
        machine["RatedPowerKW"]
    )


    # --------------------------------------------------------
    # RUNNING
    # --------------------------------------------------------

    if status == "Running":

        energy = (
            rated_power *
            np.random.uniform(
                0.60,
                1.00
            )
        )

        water = np.random.uniform(
            5,
            50
        )

        waste = np.random.uniform(
            1,
            15
        )

        production = np.random.randint(
            20,
            100
        )

        downtime = np.random.randint(
            0,
            3
        )

        temperature = np.random.uniform(
            28,
            40
        )

        humidity = np.random.uniform(
            40,
            75
        )

        vibration = np.random.uniform(
            0.20,
            1.20
        )


    # --------------------------------------------------------
    # STANDBY
    # --------------------------------------------------------

    elif status == "Standby":

        energy = (
            rated_power *
            np.random.uniform(
                0.05,
                0.15
            )
        )

        water = np.random.uniform(
            0,
            5
        )

        waste = np.random.uniform(
            0.1,
            1
        )

        production = np.random.randint(
            0,
            5
        )

        downtime = np.random.randint(
            0,
            5
        )

        temperature = np.random.uniform(
            24,
            30
        )

        humidity = np.random.uniform(
            40,
            60
        )

        vibration = np.random.uniform(
            0.05,
            0.30
        )


    # --------------------------------------------------------
    # MAINTENANCE
    # --------------------------------------------------------

    else:

        energy = (
            rated_power *
            np.random.uniform(
                0.10,
                0.30
            )
        )

        water = np.random.uniform(
            2,
            15
        )

        waste = np.random.uniform(
            0.5,
            3
        )

        production = np.random.randint(
            0,
            3
        )

        downtime = np.random.randint(
            5,
            15
        )

        temperature = np.random.uniform(
            25,
            32
        )

        humidity = np.random.uniform(
            40,
            65
        )

        vibration = np.random.uniform(
            0.10,
            0.50
        )


    # ========================================================
    # MACHINE TYPE ADJUSTMENTS
    # ========================================================

    machine_type_lower = machine_type.lower()


    if "boiler" in machine_type_lower:

        energy *= 1.20
        water *= 1.50
        temperature += 10
        waste *= 1.20


    elif "chiller" in machine_type_lower:

        energy *= 1.30
        water *= 1.30


    elif "cnc" in machine_type_lower:

        energy *= 1.10
        vibration *= 1.20
        waste *= 1.30


    elif "injection" in machine_type_lower:

        energy *= 1.25
        water *= 1.20
        waste *= 1.50


    elif "welding" in machine_type_lower:

        energy *= 1.15
        temperature += 5


    elif "forklift" in machine_type_lower:

        energy *= 0.80
        production *= 0.70


    # ========================================================
    # CO2 CALCULATION
    # ========================================================

    co2 = (
        energy *
        np.random.uniform(
            0.40,
            0.55
        )
    )


    # ========================================================
    # RETURN
    # ========================================================

    return (

        machine_id,

        department_id,

        datetime.now(),

        round(max(0, energy), 2),

        round(max(0, water), 2),

        round(max(0, waste), 2),

        round(max(0, co2), 2),

        round(temperature, 2),

        round(humidity, 2),

        round(vibration, 3),

        int(production),

        int(downtime),

        status
    )


# ============================================================
# INSERT INDUSTRIAL DATA
# ============================================================

def generate_and_insert_data():

    machines = get_machines()


    if machines.empty:

        raise Exception(
            "No machines found in Machines table."
        )


    records = []


    for _, machine in machines.iterrows():

        records.append(
            generate_machine_data(
                machine
            )
        )


    connection = get_connection()

    cursor = connection.cursor()

    cursor.fast_executemany = True


    query = """

    INSERT INTO IndustrialData
    (
        MachineID,
        DepartmentID,
        Timestamp,

        EnergyKWH,
        WaterLitres,
        WasteKG,
        CO2Emission,

        Temperature,
        Humidity,
        Vibration,

        ProductionUnits,
        DowntimeMinutes,

        MachineStatus
    )

    VALUES
    (
        ?, ?, ?,
        ?, ?, ?, ?,
        ?, ?, ?,
        ?, ?, ?
    )

    """


    cursor.executemany(
        query,
        records
    )


    connection.commit()

    cursor.close()

    connection.close()


    return len(records)


# ============================================================
# LOAD LATEST MACHINE DATA
# ============================================================

def get_latest_machine_data():

    connection = get_connection()


    query = """

    WITH LatestData AS
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

            ON i.MachineID =
               m.MachineID

        INNER JOIN Departments d

            ON i.DepartmentID =
               d.DepartmentID

    )

    SELECT *

    FROM LatestData

    WHERE rn = 1

    ORDER BY MachineID;

    """


    latest_df = pd.read_sql(
        query,
        connection
    )


    connection.close()


    return latest_df


# ============================================================
# GET HISTORICAL MACHINE DATA
# ============================================================

def get_historical_features():

    connection = get_connection()


    query = """

    WITH RankedData AS
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

    )

    SELECT

        MachineID,

        AVG(EnergyKWH)
            AS Previous_EnergyKWH,

        AVG(WaterLitres)
            AS Previous_WaterLitres,

        AVG(WasteKG)
            AS Previous_WasteKG,

        AVG(CO2Emission)
            AS Previous_CO2Emission,

        AVG(DowntimeMinutes)
            AS Previous_DowntimeMinutes,

        AVG(ProductionUnits)
            AS PreviousProduction,

        AVG(Vibration)
            AS PreviousVibration,

        AVG(Temperature)
            AS PreviousTemperature

    FROM RankedData

    WHERE rn <= 10

    GROUP BY MachineID;

    """


    history_df = pd.read_sql(
        query,
        connection
    )


    connection.close()


    return history_df


# ============================================================
# CREATE AI FEATURES
# ============================================================

def create_features(
    latest_df,
    history_df
):

    df = latest_df.copy()


    # --------------------------------------------------------
    # Machine age
    # --------------------------------------------------------

    current_year = datetime.now().year

    df["MachineAge"] = (

        current_year -
        df["InstallationYear"]

    ).clip(lower=0)


    # --------------------------------------------------------
    # Time features
    # --------------------------------------------------------

    df["Timestamp"] = pd.to_datetime(
        df["Timestamp"]
    )


    df["Hour"] = (
        df["Timestamp"].dt.hour
    )

    df["Minute"] = (
        df["Timestamp"].dt.minute
    )

    df["DayOfWeek"] = (
        df["Timestamp"].dt.dayofweek
    )


    # --------------------------------------------------------
    # Historical averages
    # --------------------------------------------------------

    df = df.merge(

        history_df,

        on="MachineID",

        how="left"
    )


    # --------------------------------------------------------
    # Features required by model
    # --------------------------------------------------------

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


    # Fill missing historical values

    historical_columns = [

        "Previous_EnergyKWH",
        "Previous_WaterLitres",
        "Previous_WasteKG",
        "Previous_CO2Emission",
        "Previous_DowntimeMinutes",

        "PreviousProduction",
        "PreviousVibration",
        "PreviousTemperature"

    ]


    for column in historical_columns:

        df[column] = df[column].fillna(
            df[column].median()
        )


    return df, features


# ============================================================
# CALCULATE SUSTAINABILITY SCORE
# ============================================================

def calculate_scores(
    predictions,
    history_df
):

    result = predictions.copy()


    result = result.merge(

        history_df,

        on="MachineID",

        how="left"
    )


    def score(
        predicted,
        baseline
    ):

        if (
            pd.isna(baseline)
            or baseline <= 0
        ):

            return 50


        ratio = (
            predicted /
            baseline
        )


        value = (
            100 -
            ((ratio - 1) * 100)
        )


        return max(
            0,
            min(100, value)
        )


    result["EnergyScore"] = result.apply(

        lambda row:

        score(
            row["PredictedEnergyKWH"],
            row["Previous_EnergyKWH"]
        ),

        axis=1
    )


    result["WaterScore"] = result.apply(

        lambda row:

        score(
            row["PredictedWaterLitres"],
            row["Previous_WaterLitres"]
        ),

        axis=1
    )


    result["WasteScore"] = result.apply(

        lambda row:

        score(
            row["PredictedWasteKG"],
            row["Previous_WasteKG"]
        ),

        axis=1
    )


    result["CarbonScore"] = result.apply(

        lambda row:

        score(
            row["PredictedCO2Emission"],
            row["Previous_CO2Emission"]
        ),

        axis=1
    )


    result["DowntimeScore"] = result.apply(

        lambda row:

        score(
            row["PredictedDowntimeMinutes"],
            row["Previous_DowntimeMinutes"]
        ),

        axis=1
    )


    # ========================================================
    # WEIGHTED SCORE
    # ========================================================

    result["SustainabilityScore"] = (

        result["EnergyScore"] * 0.25 +

        result["WaterScore"] * 0.15 +

        result["WasteScore"] * 0.20 +

        result["CarbonScore"] * 0.25 +

        result["DowntimeScore"] * 0.15

    )


    result[
        "SustainabilityScore"
    ] = result[
        "SustainabilityScore"
    ].clip(
        0,
        100
    ).round(2)


    return result


# ============================================================
# AI RECOMMENDATION
# ============================================================

def generate_recommendation(
    row
):

    score = row[
        "SustainabilityScore"
    ]


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


# ============================================================
# INSERT PREDICTIONS
# ============================================================

def insert_predictions(
    result
):

    connection = get_connection()

    cursor = connection.cursor()


    query = """

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


    records = []


    for _, row in result.iterrows():

        records.append(

            (

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

                str(
                    row["MachineStatus"]
                ),

                str(
                    row["AIRecommendation"]
                )

            )

        )


    cursor.fast_executemany = True


    cursor.executemany(
        query,
        records
    )


    connection.commit()


    cursor.close()

    connection.close()


    return len(records)


# ============================================================
# ONE COMPLETE AI CYCLE
# ============================================================

def run_cycle():

    print("\n" + "=" * 75)

    print(
        "CYCLE START:",
        datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )

    print("=" * 75)


    # --------------------------------------------------------
    # STEP 1
    # Generate industrial data
    # --------------------------------------------------------

    records = (
        generate_and_insert_data()
    )


    print(
        f"[1/5] Industrial records inserted: "
        f"{records}"
    )


    # --------------------------------------------------------
    # STEP 2
    # Get latest data
    # --------------------------------------------------------

    latest_df = (
        get_latest_machine_data()
    )


    print(
        f"[2/5] Latest machines loaded: "
        f"{len(latest_df)}"
    )


    # --------------------------------------------------------
    # STEP 3
    # Historical features
    # --------------------------------------------------------

    history_df = (
        get_historical_features()
    )


    print(
        "[3/5] Historical features calculated"
    )


    # --------------------------------------------------------
    # STEP 4
    # AI prediction
    # --------------------------------------------------------

    feature_df, features = (
        create_features(
            latest_df,
            history_df
        )
    )


    X_latest = feature_df[
        features
    ]


    predictions = model.predict(
        X_latest
    )


    prediction_result = pd.DataFrame(

        predictions,

        columns=[

            "PredictedEnergyKWH",

            "PredictedWaterLitres",

            "PredictedWasteKG",

            "PredictedCO2Emission",

            "PredictedDowntimeMinutes"

        ]

    )


    prediction_result[
        "MachineID"
    ] = feature_df[
        "MachineID"
    ].values


    prediction_result[
        "DepartmentID"
    ] = feature_df[
        "DepartmentID"
    ].values


    prediction_result[
        "MachineStatus"
    ] = feature_df[
        "MachineStatus"
    ].values


    # Prevent negative predictions

    prediction_columns = [

        "PredictedEnergyKWH",
        "PredictedWaterLitres",
        "PredictedWasteKG",
        "PredictedCO2Emission",
        "PredictedDowntimeMinutes"

    ]


    for column in prediction_columns:

        prediction_result[column] = (

            prediction_result[column]
            .clip(lower=0)
            .round(2)

        )


    print(
        "[4/5] AI predictions generated"
    )


    # --------------------------------------------------------
    # STEP 5
    # Sustainability
    # --------------------------------------------------------

    result = calculate_scores(

        prediction_result,

        history_df

    )


    result[
        "AIRecommendation"
    ] = result.apply(

        generate_recommendation,

        axis=1

    )


    inserted = insert_predictions(
        result
    )


    print(
        f"[5/5] Predictions inserted: "
        f"{inserted}"
    )


    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    print("\nCycle Summary")

    print(
        f"Machines processed : "
        f"{inserted}"
    )


    print(
        f"Average energy     : "
        f"{result['PredictedEnergyKWH'].mean():.2f} KWh"
    )


    print(
        f"Average waste      : "
        f"{result['PredictedWasteKG'].mean():.2f} KG"
    )


    print(
        f"Average CO2        : "
        f"{result['PredictedCO2Emission'].mean():.2f}"
    )


    print(
        f"Average score      : "
        f"{result['SustainabilityScore'].mean():.2f}"
    )


    critical = (
        result[
            "SustainabilityScore"
        ] < 40
    ).sum()


    print(
        f"Critical machines  : "
        f"{critical}"
    )


# ============================================================
# MAIN AUTOMATION LOOP
# ============================================================

print("\nSystem is ready.")

print(
    f"Automation interval: "
    f"{INTERVAL_SECONDS} seconds"
)

print(
    "Press CTRL+C to stop."
)


try:

    while True:

        start_time = time.time()


        try:

            run_cycle()


        except Exception as error:

            print("\nERROR IN CYCLE")

            print(error)

            traceback.print_exc()


        elapsed = (
            time.time() -
            start_time
        )


        wait_time = max(
            0,
            INTERVAL_SECONDS - elapsed
        )


        print(
            f"\nNext cycle in "
            f"{wait_time:.1f} seconds..."
        )


        time.sleep(
            wait_time
        )


except KeyboardInterrupt:

    print("\n")
    print("=" * 75)
    print("AUTOMATION STOPPED")
    print("=" * 75)