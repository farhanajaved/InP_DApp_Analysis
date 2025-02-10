import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

from scipy.stats import kruskal
import scikit_posthocs as sp
from matplotlib.backends.backend_pdf import PdfPages
from cliffs_delta import cliffs_delta  # pip install cliffs_delta (if not installed)


###############################################################################
# 1. Data Loading / Merging
###############################################################################
def process_service_data(data_files, block_files, use_transaction_hash=False):
    """
    Processes latency and block metric data, merging them by transaction hash.
    """
    latency_data_list = []
    for file_info in data_files:
        file_path = file_info['path']
        latency_column = file_info['latency_column']
        if os.path.exists(file_path):
            df = pd.read_csv(file_path)
            if latency_column in df.columns:
                df.rename(columns={latency_column: 'Latency (s)'}, inplace=True)
                if use_transaction_hash:
                    # Keep both Latency + TX Hash
                    latency_data_list.append(df[['Latency (s)', 'Transaction Hash']])
                else:
                    # Keep just Latency
                    latency_data_list.append(df[['Latency (s)']])
        else:
            print(f"[WARNING] File not found: {file_path}")

    all_latency_data = pd.concat(latency_data_list, ignore_index=True) if latency_data_list else pd.DataFrame()

    gas_data_list = []
    for fpath in block_files:
        if os.path.exists(fpath):
            block_df = pd.read_csv(fpath, usecols=['Gas Price (Gwei)', 'Block Size (bytes)',
                                                   'Transaction Count', 'Transaction Hash'])
            block_df['Block Size (KB)'] = block_df['Block Size (bytes)'] / 1024.0
            gas_data_list.append(block_df[['Gas Price (Gwei)', 'Block Size (KB)',
                                           'Transaction Count', 'Transaction Hash']])
        else:
            print(f"[WARNING] File not found: {fpath}")

    all_gas_data = pd.concat(gas_data_list, ignore_index=True) if gas_data_list else pd.DataFrame()

    if not all_latency_data.empty and not all_gas_data.empty:
        merged_data = pd.merge(all_gas_data, all_latency_data,
                               on='Transaction Hash', how='inner').dropna()
        return merged_data
    else:
        return pd.DataFrame()


###############################################################################
# 2. Kruskal-Wallis Test for Each Factor
###############################################################################
def kruskal_test_for_factors(df, factors):
    """
    For each numeric factor in 'factors', we:
      1) Discretize the factor into 5 quintiles
      2) Collect the Latency(s) for each quintile group
      3) Perform a Kruskal-Wallis test
      4) Return a summary DataFrame: Factor, H-statistic, p-value, Interpretation
    """
    results = []
    for factor_col in factors:
        # Create a temporary copy with a new quintile column
        quintile_col = f"{factor_col}_Q"
        df[quintile_col] = pd.qcut(df[factor_col], 5, labels=['Q1','Q2','Q3','Q4','Q5'])

        # Get the list of latency arrays for each quintile
        groups = []
        for _, grp in df.groupby(quintile_col, observed=False):
            groups.append(grp['Latency (s)'].dropna().values)

        # Kruskal-Wallis
        h_stat, p_value = kruskal(*groups)

        # Interpretation
        interpretation = "Significant differences" if p_value < 0.05 else "No significant differences"

        results.append({
            "Factor": factor_col,
            "H-statistic": round(h_stat, 4),
            "p-value": round(p_value, 6),
            "Interpretation": interpretation
        })

    return pd.DataFrame(results)


