import time
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, DoubleType
from pyspark.sql.functions import col

# Initialize Spark session (Databricks does this automatically)
spark = SparkSession.builder.appName("ShipDataProcessing").getOrCreate()

# Define the schema
schema = StructType([
    StructField("# Timestamp", StringType(), True),
    StructField("Type of mobile", StringType(), True),
    StructField("MMSI", IntegerType(), True),
    StructField("Latitude", DoubleType(), True),
    StructField("Longitude", DoubleType(), True),
    StructField("Navigational status", StringType(), True),
    StructField("ROT", DoubleType(), True),
    StructField("SOG", DoubleType(), True),
    StructField("COG", DoubleType(), True),
    StructField("Heading", DoubleType(), True),
    StructField("IMO", StringType(), True),
    StructField("Callsign", StringType(), True),
    StructField("Name", StringType(), True),
    StructField("Ship type", StringType(), True),
    StructField("Cargo type", StringType(), True),
    StructField("Width", DoubleType(), True),
    StructField("Length", DoubleType(), True),
    StructField("Type of position fixing device", StringType(), True),
    StructField("Draught", StringType(), True),
    StructField("Destination", StringType(), True),
    StructField("ETA", StringType(), True),
    StructField("Data source type", StringType(), True),
    StructField("A", StringType(), True),
    StructField("B", StringType(), True),
    StructField("C", StringType(), True),
    StructField("D", StringType(), True),
])

# Define bounding box coordinates
westbc = 12.00
eastbc = 15.00
northbc = 56.00
southbc = 54.00

# Path to CSV files on DBFS
input_path = "dbfs:/ship_data2/*.csv"

# Track the total processing time
start_time = time.time()

# Get the list of all files in the directory
files = dbutils.fs.ls("dbfs:/ship_data2/")
file_processing_times = {}

# Process each file and measure time
for file in files:
    if file.path.endswith(".csv"):
        print(f"Processing file: {file.name}")
        file_start_time = time.time()

        # Read the file
        file_df = spark.read.format("csv") \
            .option("header", "true") \
            .schema(schema) \
            .load(file.path)

        # Print one line (first row) from the file
        first_row = file_df.limit(1).collect()  # Use `.collect()` to bring the first row to the driver
        if first_row:
            print(f"First row from {file.name}: {first_row[0]}")
        else:
            print(f"File {file.name} is empty or has no valid rows.")

        # Filter the data based on the bounding box
        file_filtered_df = file_df.filter(
            (col("Longitude") >= westbc) & (col("Longitude") <= eastbc) &
            (col("Latitude") >= southbc) & (col("Latitude") <= northbc)
        )

        # Record the processing time for the file
        file_processing_time = time.time() - file_start_time
        file_processing_times[file.name] = file_processing_time

# Read all CSV files together and filter the main DataFrame
df = spark.read.format("csv") \
    .option("header", "true") \
    .schema(schema) \
    .load(input_path)

filtered_df = df.filter(
    (col("Longitude") >= westbc) & (col("Longitude") <= eastbc) &
    (col("Latitude") >= southbc) & (col("Latitude") <= northbc)
)

# Select only the needed columns
selected_columns = ["# Timestamp", "MMSI", "Latitude", "Longitude", "SOG", "Heading", "Ship type"]
final_df = filtered_df.select(*selected_columns)

# Display the DataFrame (for validation in the notebook)
final_df.show(5)

# Register the DataFrame as a temporary view for SQL access in the notebook
final_df.createOrReplaceTempView("filtered_ship_data")

# Calculate the total time
total_processing_time = time.time() - start_time

# Log processing times for each file and the total time
print("\nProcessing times for individual files:")
for file_name, processing_time in file_processing_times.items():
    print(f"{file_name}: {processing_time:.2f} seconds")

print(f"\nTotal processing time: {total_processing_time:.2f} seconds")


# Save the processed data back to DBFS or GCS bucket
#output_path = "dbfs:/processed_ship_data"
#final_df.write.format("parquet") \
#    .mode("overwrite") \
#    .save(output_path)
#
#print(f"Processed and filtered data saved to {output_path}")