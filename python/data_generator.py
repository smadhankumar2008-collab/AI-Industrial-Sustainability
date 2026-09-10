import pyodbc
import random
import time
from datetime import datetime


# ============================================================
# SQL SERVER CONNECTION
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


# ============================================================
# CONNECT TO SQL SERVER
# ============================================================

def get_connection():

    return pyodbc.connect(CONNECTION_STRING)


# ============================================================
# GENERATE INDUSTRIAL DATA
# ============================================================

def generate_machine_data(machine):

    machine_id = machine[0]
    department_id = machine[1]
    machine_name = machine[2]
    machine_type = machine[3]
    machine_status = machine[4]
    rated_power = float(machine[5])

    # --------------------------------------------------------
    # Machine status
    # --------------------------------------------------------

    status = machine_status

    # --------------------------------------------------------
    # Standby machine
    # --------------------------------------------------------

    if status == "Standby":

        energy = rated_power * random.uniform(0.05, 0.15)

        water = random.uniform(0, 5)

        waste = random.uniform(0.1, 1.0)

        production = random.randint(0, 5)

        downtime = random.randint(0, 5)

        temperature = random.uniform(24, 30)

        humidity = random.uniform(40, 60)

        vibration = random.uniform(0.05, 0.30)

    # --------------------------------------------------------
    # Maintenance machine
    # --------------------------------------------------------

    elif status == "Maintenance":

        energy = rated_power * random.uniform(0.10, 0.30)

        water = random.uniform(2, 15)

        waste = random.uniform(0.5, 3)

        production = random.randint(0, 3)

        downtime = random.randint(5, 15)

        temperature = random.uniform(25, 32)

        humidity = random.uniform(40, 65)

        vibration = random.uniform(0.10, 0.50)

    # --------------------------------------------------------
    # Running machine
    # --------------------------------------------------------

    else:

        energy = rated_power * random.uniform(0.60, 1.00)

        water = random.uniform(5, 50)

        waste = random.uniform(1, 15)

        production = random.randint(20, 100)

        downtime = random.randint(0, 3)

        temperature = random.uniform(28, 40)

        humidity = random.uniform(40, 75)

        vibration = random.uniform(0.20, 1.20)

    # --------------------------------------------------------
    # Machine-specific adjustments
    # --------------------------------------------------------

    if "Boiler" in machine_type:

        energy *= 1.20
        water *= 1.50
        temperature += 10
        waste *= 1.20

    elif "Chiller" in machine_type:

        energy *= 1.30
        water *= 1.30

    elif "CNC" in machine_type:

        energy *= 1.10
        vibration *= 1.20
        waste *= 1.30

    elif "Injection" in machine_type:

        energy *= 1.25
        water *= 1.20
        waste *= 1.50

    elif "Welding" in machine_type:

        energy *= 1.15
        temperature += 5

    elif "Forklift" in machine_type:

        energy *= 0.80
        production *= 0.70

    # --------------------------------------------------------
    # CO2 estimation
    # Approximate emission factor
    # --------------------------------------------------------

    co2 = energy * random.uniform(0.40, 0.55)

    # --------------------------------------------------------
    # Round values
    # --------------------------------------------------------

    energy = round(max(0, energy), 2)
    water = round(max(0, water), 2)
    waste = round(max(0, waste), 2)
    co2 = round(max(0, co2), 2)

    temperature = round(temperature, 2)
    humidity = round(humidity, 2)
    vibration = round(vibration, 3)

    return (
        machine_id,
        department_id,
        datetime.now(),
        energy,
        water,
        waste,
        co2,
        temperature,
        humidity,
        vibration,
        production,
        downtime,
        status
    )


# ============================================================
# INSERT DATA INTO SQL SERVER
# ============================================================

def insert_data():

    connection = None

    try:

        connection = get_connection()

        cursor = connection.cursor()

        # Get all 100 machines

        cursor.execute("""
            SELECT
                MachineID,
                DepartmentID,
                MachineName,
                MachineType,
                MachineStatus,
                RatedPowerKW
            FROM Machines
            ORDER BY MachineID
        """)

        machines = cursor.fetchall()

        if len(machines) == 0:

            print("ERROR: No machines found.")

            return

        print(f"Machines found: {len(machines)}")

        data = []

        for machine in machines:

            row = generate_machine_data(machine)

            data.append(row)

        # ----------------------------------------------------
        # Bulk insert
        # ----------------------------------------------------

        cursor.fast_executemany = True

        cursor.executemany("""
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
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, data)

        connection.commit()

        print(
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
            f"Inserted {len(data)} records"
        )

    except Exception as e:

        print("ERROR:", e)

        if connection:
            connection.rollback()

    finally:

        if connection:
            connection.close()


# ============================================================
# AUTOMATION LOOP
# ============================================================

print("=" * 60)
print("INDUSTRIAL SUSTAINABILITY AUTOMATION")
print("=" * 60)

print("Database:", DATABASE)
print("Server:", SERVER)
print("Interval: 10 seconds")
print("Press CTRL+C to stop")
print("=" * 60)


try:

    while True:

        insert_data()

        time.sleep(10)

except KeyboardInterrupt:

    print("\nAutomation stopped by user.")