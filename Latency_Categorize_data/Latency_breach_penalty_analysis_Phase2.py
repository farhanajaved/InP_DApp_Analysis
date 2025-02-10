import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

from scipy.stats import kruskal
import scikit_posthocs as sp
from cliffs_delta import cliffs_delta
from matplotlib.backends.backend_pdf import PdfPages

###############################################################################
# 1. DATA LOADING / MERGING
###############################################################################
def process_service_data(data_files, block_files, index_based=False, use_transaction_hash=False):
    """
    Reads CSV files for latency and block metrics, merges them either by:
      - index_based approach, or
      - transaction hash-based approach (if use_transaction_hash=True).
    Returns a single DataFrame with columns:
      ['Latency (s)', 'Gas Price (Gwei)', 'Block Size (KB)', 'Transaction Count', 'Transaction Hash'(opt)]
    """

    # --- Load Latency Data ---
    latency_data_list = []
    for file_info in data_files:
        file_path = file_info['path']
        latency_column = file_info['latency_column']
        if os.path.exists(file_path):
            try:
                df = pd.read_csv(file_path)

                # If index-based grouping is needed
                if index_based:
                    if 'UserIndex' in df.columns and 'Iteration' in df.columns:
                        df = df.groupby(['Iteration','UserIndex']).first().reset_index()
                    elif 'Iteration' in df.columns:
                        df = df.groupby('Iteration').first().reset_index()
                    else:
                        print(f"[WARNING] Index-based grouping skipped for {file_path}, missing 'Iteration' or 'UserIndex'.")

                elif use_transaction_hash and 'Transaction Hash' in df.columns:
                    df = df.dropna(subset=['Transaction Hash'])
                else:
                    # Might not need grouping if you do not rely on transaction hash or iteration
                    pass

                # Rename your latency column to a consistent name: 'Latency (s)'
                if latency_column in df.columns:
                    df.rename(columns={latency_column: 'Latency (s)'}, inplace=True)

                    # Keep only the relevant columns
                    if index_based:
                        if 'UserIndex' in df.columns and 'Iteration' in df.columns:
                            latency_data_list.append(df[['Latency (s)', 'Iteration','UserIndex']])
                        elif 'Iteration' in df.columns:
                            latency_data_list.append(df[['Latency (s)', 'Iteration']])
                        else:
                            # fallback
                            latency_data_list.append(df[['Latency (s)']])
                    elif use_transaction_hash:
                        if 'Transaction Hash' in df.columns:
                            latency_data_list.append(df[['Latency (s)', 'Transaction Hash']])
                    else:
                        # fallback
                        latency_data_list.append(df[['Latency (s)']])
                else:
                    print(f"[WARNING] Latency column '{latency_column}' not found in {file_path}.")

            except Exception as e:
                print(f"[ERROR] Reading {file_path}: {e}")
        else:
            print(f"[WARNING] File not found: {file_path}")

    all_latency_data = pd.concat(latency_data_list, ignore_index=True) if latency_data_list else pd.DataFrame()

    # --- Load Block/Gas Data ---
    gas_data_list = []
    for block_path in block_files:
        if os.path.exists(block_path):
            try:
                df_block = pd.read_csv(block_path, usecols=['Gas Price (Gwei)','Block Size (bytes)',
                                                            'Transaction Count','Transaction Hash'])
                df_block['Block Size (KB)'] = df_block['Block Size (bytes)'] / 1024.0
                gas_data_list.append(df_block[['Gas Price (Gwei)','Block Size (KB)',
                                               'Transaction Count','Transaction Hash']])
            except Exception as e:
                print(f"[ERROR] Reading gas data from {block_path}: {e}")
        else:
            print(f"[WARNING] File not found: {block_path}")

    all_gas_data = pd.concat(gas_data_list, ignore_index=True) if gas_data_list else pd.DataFrame()

    # --- Merge Data ---
    if not all_latency_data.empty and not all_gas_data.empty:
        if index_based:
            # Combine side by side (assuming same length, same order after grouping)
            merged_df = pd.concat([all_gas_data.reset_index(drop=True),
                                   all_latency_data.reset_index(drop=True)], axis=1).dropna()
            return merged_df
        elif use_transaction_hash:
            merged_df = pd.merge(all_gas_data, all_latency_data, on='Transaction Hash', how='inner').dropna()
            return merged_df
        else:
            # If neither approach is used, we might just return a fallback
            merged_df = pd.concat([all_gas_data, all_latency_data], axis=1).dropna()
            return merged_df
    else:
        print("[WARNING] No data available to merge.")
        return pd.DataFrame()


