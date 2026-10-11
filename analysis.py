import sqlite3
from pathlib import Path
from statistics import median

from scipy.stats import mannwhitneyu


# Locate the database in the project folder.
PROJECT_DIR = Path(__file__).resolve().parent
DATABASE_PATH = PROJECT_DIR / "cell_counts.db"


# ============================================================
# PART 2: INITIAL ANALYSIS — CELL-POPULATION FREQUENCIES
# ============================================================

def create_frequency_table(connection):
    """Calculate and store cell-population frequencies."""

    connection.executescript(
        """
        DROP TABLE IF EXISTS cell_frequencies;

        CREATE TABLE cell_frequencies (
            sample TEXT NOT NULL,
            total_count INTEGER NOT NULL,
            population TEXT NOT NULL,
            count INTEGER NOT NULL,
            percentage REAL NOT NULL,
            PRIMARY KEY (sample, population)
        );

        WITH sample_totals AS (
            SELECT
                sample_id,
                SUM(count) AS total_count
            FROM cell_counts
            GROUP BY sample_id
        )
        INSERT INTO cell_frequencies (
            sample,
            total_count,
            population,
            count,
            percentage
        )
        SELECT
            cell_counts.sample_id,
            sample_totals.total_count,
            cell_counts.population,
            cell_counts.count,
            CASE
                WHEN sample_totals.total_count = 0 THEN 0.0
                ELSE (
                    100.0 * cell_counts.count
                    / sample_totals.total_count
                )
            END AS percentage
        FROM cell_counts
        JOIN sample_totals
            ON cell_counts.sample_id = sample_totals.sample_id;
        """
    )


def display_frequency_preview(connection):
    """Display the first ten rows of the Part 2 frequency table."""

    rows = connection.execute(
        """
        SELECT
            sample,
            total_count,
            population,
            count,
            percentage
        FROM cell_frequencies
        ORDER BY sample, population
        LIMIT 10
        """
    ).fetchall()

    print(
        f"{'sample':<15}"
        f"{'total_count':<15}"
        f"{'population':<18}"
        f"{'count':<12}"
        f"{'percentage':<12}"
    )

    for sample, total_count, population, count, percentage in rows:
        print(
            f"{sample:<15}"
            f"{total_count:<15}"
            f"{population:<18}"
            f"{count:<12}"
            f"{percentage:<12.2f}"
        )


# ============================================================
# PART 3: STATISTICAL ANALYSIS
# ============================================================

def create_subject_frequencies(connection):
    """
    Filter to melanoma, miraclib, and PBMC samples.

    Calculate one mean percentage for each subject and population
    across the subject's available time points.
    """

    connection.executescript(
        """
        DROP TABLE IF EXISTS statistical_results;
        DROP TABLE IF EXISTS subject_frequencies;

        CREATE TABLE subject_frequencies (
            subject_id TEXT NOT NULL,
            response TEXT NOT NULL,
            population TEXT NOT NULL,
            mean_percentage REAL NOT NULL,
            PRIMARY KEY (subject_id, population)
        );

        INSERT INTO subject_frequencies (
            subject_id,
            response,
            population,
            mean_percentage
        )
        SELECT
            subjects.subject_id,
            subjects.response,
            cell_frequencies.population,
            AVG(cell_frequencies.percentage)
        FROM cell_frequencies
        JOIN samples
            ON cell_frequencies.sample = samples.sample_id
        JOIN subjects
            ON samples.subject_id = subjects.subject_id
        WHERE subjects.condition = 'melanoma'
          AND subjects.treatment = 'miraclib'
          AND samples.sample_type = 'PBMC'
          AND subjects.response IN ('yes', 'no')
        GROUP BY
            subjects.subject_id,
            subjects.response,
            cell_frequencies.population;
        """
    )


def adjust_p_values(p_values):
    """Apply the Benjamini-Hochberg multiple-testing correction."""

    number_of_tests = len(p_values)

    ranked_p_values = sorted(
        enumerate(p_values),
        key=lambda item: item[1]
    )

    adjusted_p_values = [0.0] * number_of_tests
    previous_adjusted_value = 1.0

    for position in range(number_of_tests - 1, -1, -1):
        original_index, p_value = ranked_p_values[position]
        rank = position + 1

        adjusted_value = min(
            previous_adjusted_value,
            p_value * number_of_tests / rank,
            1.0,
        )

        adjusted_p_values[original_index] = adjusted_value
        previous_adjusted_value = adjusted_value

    return adjusted_p_values


