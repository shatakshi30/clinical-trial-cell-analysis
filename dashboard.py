import sqlite3
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


PROJECT_DIR = Path(__file__).resolve().parent
DATABASE_PATH = PROJECT_DIR / "cell_counts.db"

REQUIRED_TABLES = {
    "subjects",
    "samples",
    "cell_counts",
    "cell_frequencies",
    "subject_frequencies",
    "statistical_results",
    "baseline_subset",
    "subset_summary",
    "part4_results",
}

POPULATION_LABELS = {
    "b_cell": "B cells",
    "cd4_t_cell": "CD4 T cells",
    "cd8_t_cell": "CD8 T cells",
    "monocyte": "Monocytes",
    "nk_cell": "NK cells",
}

POPULATION_ORDER = [
    "B cells",
    "CD4 T cells",
    "CD8 T cells",
    "Monocytes",
    "NK cells",
]

RESPONSE_LABELS = {
    "no": "Non-responder",
    "yes": "Responder",
}

RESPONSE_COLORS = {
    "Non-responder": "#52657a",
    "Responder": "#0e9f8b",
}


st.set_page_config(
    page_title="Immune Response Explorer",
    page_icon="🧬",
    layout="wide",
)


st.markdown(
    """
    <style>
        .stApp {
            background: #f5f8fa;
        }
        .block-container {
            max-width: 1480px;
            padding-top: 2rem;
            padding-bottom: 4rem;
        }
        .hero {
            padding: 2rem 2.2rem;
            border-radius: 20px;
            background: linear-gradient(125deg, #102a43 0%, #174f5c 62%, #0e9f8b 100%);
            color: white;
            margin-bottom: 1.4rem;
            box-shadow: 0 14px 32px rgba(16, 42, 67, 0.16);
        }
        .hero-kicker {
            color: #9ff3df;
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.13em;
            text-transform: uppercase;
            margin-bottom: 0.55rem;
        }
        .hero h1 {
            color: white !important;
            font-size: 2.35rem;
            line-height: 1.12;
            margin: 0;
        }
        .hero p {
            color: #dbe9ee !important;
            font-size: 1.02rem;
            max-width: 850px;
            margin: 0.8rem 0 0;
        }
        div[data-testid="stMetric"] {
            background: white;
            border: 1px solid #dce6eb;
            border-radius: 14px;
            padding: 0.9rem 1rem;
            box-shadow: 0 5px 18px rgba(16, 42, 67, 0.06);
        }
        div[data-testid="stMetricLabel"] {
            color: #52657a !important;
        }
        div[data-testid="stMetricLabel"] p {
            color: #52657a !important;
        }
        div[data-testid="stMetricValue"] {
            color: #102a43 !important;
        }
        .stApp h1, .stApp h2, .stApp h3, .stApp h4 {
            color: #102a43 !important;
        }
        .stApp .hero h1 {
            color: white !important;
        }
        .stApp [data-testid="stMarkdownContainer"] p {
            color: #334e68;
        }
        .stApp [data-testid="stWidgetLabel"] p,
        .stApp [data-testid="stCaptionContainer"] p,
        .stApp label {
            color: #334e68 !important;
        }
        .stApp .hero p {
            color: #dbe9ee !important;
        }
        .stApp .hero-kicker {
            color: #9ff3df !important;
        }
        .section-note {
            background: white;
            border-left: 4px solid #0e9f8b;
            border-radius: 8px;
            padding: 0.85rem 1rem;
            margin: 0.4rem 0 1rem;
            color: #334e68;
        }
        div[data-baseweb="tab-list"] {
            gap: 0.65rem;
            background: white;
            border: 1px solid #dce6eb;
            border-radius: 14px;
            padding: 0.45rem;
            margin-bottom: 1.25rem;
            box-shadow: 0 5px 18px rgba(16, 42, 67, 0.06);
        }
        button[data-baseweb="tab"] {
            min-height: 3.2rem;
            padding: 0 1.25rem;
            border-radius: 10px;
            color: #334e68;
            font-size: 0.98rem;
            font-weight: 650;
        }
        button[data-baseweb="tab"]:hover {
            background: #e6f6f3;
            color: #0b6f64;
        }
        button[data-baseweb="tab"][aria-selected="true"] {
            background: #102a43;
            color: white;
        }
        .question-card {
            min-height: 180px;
            padding: 1.15rem 1.2rem;
            border: 1px solid #dce6eb;
            border-radius: 14px;
            background: white;
            box-shadow: 0 5px 18px rgba(16, 42, 67, 0.05);
        }
        .question-card-label {
            color: #0e9f8b;
            font-size: 0.74rem;
            font-weight: 750;
            letter-spacing: 0.1em;
            text-transform: uppercase;
        }
        .question-card h4 {
            color: #102a43 !important;
            font-size: 1.08rem;
            margin: 0.45rem 0;
        }
        .question-card p {
            color: #52657a !important;
            line-height: 1.5;
            margin: 0;
        }
        @media (max-width: 800px) {
            button[data-baseweb="tab"] {
                padding: 0 0.75rem;
                font-size: 0.88rem;
            }
        }
    </style>
    """,
    unsafe_allow_html=True,
)


