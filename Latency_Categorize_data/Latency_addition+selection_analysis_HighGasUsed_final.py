import pandas as pd
import os
import matplotlib.pyplot as plt
import seaborn as sns


def process_service_data(data_files, block_files, index_based=False, use_transaction_hash=False):
    # Process Latency Data
    latency_data_list = []
    for file_info in data_files:
        file_path = file_info['path']
        latency_column = file_info['latency_column']
        if os.path.exists(file_path):
            try:
                df = pd.read_csv(file_path)

                # Handle index-based (for breach, penalty, transfer) or transaction hash-based (for addservice, selectservice)
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

def generate_summary_table(combined_data):
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
    
    return summary_table

def plot_combined_data(combined_data):
    combined_data['Transaction Count'] = combined_data['Transaction Count'].astype(int)
    
    quintile_labels = ['Q1', 'Q2', 'Q3', 'Q4', 'Q5']
    combined_data['Gas Price Quintile'] = pd.qcut(combined_data['Gas Price (Gwei)'], 5, labels=quintile_labels)
    combined_data['Block Size Quintile'] = pd.qcut(combined_data['Block Size (KB)'], 5, labels=quintile_labels)
    combined_data['Transaction Count Quintile'] = pd.qcut(combined_data['Transaction Count'], 5, labels=quintile_labels)

    quintiles_gas = pd.qcut(combined_data['Gas Price (Gwei)'], 5)
    quintiles_block_size = pd.qcut(combined_data['Block Size (KB)'], 5)
    quintiles_tx_count = pd.qcut(combined_data['Transaction Count'], 5)

    fig, axes = plt.subplots(1, 3, figsize=(20, 6), sharey=True)
    categories = ['Gas Price Quintile', 'Block Size Quintile', 'Transaction Count Quintile']
    quintile_ranges = [quintiles_gas, quintiles_block_size, quintiles_tx_count]
    titles = ['Gas Price (Gwei) Quintiles', 'Block Size (KB) Quintiles', 'Transaction Count Quintiles']

    for i, (ax, category, title, quintile_range) in enumerate(zip(axes, categories, titles, quintile_ranges)):
        sns.boxplot(x=category, y='Latency (s)', data=combined_data, ax=ax, palette="Set2", width=0.3)
        ax.set_xlabel(title)
        if i == 0:
            ax.set_ylabel('Latency (s)')
        else:
            ax.set_ylabel('')
        
        means = combined_data.groupby(category)['Latency (s)'].mean()
        ax.plot(range(len(means)), means, marker='o', linestyle='--', color='red', label='Mean Latency', linewidth=1)

        if category == 'Gas Price Quintile':
            range_text = '\n'.join([f"{label}: {category_range.left:.2f} - {category_range.right:.2f}"
                                    for label, category_range in zip(quintile_labels, quintile_range.cat.categories)])
        elif category == 'Block Size Quintile':
            range_text = '\n'.join([f"{label}: {category_range.left:.2f} - {category_range.right:.2f}"
                                    for label, category_range in zip(quintile_labels, quintile_range.cat.categories)])
        elif category == 'Transaction Count Quintile':
            range_text = '\n'.join([f"{label}: {int(category_range.left)} - {int(category_range.right)}"
                                    for label, category_range in zip(quintile_labels, quintile_range.cat.categories)])

        ax.text(0.05, 0.95, range_text, transform=ax.transAxes, fontsize=10,
                verticalalignment='top', bbox=dict(facecolor='white', alpha=0.5))

        ax.legend(loc='upper right')

    plt.tight_layout()
    plt.savefig('/home/fjaved/demos/hardhat-project/Latency_Vs_Other_Parameters_HighGasUsed_v1.png')
    plt.savefig('/home/fjaved/demos/hardhat-project/Latency_Vs_Other_Parameters_HighGasUsed_v1.svg')
    plt.savefig('/home/fjaved/demos/hardhat-project/Latency_Vs_Other_Parameters_HighGasUsed_v1.pdf')

    plt.show()


    

# Configuration for AddService
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

# Configuration for SelectService
selectservice_data_files = [
    {'path': '/home/fjaved/demos/hardhat-project/test/sepolia/SelectService/merged_service_selection_log.csv', 'latency_column': 'Transaction Latency (s)'}
]
selectservice_block_files = [
    '/home/fjaved/demos/hardhat-project/test/sepolia/SelectService/selectService_block_number.csv'
]



# Process data for all services
df_addservice = process_service_data(addservice_data_files, addservice_block_files, use_transaction_hash=True)
df_selectservice = process_service_data(selectservice_data_files, selectservice_block_files, use_transaction_hash=True)

# Combine the data from all services
combined_data = pd.concat([df_addservice, df_selectservice], ignore_index=True)

# Plot combined data and generate summary table
if not combined_data.empty:
    plot_combined_data(combined_data)
    summary_table = generate_summary_table(combined_data)
    
    # Save the summary table to a CSV file
    summary_filename = 'summary_table_Latency_Vs_Other_Parameters_for_High_Gas_v1.csv'
    summary_table.to_csv(summary_filename, index=False)
    
    print(f"Summary table has been saved as '{summary_filename}'.")
else:
    print("No data available for plotting.")

def plot_combined_data(combined_data):
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
        ax.set_ylim(0, 175)

    plt.tight_layout()
    plt.show()