###############################################################################
# 2. STATS & POST-HOC ANALYSIS (ONE FACTOR AT A TIME)
###############################################################################
def analyze_factor(df, factor_col, factor_label):
    """
    1) Splits 'factor_col' into 5 quintiles: Q1..Q5
    2) Summarizes the latency in each quintile:
       - range of factor in that quintile
       - mean, median, std, count of Latency (s)
    3) Runs Kruskal-Wallis test across the 5 quintiles
    4) If p < 0.05, runs Dunn's post-hoc & Cliff's Delta for each Q1..Q5 pair
    5) Returns:
       - summary_table (df)
       - kw_stat, kw_p
       - posthoc_df (or None if not significant)
    """

    # Create quintile column
    quintile_col = f"{factor_col}_Q"
    df[quintile_col] = pd.qcut(df[factor_col], 5, labels=['Q1','Q2','Q3','Q4','Q5'])

    # Summary stats
    summary_rows = []
    for q_label, grp in df.groupby(quintile_col, observed=False):
        sub_factors = grp[factor_col].dropna()
        sub_lat = grp['Latency (s)'].dropna()

        if len(sub_factors) == 0 or len(sub_lat) == 0:
            continue

        row = {
            "Quintile": q_label,
            "Factor Range": f"{sub_factors.min():.2f}..{sub_factors.max():.2f}",
            "Count": len(sub_lat),
            "Mean Latency": round(sub_lat.mean(), 4),
            "Median Latency": round(sub_lat.median(), 4),
            "StdDev Latency": round(sub_lat.std(), 4)
        }
        summary_rows.append(row)

    summary_df = pd.DataFrame(summary_rows)

    # Kruskal-Wallis
    groups = []
    for _, grp in df.groupby(quintile_col, observed=False):
        groups.append(grp['Latency (s)'].dropna())
    if len(groups) < 5:
        kw_stat, kw_p = (None, None)
        posthoc_df = None
    else:
        kw_stat, kw_p = kruskal(*groups)
        posthoc_df = None

        # If significant, do Dunn's + Cliff's
        if kw_p is not None and kw_p < 0.05:
            # Dunn’s test from scikit_posthocs
            # We must supply a list of arrays or do “posthoc_dunn” with group_col
            # Easiest way: re-group the data
            data_for_posthoc = []
            label_for_posthoc = []
            for q_label, grp in df.groupby(quintile_col, observed=False):
                for val in grp['Latency (s)'].dropna():
                    data_for_posthoc.append(val)
                    label_for_posthoc.append(q_label)

            posthoc_mat = sp.posthoc_dunn(
                pd.DataFrame({"val": data_for_posthoc, "grp": label_for_posthoc}),
                val_col='val', group_col='grp', p_adjust='bonferroni'
            )

            # Build pairwise table with p-values + Cliff's Delta
            # (Q1..Q5 indices -> 0..4 in posthoc_mat)
            pair_rows = []
            quintiles = ['Q1','Q2','Q3','Q4','Q5']
            for i in range(len(quintiles)):
                for j in range(i+1, len(quintiles)):
                    q_i = quintiles[i]
                    q_j = quintiles[j]
                    pval_ij = posthoc_mat.loc[q_i, q_j]

                    # Cliff's Delta
                    d_val, _ = cliffs_delta(
                        df.loc[df[quintile_col] == q_i, 'Latency (s)'].dropna(),
                        df.loc[df[quintile_col] == q_j, 'Latency (s)'].dropna()
                    )

                    row = {
                        "Comparison": f"{q_i} vs {q_j}",
                        "p-value": round(pval_ij, 5),
                        "Cliff's Delta": round(d_val, 3),
                        "Significant?": ("Yes" if pval_ij < 0.05 else "No")
                    }
                    pair_rows.append(row)

            posthoc_df = pd.DataFrame(pair_rows)
        else:
            posthoc_df = None

    return summary_df, kw_stat, kw_p, posthoc_df