def database_connection():
    """Open the analysis database in read-only mode."""

    database_uri = f"{DATABASE_PATH.as_uri()}?mode=ro"
    return sqlite3.connect(database_uri, uri=True)


def validate_database():
    """Confirm that the pipeline-created database is ready."""

    if not DATABASE_PATH.exists():
        st.error(
            "The analysis database was not found. Run `make pipeline` "
            "before starting the dashboard."
        )
        st.stop()

    with database_connection() as connection:
        available_tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }

    missing_tables = REQUIRED_TABLES - available_tables

    if missing_tables:
        missing_list = ", ".join(sorted(missing_tables))
        st.error(
            "The database is incomplete. Run `make pipeline` again. "
            f"Missing tables: {missing_list}."
        )
        st.stop()


@st.cache_data(show_spinner=False)
def read_query(query, database_modified_time):
    """Read a SQL query and refresh the cache when the database changes."""

    del database_modified_time

    with database_connection() as connection:
        return pd.read_sql_query(query, connection)


def load_data():
    """Load the dashboard tables from SQLite."""

    database_modified_time = DATABASE_PATH.stat().st_mtime_ns

    frequency_data = read_query(
        """
        SELECT sample, total_count, population, count, percentage
        FROM cell_frequencies
        ORDER BY sample, population
        """,
        database_modified_time,
    )

    subject_frequency_data = read_query(
        """
        SELECT subject_id, response, population, mean_percentage
        FROM subject_frequencies
        ORDER BY population, response, subject_id
        """,
        database_modified_time,
    )

    statistical_data = read_query(
        """
        SELECT
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
        FROM statistical_results
        ORDER BY population
        """,
        database_modified_time,
    )

    baseline_data = read_query(
        """
        SELECT sample, subject_id, project, response, sex
        FROM baseline_subset
        ORDER BY sample
        """,
        database_modified_time,
    )

    subset_summary = read_query(
        """
        SELECT metric, category, count
        FROM subset_summary
        ORDER BY metric, category
        """,
        database_modified_time,
    )

    part4_results = read_query(
        """
        SELECT metric, sample_count, result_value
        FROM part4_results
        """,
        database_modified_time,
    )

    overview = read_query(
        """
        SELECT
            (SELECT COUNT(*) FROM subjects) AS subjects,
            (SELECT COUNT(*) FROM samples) AS samples,
            (SELECT COUNT(DISTINCT project) FROM subjects) AS projects,
            (SELECT COUNT(DISTINCT population) FROM cell_counts) AS populations
        """,
        database_modified_time,
    )

    return {
        "frequency": frequency_data,
        "subject_frequency": subject_frequency_data,
        "statistics": statistical_data,
        "baseline": baseline_data,
        "subset_summary": subset_summary,
        "part4_results": part4_results,
        "overview": overview.iloc[0],
    }


