import csv
import sqlite3
from pathlib import Path


# Locate the folder containing this Python script.
PROJECT_DIR = Path(__file__).resolve().parent

# Build paths to the input CSV and output database.
CSV_PATH = PROJECT_DIR / "cell-count.csv"
DATABASE_PATH = PROJECT_DIR / "cell_counts.db"

# The five population columns present in the CSV file.
CELL_POPULATIONS = [
    "b_cell",
    "cd8_t_cell",
    "cd4_t_cell",
    "nk_cell",
    "monocyte",
]


def create_tables(connection):
    """Create the database tables."""

    connection.executescript(
        """
        DROP TABLE IF EXISTS cell_counts;
        DROP TABLE IF EXISTS samples;
        DROP TABLE IF EXISTS subjects;

        CREATE TABLE subjects (
            subject_id TEXT PRIMARY KEY,
            project TEXT NOT NULL,
            condition TEXT NOT NULL,
            age INTEGER NOT NULL,
            sex TEXT NOT NULL,
            treatment TEXT NOT NULL,
            response TEXT
        );

        CREATE TABLE samples (
            sample_id TEXT PRIMARY KEY,
            subject_id TEXT NOT NULL,
            sample_type TEXT NOT NULL,
            time_from_treatment_start INTEGER NOT NULL,
            FOREIGN KEY (subject_id) REFERENCES subjects(subject_id)
        );

        CREATE TABLE cell_counts (
            sample_id TEXT NOT NULL,
            population TEXT NOT NULL,
            count INTEGER NOT NULL,
            PRIMARY KEY (sample_id, population),
            FOREIGN KEY (sample_id) REFERENCES samples(sample_id)
        );
        """
    )


def load_csv(connection):
    """Read the CSV file and insert its data into the database."""

    with CSV_PATH.open(mode="r", newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)

        for row in reader:
            connection.execute(
                """
                INSERT OR IGNORE INTO subjects (
                    subject_id,
                    project,
                    condition,
                    age,
                    sex,
                    treatment,
                    response
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["subject"],
                    row["project"],
                    row["condition"],
                    int(row["age"]),
                    row["sex"],
                    row["treatment"],
                    row["response"] or None,
                ),
            )

            connection.execute(
                """
                INSERT INTO samples (
                    sample_id,
                    subject_id,
                    sample_type,
                    time_from_treatment_start
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    row["sample"],
                    row["subject"],
                    row["sample_type"],
                    int(row["time_from_treatment_start"]),
                ),
            )

            for population in CELL_POPULATIONS:
                connection.execute(
                    """
                    INSERT INTO cell_counts (
                        sample_id,
                        population,
                        count
                    )
                    VALUES (?, ?, ?)
                    """,
                    (
                        row["sample"],
                        population,
                        int(row[population]),
                    ),
                )


def main():
    """Create the database and load the CSV data."""

    if not CSV_PATH.exists():
        raise FileNotFoundError(f"CSV file not found: {CSV_PATH}")

    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        create_tables(connection)
        load_csv(connection)

    print(f"Database created successfully: {DATABASE_PATH.name}")


if __name__ == "__main__":
    main()