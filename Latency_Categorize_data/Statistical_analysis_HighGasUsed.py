import pandas as pd
import numpy as np
from scipy.stats import kruskal
import scikit_posthocs as sp
import os
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

def process_service_data(data_files, block_files, use_transaction_hash):
    """Processes latency and block data from specified files."""
    latency_data_list = []
    for file_info in data_files:
        file_path = file_info['path']
        latency_column = file_info['latency_column']
        if os.path.exists(file_path):
            df = pd.read_csv(file_path)
            if use_transaction_hash:
                df = df.dropna(subset=['Transaction Hash'])
            df.rename(columns={latency_column: 'Latency (s)'}, inplace=True)
            latency_data_list.append(df[['Latency (s)', 'Transaction Hash']])
    all_latency_data = pd.concat(latency_data_list, ignore_index=True) if latency_data_list else pd.DataFrame()

    block_data_list = []
    for file_path in block_files:
        if os.path.exists(file_path):
            data = pd.read_csv(file_path)
            block_data_list.append(data[['Gas Price (Gwei)', 'Block Size (bytes)', 'Transaction Count', 'Transaction Hash']])
    all_block_data = pd.concat(block_data_list, ignore_index=True) if block_data_list else pd.DataFrame()

    if not all_latency_data.empty and not all_block_data.empty:
        merged_data = pd.merge(all_block_data, all_latency_data, on='Transaction Hash', how='inner')
        return merged_data
    else:
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
    - <b>Block Size (bytes)</b><br/>
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

    for feature in ['Gas Price (Gwei)', 'Block Size (bytes)', 'Transaction Count']:
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
    elements.append(Paragraph(
        "- <b>Gas Price</b> and <b>Transaction Count</b> show significant differences in transaction latency across quintiles.<br/>"
        "- <b>Block Size</b> does not show significant differences, suggesting it may not impact transaction latency.", styles['Normal']))
    elements.append(Spacer(1, 12))

    # For each feature
    for feature in ['Gas Price (Gwei)', 'Block Size (bytes)', 'Transaction Count']:
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

            # Specific Interpretation
            elements.append(Paragraph("Interpretation:", styles['Heading3']))
            if feature == 'Gas Price (Gwei)':
                gas_price_interpretation = """
                - Transactions in <b>Q5</b> (highest Gas Price quintile) tend to have <b>lower latencies</b> compared to other quintiles.<br/>
                - <b>Q4</b> shows higher latencies compared to Q1, Q2, and Q3.
                """
                elements.append(Paragraph(gas_price_interpretation, styles['Normal']))
            elif feature == 'Transaction Count':
                txn_count_interpretation = """
                - Higher transaction counts (<b>Q5</b>) are associated with <b>higher latencies</b>.<br/>
                - Significant differences are observed primarily between the highest quintile (Q5) and the lower quintiles.
                """
                elements.append(Paragraph(txn_count_interpretation, styles['Normal']))
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
    <b>Gas Price (Gwei):</b><br/>
    - Highest gas prices (Q5) are associated with <b>lower transaction latencies</b>.<br/>
    - Mid-range gas prices (Q4) are associated with <b>higher latencies</b>.<br/><br/>
    <b>Block Size (bytes):</b><br/>
    - No significant impact on transaction latency was observed across different block sizes.<br/><br/>
    <b>Transaction Count:</b><br/>
    - Higher transaction counts (Q5) correlate with <b>increased transaction latency</b>.<br/><br/>
    """
    elements.append(Paragraph(conclusions, styles['Normal']))
    elements.append(Spacer(1, 12))

    # Recommendations
    elements.append(Paragraph("4. Recommendations", styles['Heading2']))
    elements.append(Spacer(1, 12))
    recommendations = """
    <b>For Users:</b><br/>
    - To minimize latency, consider setting gas prices at higher levels (Q5).<br/>
    - Be cautious of setting gas prices in the mid-range (Q4), as this may not reduce latency effectively.<br/><br/>
    <b>For Network Operators:</b><br/>
    - Implement strategies to manage transaction counts per block to prevent latency increases.<br/>
    - Consider optimizing protocols to handle higher transaction volumes without compromising speed.<br/><br/>
    <b>For Developers:</b><br/>
    - Although block size didn't show a significant impact, monitoring is advised as network conditions evolve.<br/>
    - Future studies could explore larger block sizes or different block configurations.<br/><br/>
    """
    elements.append(Paragraph(recommendations, styles['Normal']))
    elements.append(Spacer(1, 12))

    # Final Thoughts
    elements.append(Paragraph("5. Final Thoughts", styles['Heading2']))
    elements.append(Spacer(1, 12))
    final_thoughts = """
    This analysis provides insights into how gas prices and transaction counts affect transaction latency in blockchain networks. By understanding these relationships, stakeholders can make informed decisions to optimize performance and user experience.
    """
    elements.append(Paragraph(final_thoughts, styles['Normal']))
    elements.append(Spacer(1, 12))

    # Build PDF
    doc.build(elements)

# Data file configurations
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

# Processing and analyzing data
df_service = process_service_data(addservice_data_files, addservice_block_files, use_transaction_hash=True)
if not df_service.empty:
    perform_statistical_analysis(df_service, 'analysis_report.pdf')
    print("Report generated: analysis_report.pdf")
else:
    print("No data available for analysis.")