def plot_factor_boxplot(df, factor_col, factor_label, y_limit=200):
    """
    Creates a boxplot of Latency(s) vs. quintiles of 'factor_col',
    with red dots for the mean. Returns a Matplotlib figure object.
    """
    quintile_col = f"{factor_col}_Q"
    if quintile_col not in df.columns:
        df[quintile_col] = pd.qcut(df[factor_col], 5, labels=['Q1','Q2','Q3','Q4','Q5'])

    fig, ax = plt.subplots(figsize=(8,5))
    sns.boxplot(x=quintile_col, y='Latency (s)', data=df, palette='Set2', width=0.4, ax=ax)
    ax.set_title(f"Latency by {factor_label} Quintiles", fontsize=12)
    ax.set_xlabel(f"{factor_label} Quintiles")
    ax.set_ylabel("Latency (s)")
    ax.set_ylim(0, y_limit)

    # Red dot for the mean
    mean_series = df.groupby(quintile_col)['Latency (s)'].mean()
    for i, q_label in enumerate(mean_series.index):
        val = mean_series.loc[q_label]
        ax.scatter(i, val, color='red', zorder=5, s=40)
        ax.text(i, val, f"{val:.2f}", ha='center', va='bottom', fontsize=8, color='black')

    fig.tight_layout()
    return fig


