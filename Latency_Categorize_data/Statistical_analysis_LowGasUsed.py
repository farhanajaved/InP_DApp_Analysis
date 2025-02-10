import pandas as pd
import numpy as np
from scipy.stats import kruskal
import scikit_posthocs as sp
import os
import matplotlib.pyplot as plt
import seaborn as sns
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet

def cliffs_delta(lst1, lst2):
    """Calculate Cliff's Delta."""
    n1 = len(lst1)
    n2 = len(lst2)
    all_pairs = [(x1, x2) for x1 in lst1 for x2 in lst2]
    n_concordant = sum(1 for x1, x2 in all_pairs if x1 > x2)
    n_discordant = sum(1 for x1, x2 in all_pairs if x1 < x2)
    delta = (n_concordant - n_discordant) / (n1 * n2)
    return delta

def process_service_data(data_files, block_files, index_based=False, use_transaction_hash=False):
    """Processes latency and block data from specified files."""
    latency_data_list = []
    for file_info in data_files:
        file_path = file_info['path']
        latency_column = file_info['latency_column']
        if os.path.exists(file_path):
            try:
                df = pd.read_csv(file_path)

                # Handle index-based or transaction hash-based data
                if index_based:
                    if 'UserIndex' in df.columns and 'Iteration' in df.columns:
                        df = df.groupby(['Iteration', 'UserIndex']).first().reset_index()
                    elif 'Iteration' in df.columns:
                        df = df.groupby(['Iteration']).first().reset_index()
                    else:
                        print(f"Skipping grouping for {file_path} as 'Iteration' or 'UserIndex' is missing")
                elif use_transaction_hash and 'Transaction Hash' in df.columns:
                    df = df.dropna(subset=['Transaction Hash'])
                else:
                    print(f"Skipping grouping for {file_path} as relevant columns are missing")

                if latency_column in df.columns:
                    df.rename(columns={latency_column: 'Latency (s)'}, inplace=True)
                    if index_based:
                        if 'UserIndex' in df.columns:
                            latency_data_list.append(df[['Latency (s)', 'Iteration', 'UserIndex']])
                        else:
                            latency_data_list.append(df[['Latency (s)', 'Iteration']])
                    elif use_transaction_hash:
                        latency_data_list.append(df[['Latency (s)', 'Transaction Hash']])
                else:
                    print(f"Latency column '{latency_column}' not found in {file_path}")
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
        else:
            print(f"File not found: {file_path}")

    all_latency_data = pd.concat(latency_data_list, ignore_index=True) if latency_data_list else pd.DataFrame()

    # Process Gas Price, Block Size, and Transaction Count Data
    gas_data_list = []
    for file_path in block_files:
        if os.path.exists(file_path):
            try:
                data = pd.read_csv(file_path, usecols=['Gas Price (Gwei)', 'Block Size (bytes)', 'Transaction Count', 'Transaction Hash'])
                data['Block Size (KB)'] = data['Block Size (bytes)'] / 1024
                gas_data_list.append(data[['Gas Price (Gwei)', 'Block Size (KB)', 'Transaction Count', 'Transaction Hash']])
            except Exception as e:
                print(f"Error reading gas data from {file_path}: {e}")
        else:
            print(f"File not found: {file_path}")

    all_gas_data = pd.concat(gas_data_list, ignore_index=True) if gas_data_list else pd.DataFrame()

    # Merge Latency and Gas Data
    if not all_latency_data.empty and not all_gas_data.empty:
        if index_based:
            merged_data = pd.concat([all_gas_data.reset_index(drop=True), all_latency_data.reset_index(drop=True)], axis=1).dropna()
        elif use_transaction_hash:
            merged_data = pd.merge(all_gas_data, all_latency_data, how='inner', on='Transaction Hash').dropna()
        else:
            merged_data = pd.DataFrame()
        return merged_data
    else:
        print(f"No data available for some files.")
        return pd.DataFrame()

