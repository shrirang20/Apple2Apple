import pandas as pd
import numpy as np
from datetime import datetime

def compare_dataframes_by_groups(df1, df2):
    """
    Compare two dataframes by grouping on 'dataset_id', then comparing 
    rows within each group based on matching 'tactic_id' AND 'recency_flag'.
    Only compares rows where recency_flag = 'history' and ignores 'description' column.
    
    Args:
        df1: First dataframe (File A)
        df2: Second dataframe (File B)
    
    Returns:
        Dictionary containing comparison results and validation messages
    """
    # Initialize validation messages
    validation_messages = []
    
    # Standardize NULL/empty values in tactic_id and tactic_nm
    for df in [df1, df2]:
        df['tactic_id'] = df['tactic_id'].replace(['', 'NULL', 'null', 'None'], np.nan)
        df['tactic_nm'] = df['tactic_nm'].replace(['', 'NULL', 'null', 'None'], np.nan)
    
    # Check for NULL tactic_id values
    for df, file_name in [(df1, "File A"), (df2, "File B")]:
        null_tactics = df[df['tactic_id'].isna()]
        if len(null_tactics) > 0:
            validation_messages.append(f"⚠️ {file_name} contains {len(null_tactics)} rows with NULL tactic_id values")
    
    # Check for missing key columns
    key_columns = ['tactic_id', 'tactic_nm', 'dataset_id', 'dataset_nm']
    for file_name, df in [("File A", df1), ("File B", df2)]:
        missing_cols = [col for col in key_columns if col not in df.columns]
        if missing_cols:
            validation_messages.append(f"⚠️ {file_name} is missing the following key columns: {', '.join(missing_cols)}")
    
    # Filter to only include rows with recency_flag = 'history'
    df1 = df1[df1['recency_flag'] == 'history'].copy()
    df2 = df2[df2['recency_flag'] == 'history'].copy()
    
    # Sort both dataframes by dataset_id, tactic_id, and recency_flag
    df1 = df1.sort_values(['dataset_id', 'tactic_id', 'recency_flag']).reset_index(drop=True)
    df2 = df2.sort_values(['dataset_id', 'tactic_id', 'recency_flag']).reset_index(drop=True)
    
    # Get unique dataset_ids from both files
    df1_ids = set(df1['dataset_id'].unique())
    df2_ids = set(df2['dataset_id'].unique())
    
    # Find groups that are only in one file
    groups_only_in_df1 = df1_ids - df2_ids
    groups_only_in_df2 = df2_ids - df1_ids
    common_groups = df1_ids.intersection(df2_ids)
    
    # Compare column structures
    all_columns_df1 = set(df1.columns)
    all_columns_df2 = set(df2.columns)
    
    # Remove 'description' from column differences since we're ignoring it
    all_columns_df1.discard('description')
    all_columns_df2.discard('description')
    
    column_differences = {
        "only_in_df1": list(all_columns_df1 - all_columns_df2),
        "only_in_df2": list(all_columns_df2 - all_columns_df1),
        "common": list(all_columns_df1.intersection(all_columns_df2))
    }
    
    # Compare groups that exist in both files
    modified_groups = {}
    identical_groups = []
    
    for dataset_id in common_groups:
        group1 = df1[df1['dataset_id'] == dataset_id].copy()
        group2 = df2[df2['dataset_id'] == dataset_id].copy()
        
        # Compare groups by tactic_id and recency_flag combination
        group_comparison = compare_groups_by_tactic_recency(group1, group2, dataset_id, column_differences["common"])
        
        if group_comparison["has_changes"]:
            modified_groups[dataset_id] = group_comparison
        else:
            identical_groups.append(dataset_id)
    
    return {
        "groups_only_in_df1": groups_only_in_df1,
        "groups_only_in_df2": groups_only_in_df2,
        "modified_groups": modified_groups,
        "identical_groups": identical_groups,
        "column_differences": column_differences,
        "validation_messages": validation_messages
    }

def normalize_date_or_timestamp(value):
    """
    Normalize dates and timestamps to a standard format for comparison.
    For timestamps with timezone (format: YYYY-MM-DD HH:MM:SS.ffffff+00:00),
    only compare the date part.
    Returns the normalized value if it's a date/timestamp, otherwise returns the original value.
    """
    if pd.isna(value):
        return value
        
    # Check if it's a timestamp with timezone (format: YYYY-MM-DD HH:MM:SS.ffffff+00:00)
    if isinstance(value, str) and len(value) > 19 and value[10] == ' ' and '+' in value:
        try:
            # Extract just the date part
            return value[:10]  # Returns YYYY-MM-DD
        except:
            pass
        
    # Try to parse as datetime with timezone
    try:
        dt = pd.to_datetime(value)
        # Convert to ISO format string without timezone for comparison
        return dt.isoformat().split('+')[0]  # Remove timezone info
    except:
        pass
        
    # Try to parse as date
    try:
        dt = pd.to_datetime(value, errors='raise')
        return dt.strftime('%Y-%m-%d')  # Standard date format
    except:
        return value