def render_overview(data):
    """Render the dashboard overview."""

    st.subheader("Overview")
    st.write(
        "The dashboard uses one dedicated tab for each analysis question. "
        "Select Part 2, Part 3, or Part 4 above to explore the full result."
    )

    st.markdown("### Trial data at a glance")

    columns = st.columns(4)
    columns[0].metric("Subjects", f"{int(data['overview']['subjects']):,}")
    columns[1].metric("Samples", f"{int(data['overview']['samples']):,}")
    columns[2].metric("Projects", f"{int(data['overview']['projects']):,}")
    columns[3].metric(
        "Cell populations",
        f"{int(data['overview']['populations']):,}",
    )

    st.markdown("### Three questions, three analysis tabs")

    question_columns = st.columns(3)

    with question_columns[0]:
        st.markdown(
            """
            <div class="question-card">
                <div class="question-card-label">Part 2</div>
                <h4>Cell composition by sample</h4>
                <p>Review the total count and relative frequency of every
                immune-cell population in every sample.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with question_columns[1]:
        st.markdown(
            """
            <div class="question-card">
                <div class="question-card-label">Part 3</div>
                <h4>Responders versus non-responders</h4>
                <p>Compare PBMC population frequencies for melanoma patients
                receiving miraclib and review the statistical evidence.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with question_columns[2]:
        st.markdown(
            """
            <div class="question-card">
                <div class="question-card-label">Part 4</div>
                <h4>Baseline subset analysis</h4>
                <p>Explore baseline melanoma PBMC samples by project,
                response, and sex, plus the requested B-cell average.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("### Headline finding")
    st.info(
        "At the conventional 5% FDR cutoff, no immune-cell population has "
        "a statistically significant responder/non-responder difference."
    )
    st.warning(
        "At an exploratory 10% FDR cutoff, CD4 T-cell frequency can be "
        "considered a suggestive result (raw p = 0.012; adjusted p = 0.062). "
        "It should not be treated as confirmatory evidence without "
        "independent validation."
    )


def render_part2(data):
    """Render the Part 2 frequency table."""

    frequency_data = data["frequency"].copy()

    st.subheader("Part 2 · Relative frequency by sample")
    st.write(
        "Each row represents one immune-cell population from one sample. "
        "The five percentages for a sample sum to 100%."
    )

    metric_columns = st.columns(3)
    metric_columns[0].metric(
        "Samples",
        f"{frequency_data['sample'].nunique():,}",
    )
    metric_columns[1].metric(
        "Frequency rows",
        f"{len(frequency_data):,}",
    )
    metric_columns[2].metric(
        "Populations per sample",
        f"{frequency_data['population'].nunique():,}",
    )

    filter_columns = st.columns([1.15, 2])

    with filter_columns[0]:
        sample_search = st.text_input(
            "Find a sample",
            placeholder="For example: sample00000",
        )

    with filter_columns[1]:
        population_options = sorted(frequency_data["population"].unique())
        selected_populations = st.multiselect(
            "Cell populations",
            options=population_options,
            default=population_options,
            format_func=lambda value: POPULATION_LABELS[value],
        )

    filtered_data = frequency_data[
        frequency_data["population"].isin(selected_populations)
    ]

    if sample_search.strip():
        filtered_data = filtered_data[
            filtered_data["sample"].str.contains(
                sample_search.strip(),
                case=False,
                regex=False,
            )
        ]

    st.caption(f"Showing {len(filtered_data):,} rows")
    st.dataframe(
        filtered_data,
        hide_index=True,
        width="stretch",
        height=520,
        column_config={
            "sample": "Sample",
            "total_count": st.column_config.NumberColumn(
                "Total count",
                format="%d",
            ),
            "population": "Population",
            "count": st.column_config.NumberColumn("Count", format="%d"),
            "percentage": st.column_config.NumberColumn(
                "Percentage",
                format="%.2f%%",
            ),
        },
    )

    st.download_button(
        "Download filtered table as CSV",
        data=filtered_data.to_csv(index=False).encode("utf-8"),
        file_name="cell_population_frequencies.csv",
        mime="text/csv",
    )


def render_part3(data):
    """Render the Part 3 responder comparison."""

    subject_frequency_data = data["subject_frequency"].copy()
    statistical_data = data["statistics"].copy()

    subject_frequency_data["Response"] = subject_frequency_data[
        "response"
    ].map(RESPONSE_LABELS)
    subject_frequency_data["Population"] = subject_frequency_data[
        "population"
    ].map(POPULATION_LABELS)

    st.subheader("Part 3 · Responders versus non-responders")
    st.write(
        "This analysis includes melanoma patients receiving miraclib and "
        "uses PBMC samples only. Each plotted value is one subject's mean "
        "relative frequency across days 0, 7, and 14."
    )

    metric_columns = st.columns(3)
    metric_columns[0].metric("Responders", "331")
    metric_columns[1].metric("Non-responders", "325")
    metric_columns[2].metric("Statistical tests", "5")

    boxplot = px.box(
        subject_frequency_data,
        x="Response",
        y="mean_percentage",
        color="Response",
        facet_col="Population",
        facet_col_wrap=3,
        points="outliers",
        category_orders={
            "Response": ["Non-responder", "Responder"],
            "Population": POPULATION_ORDER,
        },
        color_discrete_map=RESPONSE_COLORS,
        labels={"mean_percentage": "Mean relative frequency (%)"},
    )
    boxplot.for_each_annotation(
        lambda annotation: annotation.update(
            text=annotation.text.split("=")[-1]
        )
    )
    boxplot.update_layout(
        height=720,
        margin=dict(l=30, r=20, t=55, b=30),
        legend_title_text="Response",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="white",
    )
    boxplot.update_yaxes(title_text="Relative frequency (%)")
    boxplot.update_xaxes(title_text="")

    st.plotly_chart(boxplot, theme=None)

    st.info(
        "Primary conclusion (5% FDR): no cell population has a "
        "statistically significant responder/non-responder difference."
    )
    st.warning(
        "Exploratory conclusion (10% FDR): CD4 T-cell frequency is a "
        "suggestive association (raw p = 0.012; adjusted p = 0.062). "
        "This finding requires independent validation."
    )

    statistical_display = statistical_data.copy()
    statistical_display["population"] = statistical_display["population"].map(
        POPULATION_LABELS
    )
    statistical_display["significant"] = statistical_display[
        "significant"
    ].map({0: "No", 1: "Yes"})
    statistical_display["exploratory_10_percent"] = statistical_data[
        "adjusted_p_value"
    ].apply(lambda value: "Yes" if value < 0.10 else "No")

    statistical_display = statistical_display.rename(
        columns={
            "population": "Population",
            "responders": "Responder n",
            "non_responders": "Non-responder n",
            "responder_median": "Responder median (%)",
            "non_responder_median": "Non-responder median (%)",
            "median_difference": "Median difference",
            "u_statistic": "Mann–Whitney U",
            "p_value": "Raw p-value",
            "adjusted_p_value": "Adjusted p-value",
            "rank_biserial": "Rank-biserial effect",
            "significant": "Significant at 5% FDR",
            "exploratory_10_percent": "Below 10% FDR",
        }
    )

    st.markdown("#### Statistical results")
    st.dataframe(
        statistical_display,
        hide_index=True,
        width="stretch",
        column_config={
            "Responder median (%)": st.column_config.NumberColumn(
                format="%.2f"
            ),
            "Non-responder median (%)": st.column_config.NumberColumn(
                format="%.2f"
            ),
            "Median difference": st.column_config.NumberColumn(
                format="%.2f"
            ),
            "Mann–Whitney U": st.column_config.NumberColumn(format="%.1f"),
            "Raw p-value": st.column_config.NumberColumn(format="%.3e"),
            "Adjusted p-value": st.column_config.NumberColumn(format="%.3e"),
            "Rank-biserial effect": st.column_config.NumberColumn(
                format="%.3f"
            ),
        },
    )

    st.caption(
        "Two-sided Mann–Whitney U tests compare one mean value per subject. "
        "P-values are adjusted across five populations with the "
        "Benjamini–Hochberg procedure."
    )


def summary_chart(summary_data, title, color):
    """Create a compact Part 4 summary chart."""

    chart = px.bar(
        summary_data,
        x="category",
        y="count",
        text="count",
        labels={"category": "", "count": "Count"},
        title=title,
    )
    chart.update_traces(marker_color=color, textposition="outside")
    chart.update_layout(
        height=330,
        margin=dict(l=20, r=15, t=55, b=20),
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="white",
    )
    chart.update_yaxes(rangemode="tozero")
    return chart


def render_part4(data):
    """Render the Part 4 subset analysis."""

    baseline_data = data["baseline"].copy()
    subset_summary = data["subset_summary"].copy()
    part4_result = data["part4_results"].iloc[0]

    st.subheader("Part 4 · Baseline subset analysis")
    st.write(
        "The baseline subset contains melanoma PBMC samples collected at "
        "day 0 from patients treated with miraclib."
    )

    metric_columns = st.columns(4)
    metric_columns[0].metric("Baseline samples", f"{len(baseline_data):,}")
    metric_columns[1].metric(
        "Projects represented",
        f"{baseline_data['project'].nunique():,}",
    )
    metric_columns[2].metric(
        "Responders",
        f"{baseline_data.loc[baseline_data['response'] == 'yes', 'subject_id'].nunique():,}",
    )
    metric_columns[3].metric(
        "Non-responders",
        f"{baseline_data.loc[baseline_data['response'] == 'no', 'subject_id'].nunique():,}",
    )

    project_summary = subset_summary[
        subset_summary["metric"] == "samples_by_project"
    ]
    response_summary = subset_summary[
        subset_summary["metric"] == "subjects_by_response"
    ].copy()
    response_summary["category"] = response_summary["category"].map(
        RESPONSE_LABELS
    )
    sex_summary = subset_summary[
        subset_summary["metric"] == "subjects_by_sex"
    ].copy()
    sex_summary["category"] = sex_summary["category"].map(
        {"F": "Female", "M": "Male"}
    )

    chart_columns = st.columns(3)
    with chart_columns[0]:
        st.plotly_chart(
            summary_chart(project_summary, "Samples by project", "#1f6f8b"),
            theme=None,
        )
    with chart_columns[1]:
        st.plotly_chart(
            summary_chart(response_summary, "Subjects by response", "#0e9f8b"),
            theme=None,
        )
    with chart_columns[2]:
        st.plotly_chart(
            summary_chart(sex_summary, "Subjects by sex", "#7668b3"),
            theme=None,
        )

    st.markdown("#### Baseline samples")
    project_options = sorted(baseline_data["project"].unique())
    selected_projects = st.multiselect(
        "Filter baseline table by project",
        options=project_options,
        default=project_options,
    )
    filtered_baseline = baseline_data[
        baseline_data["project"].isin(selected_projects)
    ]
    st.dataframe(
        filtered_baseline,
        hide_index=True,
        width="stretch",
        height=350,
        column_config={
            "sample": "Sample",
            "subject_id": "Subject",
            "project": "Project",
            "response": "Response",
            "sex": "Sex",
        },
    )

    st.markdown("#### Additional B-cell question")
    b_cell_columns = st.columns([1, 1, 2])
    b_cell_columns[0].metric(
        "Average B-cell count",
        f"{part4_result['result_value']:.2f}",
    )
    b_cell_columns[1].metric(
        "Samples included",
        f"{int(part4_result['sample_count']):,}",
    )
    b_cell_columns[2].write(
        "This calculation includes melanoma male responders at time 0 "
        "across all sample and treatment types, as required by the brief."
    )

    st.caption(
        "Quintazide is mentioned in the assignment brief, but it is not a "
        "treatment value in the supplied dataset and is not used as a filter."
    )


def main():
    """Render the interactive dashboard."""

    validate_database()
    data = load_data()

    st.markdown(
        """
        <div class="hero">
            <div class="hero-kicker">Loblaw Bio · Clinical Trial Analytics</div>
            <h1>Immune Response Explorer</h1>
            <p>
                Explore immune-cell composition, compare miraclib response
                groups, and inspect the trial's baseline melanoma cohort.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    overview_tab, part2_tab, part3_tab, part4_tab = st.tabs(
        [
            "Overview",
            "Part 2 — Frequencies",
            "Part 3 — Response Analysis",
            "Part 4 — Baseline Subset",
        ]
    )

    with overview_tab:
        render_overview(data)

    with part2_tab:
        render_part2(data)

    with part3_tab:
        render_part3(data)

    with part4_tab:
        render_part4(data)


if __name__ == "__main__":
    main()