###############################################################################
# 3. BUILD MULTI-PAGE PDF REPORT
###############################################################################
def build_report_one_factor(df, pdf_filename="OneFactor_Latency_Report.pdf"):
    """
    Generates a multi-page PDF analyzing each factor separately (Gas Price, Block Size, Tx Count):
      1) Splits each factor into Q1..Q5,
      2) Summarizes stats,
      3) KW test,
      4) Post-hoc if significant,
      5) Boxplot figure.

    All results go into a PDF with multiple pages.
    """
    factors = [
        ("Gas Price (Gwei)", "Gas Price"),
        ("Block Size (KB)", "Block Size"),
        ("Transaction Count", "Transaction Count")
    ]

    with PdfPages(pdf_filename) as pdf:
        # --- Intro page
        fig_intro, ax_intro = plt.subplots(figsize=(8.5, 11))
        ax_intro.axis('off')
        ax_intro.text(0.5, 0.9, "One-Factor-at-a-Time Latency Analysis Report",
                      ha='center', va='center', fontsize=16)
        intro_text = [
            "This report analyzes Gas Price, Block Size, and Transaction Count separately.",
            "For each factor, we create quintiles (Q1..Q5) and assess Latency (s).",
            "Statistical methods: Kruskal-Wallis, Dunn's post-hoc, Cliff's Delta for effect size.",
        ]
        ystart = 0.7
        for line in intro_text:
            ax_intro.text(0.05, ystart, line, fontsize=12)
            ystart -= 0.05

        pdf.savefig(fig_intro)
        plt.close(fig_intro)

        # --- Analyze each factor separately
        for factor_col, factor_label in factors:
            # 1) Summarize and run KW
            summary_df, kw_stat, kw_p, posthoc_df = analyze_factor(df, factor_col, factor_label)

            # --- Page: Summary Table
            fig_table, ax_table = plt.subplots(figsize=(10,4))
            ax_table.axis('off')
            ax_table.set_title(f"{factor_label} Quintile Summary + Kruskal-Wallis", fontsize=12, pad=10)
            
            # Convert summary_df into table text
            # We'll add a small row for the KW result
            table_data = []
            header = list(summary_df.columns)
            table_data.append(header)
            for row_vals in summary_df.values:
                table_data.append([str(v) for v in row_vals])

            # Show KW test result
            if kw_stat is not None:
                table_data.append(["KW Test", f"H={kw_stat:.2f}", f"p={kw_p:.5f}", "", "", ""])
            else:
                table_data.append(["KW Test", "N/A", "N/A", "", "", ""])

            table = ax_table.table(cellText=table_data, loc='center', cellLoc='left', edges='horizontal')
            table.auto_set_font_size(False)
            table.set_fontsize(10)
            table.auto_set_column_width(col=list(range(len(header))))

            fig_table.tight_layout()
            pdf.savefig(fig_table)
            plt.close(fig_table)

            # If significant -> Page: Post-hoc results
            if kw_p is not None and kw_p < 0.05 and posthoc_df is not None:
                fig_posthoc, ax_ph = plt.subplots(figsize=(10,4))
                ax_ph.axis('off')
                ax_ph.set_title(f"{factor_label} Post-hoc Dunn + Cliff's Delta", fontsize=12)

                # Build table data
                ph_header = list(posthoc_df.columns)
                ph_data = [ph_header]
                for row_vals in posthoc_df.values:
                    ph_data.append([str(v) for v in row_vals])

                ph_table = ax_ph.table(cellText=ph_data, loc='center', cellLoc='left', edges='horizontal')
                ph_table.auto_set_font_size(False)
                ph_table.set_fontsize(9)
                ph_table.auto_set_column_width(col=list(range(len(ph_header))))

                fig_posthoc.tight_layout()
                pdf.savefig(fig_posthoc)
                plt.close(fig_posthoc)

            # --- Page: Boxplot
            fig_bp = plot_factor_boxplot(df, factor_col, factor_label, y_limit=200)
            pdf.savefig(fig_bp)
            plt.close(fig_bp)

    print(f"[INFO] One-factor analysis PDF saved as {pdf_filename}")