def compare_values(val1, val2):
    """
    Compare two values with special handling for dates/timestamps.
    Returns True if values are equal (including same date in different formats).
    """
    if pd.isna(val1) and pd.isna(val2):
        return True
        
    # Normalize dates/timestamps
    norm_val1 = normalize_date_or_timestamp(val1)
    norm_val2 = normalize_date_or_timestamp(val2)
    
    if norm_val1 != val1 or norm_val2 != val2:
        # At least one value was a date/timestamp that got normalized
        return norm_val1 == norm_val2
    
    return val1 == val2

def compare_groups_by_tactic_recency(group1, group2, dataset_id, common_columns):
    """
    Compare two groups by matching rows with same tactic_id AND recency_flag.
    Ignores the 'description' column in comparisons.
    
    Args:
        group1: Group from first dataframe
        group2: Group from second dataframe
        dataset_id: The dataset_id being compared
        common_columns: List of columns present in both dataframes
    
    Returns:
        Dictionary containing group comparison results
    """
    
    # Remove 'description' from common_columns if present
    common_columns = [col for col in common_columns if col != 'description']
    
    # Reset indices and sort by tactic_id and recency_flag
    group1 = group1.sort_values(['tactic_id', 'recency_flag']).reset_index(drop=True)
    group2 = group2.sort_values(['tactic_id', 'recency_flag']).reset_index(drop=True)
    
    # Create combination keys (tactic_id, recency_flag) for both groups
    group1['_combo_key'] = list(zip(
        group1['tactic_id'].fillna('NULL'), 
        group1['recency_flag']
    ))
    group2['_combo_key'] = list(zip(
        group2['tactic_id'].fillna('NULL'), 
        group2['recency_flag']
    ))
    
    # Get unique combinations from both groups
    group1_combos = set(group1['_combo_key'].unique())
    group2_combos = set(group2['_combo_key'].unique())
    
    # Find combinations that are only in one group
    combos_only_in_group1 = group1_combos - group2_combos
    combos_only_in_group2 = group2_combos - group1_combos
    common_combos = group1_combos.intersection(group2_combos)
    
    tactic_recency_changes = {}
    cell_changes = []
    has_changes = False
    
    # Handle unmatched combinations
    unmatched_combinations = {
        "only_in_group1": [],
        "only_in_group2": []
    }
    
    # Combinations only in group1 (removed combinations)
    for combo_key in combos_only_in_group1:
        has_changes = True
        tactic_id, recency_flag = combo_key
        combo_rows = group1[group1['_combo_key'] == combo_key]
        
        for _, row in combo_rows.iterrows():
            # Simplified display format
            display_data = {
                "dataset_id": dataset_id,
                "tactic_id": tactic_id if tactic_id != 'NULL' else None,
                "recency_flag": recency_flag,
                "count": 1  # Count of rows with this combination
            }
            unmatched_combinations["only_in_group1"].append(display_data)
    
    # Combinations only in group2 (added combinations)
    for combo_key in combos_only_in_group2:
        has_changes = True
        tactic_id, recency_flag = combo_key
        combo_rows = group2[group2['_combo_key'] == combo_key]
        
        for _, row in combo_rows.iterrows():
            # Simplified display format
            display_data = {
                "dataset_id": dataset_id,
                "tactic_id": tactic_id if tactic_id != 'NULL' else None,
                "recency_flag": recency_flag,
                "count": 1  # Count of rows with this combination
            }
            unmatched_combinations["only_in_group2"].append(display_data)
    
    # Compare combinations that exist in both groups
    for combo_key in common_combos:
        tactic_id, recency_flag = combo_key
        
        # Get rows with matching combination from both groups
        combo_rows_1 = group1[group1['_combo_key'] == combo_key].drop('_combo_key', axis=1)
        combo_rows_2 = group2[group2['_combo_key'] == combo_key].drop('_combo_key', axis=1)
        
        # Compare the combination
        combo_comparison = compare_tactic_recency_combination(
            combo_rows_1, combo_rows_2, 
            tactic_id if tactic_id != 'NULL' else None, 
            recency_flag, 
            common_columns, dataset_id
        )
        
        if combo_comparison["has_changes"]:
            has_changes = True
            tactic_recency_changes[combo_key] = {
                "cell_changes": combo_comparison["cell_changes"]
            }
            cell_changes.extend(combo_comparison["cell_changes"])
    
    # Clean up temporary columns
    if '_combo_key' in group1.columns:
        group1 = group1.drop('_combo_key', axis=1)
    if '_combo_key' in group2.columns:
        group2 = group2.drop('_combo_key', axis=1)
    
    return {
        "has_changes": has_changes,
        "tactic_recency_changes": tactic_recency_changes,
        "unmatched_combinations": unmatched_combinations,
        "cell_changes": cell_changes,
        "group1_tactic_recency_count": len(group1_combos),
        "group2_tactic_recency_count": len(group2_combos),
        "combos_only_in_group1": combos_only_in_group1,
        "combos_only_in_group2": combos_only_in_group2,
        "common_combos": common_combos
    }

