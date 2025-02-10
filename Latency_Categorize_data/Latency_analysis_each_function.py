import pandas as pd
import os
from scipy.stats import kruskal
import scikit_posthocs as sp
import numpy as np
# Configuration for AddService data files
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

# Configuration for SelectService data files
selectservice_data_files = [
    {'path': '/home/fjaved/demos/hardhat-project/test/sepolia/SelectService/merged_service_selection_log.csv', 'latency_column': 'Transaction Latency (s)'}
]
selectservice_block_files = [
    '/home/fjaved/demos/hardhat-project/test/sepolia/SelectService/selectService_block_number.csv'
]

# Configuration for HybridPenalty data files
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

# Configuration for BreachData data files
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
# Function to process service data (latency and gas/block details)
def process_service_data(data_files, block_files, index_based=False, use_transaction_hash=False):
    latency_data_list = []
    for file_info in data_files:
        file_path = file_info['path']
        latency_column = file_info['latency_column']
        if os.path.exists(file_path):
            try:
                df = pd.read_csv(file_path)
                if index_based:
                    if 'UserIndex' in df.columns and 'Iteration' in df.columns:
                        df = df.groupby(['Iteration', 'UserIndex']).first().reset_index()
                    elif 'Iteration' in df.columns:
                        df = df.groupby(['Iteration']).first().reset_index()
                elif use_transaction_hash and 'Transaction Hash' in df.columns:
                    df = df.dropna(subset=['Transaction Hash'])
                if latency_column in df.columns:
                    df.rename(columns={latency_column: 'Latency (s)'}, inplace=True)
                    if index_based:
                        latency_data_list.append(df[['Latency (s)', 'Iteration', 'UserIndex']] if 'UserIndex' in df.columns else df[['Latency (s)', 'Iteration']])
                    elif use_transaction_hash:
                        latency_data_list.append(df[['Latency (s)', 'Transaction Hash']])
                else:
                    print(f"Latency column '{latency_column}' not found in {file_path}")
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
        else:
            print(f"File not found: {file_path}")
    
    all_latency_data = pd.concat(latency_data_list, ignore_index=True) if latency_data_list else pd.DataFrame()
    
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
    
    if not all_latency_data.empty and not all_gas_data.empty:
        if index_based:
            merged_data = pd.concat([all_gas_data.reset_index(drop=True), all_latency_data.reset_index(drop=True)], axis=1).dropna()
        elif use_transaction_hash:
            merged_data = pd.merge(all_gas_data, all_latency_data, how='inner', on='Transaction Hash').dropna()
        else:
            merged_data = pd.DataFrame()
        return merged_data
    else:
        print("No data available for some files.")
        return pd.DataFrame()

# Kruskal-Wallis Test and Summary
def perform_kruskal_and_summary(combined_data, group_column):
    groups = combined_data[group_column].unique()
    group_data = [combined_data[combined_data[group_column] == g]['Latency (s)'] for g in groups]
    kruskal_test = kruskal(*group_data)
    print(f"\nKruskal-Wallis test for {group_column}: H = {kruskal_test.statistic:.2f}, p = {kruskal_test.pvalue:.4f}")
    
    if kruskal_test.pvalue < 0.05:
        print(f"Significant differences detected in {group_column}. Post-hoc analysis recommended.")
    else:
        print(f"No significant differences detected in {group_column}.")
    
    return kruskal_test, group_column

# Post-hoc Dunn's Test and Summary
def perform_dunn_posthoc(combined_data, group_column):
    posthoc_results = sp.posthoc_dunn(combined_data, val_col='Latency (s)', group_col=group_column, p_adjust='bonferroni')
    print(f"\nPost-hoc Dunn's Test for {group_column}:")
    print(posthoc_results)

# Configuration for data files and block files
combined_addselect_data_files = addservice_data_files + selectservice_data_files
combined_addselect_block_files = addservice_block_files + selectservice_block_files

combined_hybridbreach_data_files = hybridpenalty_data_files + breachdata_data_files
combined_hybridbreach_block_files = hybridpenalty_block_files + breachdata_block_files

# Process and analyze AddService + SelectService
df_combined_addselect = process_service_data(combined_addselect_data_files, combined_addselect_block_files, use_transaction_hash=True)
if not df_combined_addselect.empty:
    df_combined_addselect['Gas Price Quintile'] = pd.qcut(df_combined_addselect['Gas Price (Gwei)'], 5, labels=['Q1', 'Q2', 'Q3', 'Q4', 'Q5'])
    df_combined_addselect['Block Size Quintile'] = pd.qcut(df_combined_addselect['Block Size (KB)'], 5, labels=['Q1', 'Q2', 'Q3', 'Q4', 'Q5'])
    df_combined_addselect['Transaction Count Quintile'] = pd.qcut(df_combined_addselect['Transaction Count'], 5, labels=['Q1', 'Q2', 'Q3', 'Q4', 'Q5'])
    
    # Perform Kruskal-Wallis and post-hoc tests
    perform_kruskal_and_summary(df_combined_addselect, 'Gas Price Quintile')
    perform_dunn_posthoc(df_combined_addselect, 'Gas Price Quintile')
    perform_kruskal_and_summary(df_combined_addselect, 'Block Size Quintile')
    perform_dunn_posthoc(df_combined_addselect, 'Block Size Quintile')
    perform_kruskal_and_summary(df_combined_addselect, 'Transaction Count Quintile')
    perform_dunn_posthoc(df_combined_addselect, 'Transaction Count Quintile')

# Process and analyze HybridPenalty + BreachData
df_combined_hybridbreach = process_service_data(combined_hybridbreach_data_files, combined_hybridbreach_block_files, index_based=True)
if not df_combined_hybridbreach.empty:
    df_combined_hybridbreach['Gas Price Quintile'] = pd.qcut(df_combined_hybridbreach['Gas Price (Gwei)'], 5, labels=['Q1', 'Q2', 'Q3', 'Q4', 'Q5'])
    df_combined_hybridbreach['Block Size Quintile'] = pd.qcut(df_combined_hybridbreach['Block Size (KB)'], 5, labels=['Q1', 'Q2', 'Q3', 'Q4', 'Q5'])
    df_combined_hybridbreach['Transaction Count Quintile'] = pd.qcut(df_combined_hybridbreach['Transaction Count'], 5, labels=['Q1', 'Q2', 'Q3', 'Q4', 'Q5'])
    
    # Perform Kruskal-Wallis and post-hoc tests
    perform_kruskal_and_summary(df_combined_hybridbreach, 'Gas Price Quintile')
    perform_dunn_posthoc(df_combined_hybridbreach, 'Gas Price Quintile')
    perform_kruskal_and_summary(df_combined_hybridbreach, 'Block Size Quintile')
    perform_dunn_posthoc(df_combined_hybridbreach, 'Block Size Quintile')
    perform_kruskal_and_summary(df_combined_hybridbreach, 'Transaction Count Quintile')
    perform_dunn_posthoc(df_combined_hybridbreach, 'Transaction Count Quintile')