###############################################################################
# 3. Summary Statistics for Each Factor's Quintiles
###############################################################################
def summary_stats_for_factor(df, factor_col):
    """
    Returns a DataFrame with one row per quintile (Q1..Q5).
    Includes:
      - Quintile label
      - Factor range (min..max) in that quintile
      - Mean latency
      - Median latency
      - Std latency
    """
    quintile_col = f"{factor_col}_Q"
    if quintile_col not in df.columns:
        # If not already discretized, do so
        df[quintile_col] = pd.qcut(df[factor_col], 5, labels=['Q1','Q2','Q3','Q4','Q5'])

    rows = []
    for q_label, grp in df.groupby(quintile_col, observed=False):
        factor_vals = grp[factor_col].dropna()
        lat_vals = grp['Latency (s)'].dropna()

        if factor_vals.empty or lat_vals.empty:
            # If no data in that quintile, skip
            continue

        row = {}
        row["Quintile"] = q_label
        row["Factor Range"] = f"{factor_vals.min():.2f}..{factor_vals.max():.2f}"
        row["Mean Latency"] = round(lat_vals.mean(), 4)
        row["Median Latency"] = round(lat_vals.median(), 4)
        row["Std Latency"] = round(lat_vals.std(), 4)
        rows.append(row)

    return pd.DataFrame(rows)


###############################################################################
# 4. Post-hoc + Cliff's Delta Table (Q1..Q5, all pairs)
###############################################################################
def produce_posthoc_cliffs_table(df, factor_col):
    """
    For the given factor_col (e.g., 'Gas Price (Gwei)'):
      - Already split into Q1..Q5 in df (via qcut).
      - Run Dunn's post-hoc test for all pairs.
      - Compute Cliff's Delta for each pair.
      - Return a DataFrame with multi-level columns:

          Comparison | Is there difference in Latency?
                                 p.value ≤ 0.05   |   Effect size (delta)

      'Yes' in "Is there difference in Latency?" if p < 0.05, else 'No'.
      If p >= 0.05, put "Not significant" in "Effect size (delta)".
    """
    quintile_col = f"{factor_col}_Q"
    if quintile_col not in df.columns:
        df[quintile_col] = pd.qcut(df[factor_col], 5, labels=['Q1','Q2','Q3','Q4','Q5'])

    # Dunn’s test
    groups = [grp['Latency (s)'].dropna() for _, grp in df.groupby(quintile_col, observed=False)]
    posthoc_results = sp.posthoc_dunn(groups, p_adjust='bonferroni')

    # Cliff’s Delta group data
    group_data = df.groupby(quintile_col, observed=False)

    comparison_list   = []
    difference_list   = []
    pvalues_list      = []
    cliffsdelta_list  = []

    quintile_labels = ['Q1','Q2','Q3','Q4','Q5']
    for i, g1 in enumerate(quintile_labels):
        for j, g2 in enumerate(quintile_labels):
            if i < j:
                p_value = posthoc_results.iloc[i, j]
                d, _ = cliffs_delta(
                    group_data.get_group(g1)['Latency (s)'],
                    group_data.get_group(g2)['Latency (s)']
                )
                is_diff = "Yes" if p_value < 0.05 else "No"

                if p_value < 0.05:
                    delta_str = f"{round(d, 2)}"
                else:
                    delta_str = "Not significant"

                comparison_list.append(f"{g1} vs {g2}")
                difference_list.append(is_diff)
                pvalues_list.append(round(p_value, 4))
                cliffsdelta_list.append(delta_str)

    df_pairs = pd.DataFrame({
        "Comparison": comparison_list,
        "is_diff": difference_list,   # "Yes"/"No"
        "p_value": pvalues_list,
        "delta": cliffsdelta_list
    })

    # Build multi-level columns
    df_pairs.rename(columns={
        "Comparison": ("Comparison", ""),
        "is_diff": ("Is there difference in Latency?", ""),
        "p_value": ("Is there difference in Latency?", "p.value ≤ 0.05"),
        "delta": ("Is there difference in Latency?", "Effect size (delta)"),
    }, inplace=True)

    df_pairs.columns = pd.MultiIndex.from_tuples(df_pairs.columns)
    return df_pairs