def create_statistical_results(connection):
    """Compare responders with non-responders for each population."""

    populations = connection.execute(
        """
        SELECT DISTINCT population
        FROM subject_frequencies
        ORDER BY population
        """
    ).fetchall()

    results = []
    p_values = []

    for (population,) in populations:
        responder_values = [
            row[0]
            for row in connection.execute(
                """
                SELECT mean_percentage
                FROM subject_frequencies
                WHERE population = ?
                  AND response = 'yes'
                """,
                (population,),
            ).fetchall()
        ]

        non_responder_values = [
            row[0]
            for row in connection.execute(
                """
                SELECT mean_percentage
                FROM subject_frequencies
                WHERE population = ?
                  AND response = 'no'
                """,
                (population,),
            ).fetchall()
        ]

        test_result = mannwhitneyu(
            responder_values,
            non_responder_values,
            alternative="two-sided",
            method="asymptotic",
        )

        responder_median = median(responder_values)
        non_responder_median = median(non_responder_values)

        median_difference = (
            responder_median - non_responder_median
        )

        rank_biserial_correlation = (
            2 * test_result.statistic
            / (len(responder_values) * len(non_responder_values))
            - 1
        )

        results.append(
            {
                "population": population,
                "responders": len(responder_values),
                "non_responders": len(non_responder_values),
                "responder_median": responder_median,
                "non_responder_median": non_responder_median,
                "median_difference": median_difference,
                "u_statistic": test_result.statistic,
                "p_value": test_result.pvalue,
                "rank_biserial": rank_biserial_correlation,
            }
        )

        p_values.append(test_result.pvalue)

    adjusted_p_values = adjust_p_values(p_values)

    connection.execute(
        """
        CREATE TABLE statistical_results (
            population TEXT PRIMARY KEY,
            responders INTEGER NOT NULL,
            non_responders INTEGER NOT NULL,
            responder_median REAL NOT NULL,
            non_responder_median REAL NOT NULL,
            median_difference REAL NOT NULL,
            u_statistic REAL NOT NULL,
            p_value REAL NOT NULL,
            adjusted_p_value REAL NOT NULL,
            rank_biserial REAL NOT NULL,
            significant INTEGER NOT NULL
        )
        """
    )

    for result, adjusted_p_value in zip(
        results,
        adjusted_p_values,
    ):
        connection.execute(
            """
            INSERT INTO statistical_results (
                population,
                responders,
                non_responders,
                responder_median,
                non_responder_median,
                median_difference,
                u_statistic,
                p_value,
                adjusted_p_value,
                rank_biserial,
                significant
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result["population"],
                result["responders"],
                result["non_responders"],
                result["responder_median"],
                result["non_responder_median"],
                result["median_difference"],
                result["u_statistic"],
                result["p_value"],
                adjusted_p_value,
                result["rank_biserial"],
                int(adjusted_p_value < 0.05),
            ),
        )


def display_statistical_results(connection):
    """Display the Part 3 statistical results."""

    rows = connection.execute(
        """
        SELECT
            population,
            responders,
            non_responders,
            responder_median,
            non_responder_median,
            median_difference,
            p_value,
            adjusted_p_value,
            rank_biserial,
            significant
        FROM statistical_results
        ORDER BY population
        """
    ).fetchall()

    print(
        f"{'population':<16}"
        f"{'yes_n':>8}"
        f"{'no_n':>8}"
        f"{'yes_med':>12}"
        f"{'no_med':>12}"
        f"{'difference':>13}"
        f"{'p_value':>13}"
        f"{'adj_p':>13}"
        f"{'effect':>11}"
        f"{'significant':>14}"
    )

    for row in rows:
        (
            population,
            responders,
            non_responders,
            responder_median,
            non_responder_median,
            median_difference,
            p_value,
            adjusted_p_value,
            rank_biserial,
            significant,
        ) = row

        print(
            f"{population:<16}"
            f"{responders:>8}"
            f"{non_responders:>8}"
            f"{responder_median:>12.2f}"
            f"{non_responder_median:>12.2f}"
            f"{median_difference:>13.2f}"
            f"{p_value:>13.3e}"
            f"{adjusted_p_value:>13.3e}"
            f"{rank_biserial:>11.3f}"
            f"{('yes' if significant else 'no'):>14}"
        )


# ============================================================
# PART 4: DATA SUBSET ANALYSIS
# ============================================================

def create_subset_analysis(connection):
    """Create and summarize the requested Part 4 subsets."""

    connection.executescript(
        """
        DROP TABLE IF EXISTS subset_summary;
        DROP TABLE IF EXISTS part4_results;
        DROP TABLE IF EXISTS baseline_subset;

        CREATE TABLE baseline_subset (
            sample TEXT PRIMARY KEY,
            subject_id TEXT NOT NULL,
            project TEXT NOT NULL,
            response TEXT NOT NULL,
            sex TEXT NOT NULL
        );

        INSERT INTO baseline_subset (
            sample,
            subject_id,
            project,
            response,
            sex
        )
        SELECT
            samples.sample_id,
            subjects.subject_id,
            subjects.project,
            subjects.response,
            subjects.sex
        FROM samples
        JOIN subjects
            ON samples.subject_id = subjects.subject_id
        WHERE subjects.condition = 'melanoma'
          AND subjects.treatment = 'miraclib'
          AND samples.sample_type = 'PBMC'
          AND samples.time_from_treatment_start = 0;

        CREATE TABLE subset_summary (
            metric TEXT NOT NULL,
            category TEXT NOT NULL,
            count INTEGER NOT NULL,
            PRIMARY KEY (metric, category)
        );

        INSERT INTO subset_summary (
            metric,
            category,
            count
        )
        SELECT
            'samples_by_project',
            project,
            COUNT(*)
        FROM baseline_subset
        GROUP BY project;

        INSERT INTO subset_summary (
            metric,
            category,
            count
        )
        SELECT
            'subjects_by_response',
            response,
            COUNT(DISTINCT subject_id)
        FROM baseline_subset
        GROUP BY response;

        INSERT INTO subset_summary (
            metric,
            category,
            count
        )
        SELECT
            'subjects_by_sex',
            sex,
            COUNT(DISTINCT subject_id)
        FROM baseline_subset
        GROUP BY sex;

        CREATE TABLE part4_results (
            metric TEXT PRIMARY KEY,
            sample_count INTEGER NOT NULL,
            result_value REAL NOT NULL
        );

        INSERT INTO part4_results (
            metric,
            sample_count,
            result_value
        )
        SELECT
            'average_b_cells_melanoma_male_responders_time_0',
            COUNT(*),
            ROUND(AVG(cell_counts.count), 2)
        FROM cell_counts
        JOIN samples
            ON cell_counts.sample_id = samples.sample_id
        JOIN subjects
            ON samples.subject_id = subjects.subject_id
        WHERE subjects.condition = 'melanoma'
          AND subjects.sex = 'M'
          AND subjects.response = 'yes'
          AND samples.time_from_treatment_start = 0
          AND cell_counts.population = 'b_cell';
        """
    )


def display_subset_results(connection):
    """Display the Part 4 subset-analysis results."""

    baseline_count = connection.execute(
        "SELECT COUNT(*) FROM baseline_subset"
    ).fetchone()[0]

    print(f"Baseline melanoma/miraclib/PBMC samples: {baseline_count}")

    print("\nSamples by project:")
    project_rows = connection.execute(
        """
        SELECT category, count
        FROM subset_summary
        WHERE metric = 'samples_by_project'
        ORDER BY category
        """
    ).fetchall()

    for project, count in project_rows:
        print(f"  {project}: {count}")

    print("\nSubjects by response:")
    response_rows = connection.execute(
        """
        SELECT category, count
        FROM subset_summary
        WHERE metric = 'subjects_by_response'
        ORDER BY category
        """
    ).fetchall()

    for response, count in response_rows:
        print(f"  {response}: {count}")

    print("\nSubjects by sex:")
    sex_rows = connection.execute(
        """
        SELECT category, count
        FROM subset_summary
        WHERE metric = 'subjects_by_sex'
        ORDER BY category
        """
    ).fetchall()

    for sex, count in sex_rows:
        print(f"  {sex}: {count}")

    sample_count, average_b_cells = connection.execute(
        """
        SELECT sample_count, result_value
        FROM part4_results
        WHERE metric =
            'average_b_cells_melanoma_male_responders_time_0'
        """
    ).fetchone()

    print(
        "\nAverage B-cell count for melanoma male responders "
        "at time 0:"
    )
    print(f"  Samples included: {sample_count}")
    print(f"  Average B-cell count: {average_b_cells:.2f}")

    print(
        "\nNote: quintazide is mentioned in the assignment brief, "
        "but it is not a treatment value in this dataset."
    )


def main():
    """Run Parts 2, 3, and 4 of the analysis pipeline."""

    if not DATABASE_PATH.exists():
        raise FileNotFoundError(
            "Database not found. Run 'python load_data.py' first."
        )

    with sqlite3.connect(DATABASE_PATH) as connection:
        # Part 2
        create_frequency_table(connection)

        frequency_rows = connection.execute(
            "SELECT COUNT(*) FROM cell_frequencies"
        ).fetchone()[0]

        print("\nPART 2: CELL-POPULATION FREQUENCIES")
        print(f"Created {frequency_rows} frequency rows.\n")
        display_frequency_preview(connection)

        # Part 3
        create_subject_frequencies(connection)
        create_statistical_results(connection)

        subject_frequency_rows = connection.execute(
            "SELECT COUNT(*) FROM subject_frequencies"
        ).fetchone()[0]

        print("\nPART 3: RESPONDER VS NON-RESPONDER ANALYSIS")
        print(
            f"Created {subject_frequency_rows} "
            "subject-level frequency rows.\n"
        )
        display_statistical_results(connection)

        # Part 4
        create_subset_analysis(connection)

        print("\nPART 4: DATA SUBSET ANALYSIS")
        display_subset_results(connection)


if __name__ == "__main__":
    main()