def compare_tactic_recency_combination(rows1, rows2, tactic_id, recency_flag, common_columns, dataset_id):
    """
    Compare rows with the same tactic_id and recency_flag combination.
    Ignores the 'description' column in comparisons.
    
    Args:
        rows1: Rows from first group with same tactic_id and recency_flag
        rows2: Rows from second group with same tactic_id and recency_flag
        tactic_id: The tactic_id being compared
        recency_flag: The recency_flag being compared
        common_columns: List of columns present in both dataframes
        dataset_id: The dataset_id for reference
    
    Returns:
        Dictionary containing combination comparison results
    """
    
    cell_changes = []
    has_changes = False
    
    # Reset indices for easier comparison
    rows1 = rows1.reset_index(drop=True)
    rows2 = rows2.reset_index(drop=True)
    
    # Handle case where there are multiple rows with same combination
    min_rows = min(len(rows1), len(rows2))
    max_rows = max(len(rows1), len(rows2))
    
    # Compare common rows
    for row_idx in range(min_rows):
        row1 = rows1.iloc[row_idx]
        row2 = rows2.iloc[row_idx]
        
        for col in common_columns:
            # Skip description column
            if col == 'description':
                continue
                
            val1 = row1[col]
            val2 = row2[col]
            
            # Handle NaN comparisons
            if pd.isna(val1) and pd.isna(val2):
                continue
                
            # Compare values with special handling for dates/timestamps
            if not compare_values(val1, val2):
                has_changes = True
                cell_changes.append({
                    "dataset_id": dataset_id,
                    "tactic_id": tactic_id,
                    "recency_flag": recency_flag,
                    "Row_Index": row_idx if max_rows > 1 else None,
                    "Column": col,
                    "File_A_Value": val1 if not pd.isna(val1) else "NULL",
                    "File_B_Value": val2 if not pd.isna(val2) else "NULL",
                    "Change_Type": get_change_type(val1, val2)
                })
    
    # Handle extra rows (if counts differ)
    if len(rows1) != len(rows2):
        has_changes = True
        if len(rows1) > len(rows2):
            # Extra rows in file A (removed in file B)
            for row_idx in range(min_rows, len(rows1)):
                row1 = rows1.iloc[row_idx]
                for col in common_columns:
                    if col == 'description':
                        continue
                    cell_changes.append({
                        "dataset_id": dataset_id,
                        "tactic_id": tactic_id,
                        "recency_flag": recency_flag,
                        "Row_Index": row_idx,
                        "Column": col,
                        "File_A_Value": row1[col] if not pd.isna(row1[col]) else "NULL",
                        "File_B_Value": "ROW_REMOVED",
                        "Change_Type": "Row Removed"
                    })
        else:
            # Extra rows in file B (added in file B)
            for row_idx in range(min_rows, len(rows2)):
                row2 = rows2.iloc[row_idx]
                for col in common_columns:
                    if col == 'description':
                        continue
                    cell_changes.append({
                        "dataset_id": dataset_id,
                        "tactic_id": tactic_id,
                        "recency_flag": recency_flag,
                        "Row_Index": row_idx,
                        "Column": col,
                        "File_A_Value": "ROW_ADDED",
                        "File_B_Value": row2[col] if not pd.isna(row2[col]) else "NULL",
                        "Change_Type": "Row Added"
                    })
    
    return {
        "has_changes": has_changes,
        "cell_changes": cell_changes
    }

def get_change_type(val1, val2):
    """
    Determine the type of change between two values.
    """
    if pd.isna(val1) and not pd.isna(val2):
        return "Value Added"
    elif not pd.isna(val1) and pd.isna(val2):
        return "Value Removed"
    elif pd.isna(val1) and pd.isna(val2):
        return "No Change"
    else:
        # Check if values are dates/timestamps that are equal when normalized
        norm_val1 = normalize_date_or_timestamp(val1)
        norm_val2 = normalize_date_or_timestamp(val2)
        if norm_val1 == norm_val2:
            return "No Change"
        return "Value Modified"