def perform_statistical_analysis(combined_data, file_path):
    """Performs statistical analysis and writes the results to a PDF file."""
    doc = SimpleDocTemplate(file_path, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    # Title
    title = Paragraph("Statistical Analysis Report", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 12))

    intro_text = """
    This report investigates the relationship between various blockchain features and transaction latency. We analyzed three key features:
    <br/><br/>
    - <b>Gas Price (Gwei)</b><br/>
    - <b>Block Size (KB)</b><br/>
    - <b>Transaction Count</b><br/><br/>
    For each feature, data is divided into quintiles (Q1 to Q5) to categorize and compare transaction latencies.
    """
    elements.append(Paragraph(intro_text, styles['Normal']))
    elements.append(Spacer(1, 12))

    # Kruskal-Wallis H-test Results
    elements.append(Paragraph("1. Kruskal-Wallis H-test Results", styles['Heading2']))
    elements.append(Spacer(1, 12))

    kw_table_data = [['Feature', 'H-statistic', 'p-value', 'Interpretation']]
    kw_table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#d3d3d3')),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ])

    features = ['Gas Price (Gwei)', 'Block Size (KB)', 'Transaction Count']
    for feature in features:
        combined_data[f'{feature} Quintile'] = pd.qcut(combined_data[feature], 5, labels=['Q1', 'Q2', 'Q3', 'Q4', 'Q5'])
        result = kruskal(*[group['Latency (s)'].values for name, group in combined_data.groupby(f'{feature} Quintile')])
        interpretation = "Significant differences among quintiles" if result.pvalue < 0.05 else "No significant differences among quintiles"
        kw_table_data.append([feature, f"{result.statistic:.2f}", f"{result.pvalue:.4f}", interpretation])

    kw_table = Table(kw_table_data, colWidths=[150, 80, 80, 200])
    kw_table.setStyle(kw_table_style)
    elements.append(kw_table)
    elements.append(Spacer(1, 12))

    # Interpretation
    elements.append(Paragraph("<b>Interpretation:</b>", styles['Normal']))
    interpretations = []
    for feature in features:
        result = kruskal(*[group['Latency (s)'].values for name, group in combined_data.groupby(f'{feature} Quintile')])
        if result.pvalue < 0.05:
            interpretations.append(f"- <b>{feature}</b> shows significant differences in transaction latency across quintiles.")
        else:
            interpretations.append(f"- <b>{feature}</b> does not show significant differences among quintiles.")
    elements.append(Paragraph("<br/>".join(interpretations), styles['Normal']))
    elements.append(Spacer(1, 12))

    # For each feature
    for feature in features:
        elements.append(PageBreak())
        elements.append(Paragraph(f"2. Analysis for {feature}", styles['Heading2']))
        elements.append(Spacer(1, 12))

        combined_data[f'{feature} Quintile'] = pd.qcut(combined_data[feature], 5, labels=['Q1', 'Q2', 'Q3', 'Q4', 'Q5'])

        # Summary Statistics
        elements.append(Paragraph("Summary Statistics:", styles['Heading3']))
        quintile_stats = combined_data.groupby(f'{feature} Quintile')['Latency (s)'].agg(['count', 'mean', 'median', 'std']).reset_index()
        quintile_stats.columns = ['Quintile', 'Count', 'Mean Latency (s)', 'Median Latency (s)', 'Std Dev (s)']
        data = [quintile_stats.columns.tolist()] + quintile_stats.values.tolist()
        table = Table(data, colWidths=[80, 60, 100, 100, 80])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#d3d3d3')),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 12))

        # Kruskal-Wallis Test
        result = kruskal(*[group['Latency (s)'].values for name, group in combined_data.groupby(f'{feature} Quintile')])
        elements.append(Paragraph("Kruskal-Wallis H-test:", styles['Heading3']))
        kw_text = f"""
        The Kruskal-Wallis H-test is a non-parametric method used to determine if there are statistically significant differences between two or more groups of an independent variable on a continuous or ordinal dependent variable.<br/><br/>
        <b>Test Results:</b><br/>
        - H-statistic: {result.statistic:.2f}<br/>
        - p-value: {result.pvalue:.4f}
        """
        elements.append(Paragraph(kw_text, styles['Normal']))
        elements.append(Spacer(1, 12))

        if result.pvalue < 0.05:
            elements.append(Paragraph("Interpretation:", styles['Heading3']))
            elements.append(Paragraph(
                "Since the p-value is less than 0.05, we reject the null hypothesis and conclude that there are significant differences among the quintiles.", styles['Normal']))
            elements.append(Spacer(1, 12))

            # Post-hoc Dunn's Test
            elements.append(Paragraph("Post-hoc Analysis (Dunn's Test):", styles['Heading3']))
            posthoc = sp.posthoc_dunn(combined_data, val_col='Latency (s)', group_col=f'{feature} Quintile')

            comparisons = []
            for i in range(len(posthoc.columns)):
                for j in range(i + 1, len(posthoc.columns)):
                    p_val = posthoc.iloc[i, j]
                    comp = f"{posthoc.index[i]} vs {posthoc.index[j]}"
                    if p_val < 0.05:
                        delta = cliffs_delta(
                            combined_data[combined_data[f'{feature} Quintile'] == posthoc.index[i]]['Latency (s)'],
                            combined_data[combined_data[f'{feature} Quintile'] == posthoc.index[j]]['Latency (s)']
                        )
                        comparisons.append([comp, f"{p_val:.4f}", f"{delta:.2f}"])
                    else:
                        comparisons.append([comp, f"{p_val:.4f}", "Not significant"])

            data = [["Comparison", "p-value", "Cliff's Delta"]] + comparisons
            table = Table(data, colWidths=[150, 80, 100])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#d3d3d3')),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elements.append(table)
            elements.append(Spacer(1, 12))

            # Interpretation
            elements.append(Paragraph("Notes:", styles['Heading3']))
            interpret_text = """
            - <b>Significant p-values</b> indicate a significant difference between the groups.<br/>
            - <b>Cliff's Delta</b> measures the effect size:<br/>
                &nbsp;&nbsp;- Values range from -1 to 1.<br/>
                &nbsp;&nbsp;- Negative values indicate the first group has lower latencies.<br/>
                &nbsp;&nbsp;- Positive values indicate the first group has higher latencies.
            """
            elements.append(Paragraph(interpret_text, styles['Normal']))
            elements.append(Spacer(1, 12))

            # Specific Interpretation (You can customize this based on your data)
            elements.append(Paragraph("Interpretation:", styles['Heading3']))
            elements.append(Paragraph(
                f"Significant differences were observed in latency across different quintiles of {feature}.", styles['Normal']))
            elements.append(Spacer(1, 12))

        else:
            elements.append(Paragraph("Interpretation:", styles['Heading3']))
            elements.append(Paragraph(
                "Since the p-value is greater than 0.05, we fail to reject the null hypothesis and conclude that there are no significant differences among the quintiles.", styles['Normal']))
            elements.append(Spacer(1, 12))

    # Final Thoughts
    elements.append(PageBreak())
    elements.append(Paragraph("3. Overall Interpretation and Conclusions", styles['Heading2']))
    elements.append(Spacer(1, 12))
    conclusions = """
    This analysis provides insights into how gas prices, block sizes, and transaction counts affect transaction latency in blockchain networks. By understanding these relationships, stakeholders can make informed decisions to optimize performance and user experience.
    """
    elements.append(Paragraph(conclusions, styles['Normal']))
    elements.append(Spacer(1, 12))

    # Recommendations
    elements.append(Paragraph("4. Recommendations", styles['Heading2']))
    elements.append(Spacer(1, 12))
    recommendations = """
    <b>For Users:</b><br/>
    - Consider adjusting gas prices based on desired latency outcomes.<br/><br/>
    <b>For Network Operators:</b><br/>
    - Monitor and manage transaction counts and block sizes to maintain optimal network performance.<br/><br/>
    <b>For Developers:</b><br/>
    - Explore optimizations that can mitigate latency issues related to network parameters.
    """
    elements.append(Paragraph(recommendations, styles['Normal']))
    elements.append(Spacer(1, 12))

    # Build PDF
    doc.build(elements)
    print(f"Statistical analysis report has been generated and saved to '{file_path}'.")