###############################################################################
# 5. Rendering Tables in Matplotlib
###############################################################################
def draw_table_page(table_df, title, pdf_pages, 
                    header_color="#DDDDDD", 
                    col_widths=None, 
                    font_size=9, 
                    figsize=(14,6)):
    """
    Renders a DataFrame (single or multi-level columns) in a matplotlib figure,
    and saves that page to the provided PdfPages object.
    """
    fig, ax = plt.subplots(figsize=figsize)
    ax.set_title(title, fontsize=12, pad=10)
    ax.axis('off')

    # If we have multi-index columns
    if isinstance(table_df.columns, pd.MultiIndex):
        # Flatten the multi-level columns into 2 (or more) rows of strings
        levels = table_df.columns.nlevels
        # Example: levels = 2 => top_headers, bottom_headers
        # We'll build table_data with 'levels' header rows
        header_rows = []
        for level_idx in range(levels):
            row_labels = [col_tuple[level_idx] for col_tuple in table_df.columns]
            header_rows.append(row_labels)

        # Then the data rows
        data_rows = []
        for row_values in table_df.values:
            row_str_vals = [str(v) for v in row_values]
            data_rows.append(row_str_vals)

        table_data = header_rows + data_rows

        # Color the header rows
        cell_colors = []
        for irow in range(len(table_data)):
            row_colors = []
            for icol in range(len(table_data[0])):
                if irow < levels:
                    row_colors.append(header_color)
                else:
                    row_colors.append("white")
            cell_colors.append(row_colors)

    else:
        # Single-level columns
        # First row is col headers
        header_rows = [list(table_df.columns)]
        data_rows = []
        for row_vals in table_df.values:
            data_rows.append([str(v) for v in row_vals])
        table_data = header_rows + data_rows

        # Color the single header row
        cell_colors = []
        for irow in range(len(table_data)):
            row_colors = []
            for icol in range(len(table_data[0])):
                if irow == 0:
                    row_colors.append(header_color)
                else:
                    row_colors.append("white")
            cell_colors.append(row_colors)

    # Build the table
    table = ax.table(
        cellText=table_data,
        cellColours=cell_colors,
        loc='center',
        cellLoc='left',
        edges='horizontal'
    )
    table.auto_set_font_size(False)
    table.set_fontsize(font_size)

    # Adjust column widths if provided
    if col_widths is not None:
        for col_idx, cw in enumerate(col_widths):
            table.column_cells(col_idx).set_width(cw)
    else:
        table.auto_set_column_width(col=list(range(len(table_data[0]))))

    fig.tight_layout()
    pdf_pages.savefig(fig)
    plt.close(fig)


###############################################################################
# 6. Building the PDF Report
###############################################################################
def build_report(df, pdf_filename="Posthoc_Cliffs_Analysis.pdf"):
    """
    Creates a multi-page PDF with:
      1) Cover page
      2) KW test results table
      3) For each factor with p<0.05:
          a) Summary stats table (for quintiles)
          b) Post-hoc + Cliff’s Delta table
    """
    factor_info = [
        ("Gas Price (Gwei)", "Gas Price"),
        ("Block Size (KB)", "Block Size"),
        ("Transaction Count", "Transaction Count")
    ]

    # 6a) First, compute KW tests for all factors
    kw_df = kruskal_test_for_factors(df, [f[0] for f in factor_info])

    with PdfPages(pdf_filename) as pdf_pages:
        # Intro / cover page
        fig, ax = plt.subplots()
        ax.axis('off')
        ax.text(0.5, 0.8, "Post-hoc Analysis + Cliff's Delta (Q1..Q5 pairs)", 
                ha='center', fontsize=14)
        ax.text(0.5, 0.6, "Includes Kruskal-Wallis test + Summary Stats", 
                ha='center', fontsize=11)
        pdf_pages.savefig(fig)
        plt.close()

        # 6b) Page for KW test summary
        draw_table_page(
            kw_df, 
            title="Kruskal-Wallis Test Results", 
            pdf_pages=pdf_pages,
            figsize=(9, 3)
        )

        # 6c) For each factor that has a p < 0.05, produce:
        #     1) Summary stats table
        #     2) Post-hoc table
        for (factor_col, factor_label) in factor_info:
            # Extract row for this factor from kw_df
            row = kw_df.loc[kw_df['Factor'] == factor_col].iloc[0]
            pval = row['p-value']

            if pval < 0.05:
                # Summary stats table
                summary_df = summary_stats_for_factor(df, factor_col)
                draw_table_page(
                    summary_df, 
                    title=f"{factor_label}: Quintile Summary Stats",
                    pdf_pages=pdf_pages,
                    figsize=(10,4)
                )

                # Post-hoc table
                posthoc_df = produce_posthoc_cliffs_table(df, factor_col)
                draw_table_page(
                    posthoc_df,
                    title=f"{factor_label}: All Pairwise Comparisons (Q1..Q5)",
                    pdf_pages=pdf_pages,
                    figsize=(12,5)
                )

    print(f"[INFO] PDF report saved as: {pdf_filename}")