###############################################################################
# 4. MAIN EXECUTION (EXAMPLE)
###############################################################################
if __name__ == "__main__":
    # 4a) Example: You define your data & block files for index-based approach
    #    (Adjust file paths as needed)
    hybridpenalty_data_files = [
        {'path': '/home/fjaved/demos/hardhat-project/HybridPenaltyData/Final_dataset/penaltyData_2x10.csv', 'latency_column': 'Latency(s)'},
        {'path': '/home/fjaved/demos/hardhat-project/HybridPenaltyData/Final_dataset/penaltyData_10x10.csv', 'latency_column': 'Latency(s)'},
        {'path': '/home/fjaved/demos/hardhat-project/HybridPenaltyData/Final_dataset/penaltyData_18x10.csv', 'latency_column': 'Latency(s)'},
        {'path': '/home/fjaved/demos/hardhat-project/HybridPenaltyData/Final_dataset/penaltyData_26x10.csv', 'latency_column': 'Latency(s)'},
        {'path': '/home/fjaved/demos/hardhat-project/HybridPenaltyData/Final_dataset/penaltyData_34x5(final).csv', 'latency_column': 'Latency(s)'},
        {'path': '/home/fjaved/demos/hardhat-project/HybridPenaltyData/Final_dataset/penaltyData_42x1(final).csv', 'latency_column': 'Latency(s)'},
        {'path': '/home/fjaved/demos/hardhat-project/HybridPenaltyData/Final_dataset/penaltyData_50x10.csv', 'latency_column': 'Latency(s)'}
    ]
    hybridpenalty_block_files = [
        '/home/fjaved/demos/hardhat-project/test/sepolia/HybridPenalty/BlockDetail_calculatePenalty_2x10.csv',
        '/home/fjaved/demos/hardhat-project/test/sepolia/HybridPenalty/BlockDetail_calculatePenalty_10x10.csv',
        '/home/fjaved/demos/hardhat-project/test/sepolia/HybridPenalty/BlockDetail_calculatePenalty_18x10.csv',
        '/home/fjaved/demos/hardhat-project/test/sepolia/HybridPenalty/BlockDetail_calculatePenalty_26x10.csv',
        '/home/fjaved/demos/hardhat-project/test/sepolia/HybridPenalty/BlockDetail_calculatePenalty_34x10.csv',
        '/home/fjaved/demos/hardhat-project/test/sepolia/HybridPenalty/BlockDetail_calculatePenalty_42x10.csv',
        '/home/fjaved/demos/hardhat-project/test/sepolia/HybridPenalty/BlockDetail_calculatePenalty_50x10.csv'
    ]

    # 4b) Breach Data
    breachdata_data_files = [
        {'path': '/home/fjaved/demos/hardhat-project/HybridPenaltyData/Final_dataset/breachData_2x10.csv', 'latency_column': 'Latency'},
        {'path': '/home/fjaved/demos/hardhat-project/HybridPenaltyData/Final_dataset/breachData_10x10.csv', 'latency_column': 'Latency'},
        {'path': '/home/fjaved/demos/hardhat-project/HybridPenaltyData/Final_dataset/breachData_18x10.csv', 'latency_column': 'Latency'},
        {'path': '/home/fjaved/demos/hardhat-project/HybridPenaltyData/Final_dataset/breachData_26x10.csv', 'latency_column': 'Latency'},
        {'path': '/home/fjaved/demos/hardhat-project/HybridPenaltyData/Final_dataset/breachData_34x5_final.csv', 'latency_column': 'Latency'},
        {'path': '/home/fjaved/demos/hardhat-project/HybridPenaltyData/Final_dataset/breachData_42x2_final.csv', 'latency_column': 'Latency'},
        {'path': '/home/fjaved/demos/hardhat-project/HybridPenaltyData/Final_dataset/breachData_50x10.csv', 'latency_column': 'Latency'}
    ]
    breachdata_block_files = [
        '/home/fjaved/demos/hardhat-project/test/sepolia/HybridPenalty/BlockDetail_registerBreach_2x10.csv',
        '/home/fjaved/demos/hardhat-project/test/sepolia/HybridPenalty/BlockDetail_registerBreach_10x10.csv',
        '/home/fjaved/demos/hardhat-project/test/sepolia/HybridPenalty/BlockDetail_registerBreach_18x10.csv',
        '/home/fjaved/demos/hardhat-project/test/sepolia/HybridPenalty/BlockDetail_registerBreach_26x10.csv',
        '/home/fjaved/demos/hardhat-project/test/sepolia/HybridPenalty/BlockDetail_registerBreach_34x10.csv',
        '/home/fjaved/demos/hardhat-project/test/sepolia/HybridPenalty/BlockDetail_registerBreach_42x10.csv',
        '/home/fjaved/demos/hardhat-project/test/sepolia/HybridPenalty/BlockDetail_registerBreach_50x10.csv'
    ]

    # 4c) Merge data
    df_hybridpenalty = process_service_data(hybridpenalty_data_files, hybridpenalty_block_files, index_based=True)
    df_breachdata    = process_service_data(breachdata_data_files,  breachdata_block_files,  index_based=True)

    # Combine both sets if you like
    combined_data = pd.concat([df_hybridpenalty, df_breachdata], ignore_index=True)

    if combined_data.empty:
        print("[WARNING] No data to analyze. Exiting.")
    else:
        # Convert Transaction Count to int if needed
        combined_data['Transaction Count'] = combined_data['Transaction Count'].astype(int, errors='ignore')

        # 4d) Build the PDF report
        pdf_report_name = "OneFactor_Analysis_Report.pdf"
        build_report_one_factor(combined_data, pdf_filename=pdf_report_name)
        print(f"[INFO] Report generated: {pdf_report_name}")