def generate_summary_table(combined_data):
    """Generates a summary table and saves it to a CSV file."""
    # Calculate quintiles for Gas Price, Block Size, and Transaction Count
    combined_data['Gas Price Quintile'] = pd.qcut(combined_data['Gas Price (Gwei)'], 5, labels=['Q1', 'Q2', 'Q3', 'Q4', 'Q5'])
    combined_data['Block Size Quintile'] = pd.qcut(combined_data['Block Size (KB)'], 5, labels=['Q1', 'Q2', 'Q3', 'Q4', 'Q5'])
    combined_data['Transaction Count Quintile'] = pd.qcut(combined_data['Transaction Count'], 5, labels=['Q1', 'Q2', 'Q3', 'Q4', 'Q5'])

    # Group by Gas Price, Block Size, and Transaction Count Quintiles and calculate summary statistics
    summary_table = combined_data.groupby(['Gas Price Quintile', 'Block Size Quintile', 'Transaction Count Quintile']).agg({
        'Latency (s)': ['mean', 'median', 'std'],
        'Gas Price (Gwei)': ['mean', 'median', 'std'],
        'Block Size (KB)': ['mean', 'median', 'std'],
        'Transaction Count': ['mean', 'median', 'std']
    }).reset_index()

    summary_table.columns = ['Gas Price Quintile', 'Block Size Quintile', 'Transaction Count Quintile',
                             'Latency Mean', 'Latency Median', 'Latency Std',
                             'Gas Price Mean', 'Gas Price Median', 'Gas Price Std',
                             'Block Size Mean', 'Block Size Median', 'Block Size Std',
                             'Transaction Count Mean', 'Transaction Count Median', 'Transaction Count Std']

    # Save the summary table to a CSV file
    summary_filename = 'summary_table_Latency_Vs_Other_Parameters_combined.csv'
    summary_table.to_csv(summary_filename, index=False)
    print(f"Summary table has been saved as '{summary_filename}'.")
    return summary_table