###############################################################################
# 7. Example Execution (Main) -- Adjust or comment out as needed
###############################################################################
if __name__ == "__main__":
    # 7a) Configuration for AddService
    addservice_data_files = [
        {'path': '/home/fjaved/demos/hardhat-project/test/sepolia/AddService/2x10_AddService.csv', 'latency_column': 'Write Latency (s)'},
        {'path': '/home/fjaved/demos/hardhat-project/test/sepolia/AddService/10x10_AddService.csv', 'latency_column': 'Write Latency (s)'},
        {'path': '/home/fjaved/demos/hardhat-project/test/sepolia/AddService/18x10_AddService.csv', 'latency_column': 'Write Latency (s)'},
        {'path': '/home/fjaved/demos/hardhat-project/test/sepolia/AddService/26x10_AddService.csv', 'latency_column': 'Write Latency (s)'},
        {'path': '/home/fjaved/demos/hardhat-project/test/sepolia/AddService/34x10_AddService.csv', 'latency_column': 'Write Latency (s)'},
        {'path': '/home/fjaved/demos/hardhat-project/test/sepolia/AddService/42x10_AddService.csv', 'latency_column': 'Write Latency (s)'},
        {'path': '/home/fjaved/demos/hardhat-project/test/sepolia/AddService/50x10_AddService.csv', 'latency_column': 'Write Latency (s)'}
    ]
    addservice_block_files = [
        '/home/fjaved/demos/hardhat-project/test/sepolia/AddService/BlockNumber_2x10_AddService.csv',
        '/home/fjaved/demos/hardhat-project/test/sepolia/AddService/BlockNumber_10x10_AddService.csv',
        '/home/fjaved/demos/hardhat-project/test/sepolia/AddService/BlockNumber_18x10_AddService.csv',
        '/home/fjaved/demos/hardhat-project/test/sepolia/AddService/BlockNumber_26x10_AddService.csv',
        '/home/fjaved/demos/hardhat-project/test/sepolia/AddService/BlockNumber_34x10_AddService.csv',
        '/home/fjaved/demos/hardhat-project/test/sepolia/AddService/BlockNumber_42x10_AddService.csv',
        '/home/fjaved/demos/hardhat-project/test/sepolia/AddService/BlockNumber_50x10_AddService.csv'
    ]

    # 7b) Configuration for SelectService
    selectservice_data_files = [
        {'path': '/home/fjaved/demos/hardhat-project/test/sepolia/SelectService/merged_service_selection_log.csv', 'latency_column': 'Transaction Latency (s)'}
    ]
    selectservice_block_files = [
        '/home/fjaved/demos/hardhat-project/test/sepolia/SelectService/selectService_block_number.csv'
    ]

    # Process AddService data
    df_add = process_service_data(
        data_files=addservice_data_files,
        block_files=addservice_block_files,
        use_transaction_hash=True
    )

    # Process SelectService data
    df_sel = process_service_data(
        data_files=selectservice_data_files,
        block_files=selectservice_block_files,
        use_transaction_hash=True
    )

    # Combine both datasets
    combined_data = pd.concat([df_add, df_sel], ignore_index=True)

    if combined_data.empty:
        print("No data found! Exiting.")
    else:
        # Build the final PDF report
        output_pdf = "Blockchain_Latency_Analysis_Report_With_Posthoc.pdf"
        build_report(combined_data, pdf_filename=output_pdf)
        print(f"Report generated: {output_pdf}")