def plot_combined_data(combined_data):
    """Plots combined data and saves the figures."""
    combined_data['Transaction Count'] = combined_data['Transaction Count'].astype(int)

    quintile_labels = ['Q1', 'Q2', 'Q3', 'Q4', 'Q5']
    combined_data['Gas Price Quintile'] = pd.qcut(combined_data['Gas Price (Gwei)'], 5, labels=quintile_labels)
    combined_data['Block Size Quintile'] = pd.qcut(combined_data['Block Size (KB)'], 5, labels=quintile_labels)
    combined_data['Transaction Count Quintile'] = pd.qcut(combined_data['Transaction Count'], 5, labels=quintile_labels)

    fig, axes = plt.subplots(1, 3, figsize=(20, 6), sharey=True)

    for i, (ax, category, title) in enumerate(zip(axes, ['Gas Price Quintile', 'Block Size Quintile', 'Transaction Count Quintile'], ['Gas Price (Gwei) Quintiles', 'Block Size (KB) Quintiles', 'Transaction Count Quintiles'])):
        sns.boxplot(x=category, y='Latency (s)', data=combined_data, ax=ax, palette="Set2", width=0.3)
        ax.set_title(title)
        ax.set_xlabel('')
        ax.set_ylabel('Latency (s)' if i == 0 else '')

        # Calculate and plot mean latency
        means = combined_data.groupby(category)['Latency (s)'].mean()
        ax.plot(means.index, means, 'ro-', label='Mean Latency')
        # Set y-axis limits
        ax.set_ylim(0, combined_data['Latency (s)'].max() + 10)

    plt.tight_layout()
    plt.savefig('Latency_Vs_Other_Parameters_combined.png')
    plt.savefig('Latency_Vs_Other_Parameters_combined.svg')
    plt.savefig('Latency_Vs_Other_Parameters_combined.pdf')
    plt.show()
    print("Plots have been saved.")

# Configuration for HybridPenalty (index-based matching)
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

# Configuration for BreachData (index-based matching)
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

# Process data for all services
df_hybridpenalty = process_service_data(hybridpenalty_data_files, hybridpenalty_block_files, index_based=True)
df_breachdata = process_service_data(breachdata_data_files, breachdata_block_files, index_based=True)

# Combine the data from all services
combined_data = pd.concat([df_hybridpenalty, df_breachdata], ignore_index=True)

# Perform statistical analysis and generate the report
if not combined_data.empty:
    perform_statistical_analysis(combined_data, 'statistical_analysis_report_Low_Gas_Used.pdf')
    # Generate summary table
    summary_table = generate_summary_table(combined_data)
    # Plot combined data
    plot_combined_data(combined_data)
else:
    print("No data available for analysis.")
