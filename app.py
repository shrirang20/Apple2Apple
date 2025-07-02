# app.py (updated)

import streamlit as st
import pandas as pd
from utils import compare_dataframes_by_groups

st.set_page_config(page_title="CSV Comparison App", layout="wide")
st.title("🔍 CSV Apple-to-Apple Comparison Tool (History Only)")

st.markdown("""
Upload two CSV files to compare by dataset_id groups, tactic_id rows, and recency_flag matching. 
**Only rows with recency_flag = 'history' will be compared.** 
**The 'description' column is ignored in comparisons.**
For timestamps in format 'YYYY-MM-DD HH:MM:SS.ffffff+00:00', only the date part is compared.
NULL/empty tactic_id values are treated as equal.
""")

file1 = st.file_uploader("Upload CSV File A", type=["csv"])
file2 = st.file_uploader("Upload CSV File B", type=["csv"])

if file1 and file2:
    try:
        df1 = pd.read_csv(file1)
        df2 = pd.read_csv(file2)
        
        # Check if required columns exist in both files
        required_columns = ['dataset_id', 'tactic_id', 'recency_flag', 'dataset_nm', 'tactic_nm', 'channel_nm']
        missing_cols_df1 = [col for col in required_columns if col not in df1.columns]
        missing_cols_df2 = [col for col in required_columns if col not in df2.columns]
        
        if missing_cols_df1:
            st.error(f"❌ Missing columns in File A: {', '.join(missing_cols_df1)}")
            st.stop()
        if missing_cols_df2:
            st.error(f"❌ Missing columns in File B: {', '.join(missing_cols_df2)}")
            st.stop()
        
        st.success("✅ Files loaded successfully!")
        
        # Show basic info about the files
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"**File A:** {len(df1)} rows, {len(df1.columns)} columns")
            st.write(f"Unique dataset_ids: {df1['dataset_id'].nunique()}")
            st.write(f"Unique tactic_ids: {df1['tactic_id'].nunique()}")
            st.write(f"History rows: {len(df1[df1['recency_flag'] == 'history'])}")
        with col2:
            st.info(f"**File B:** {len(df2)} rows, {len(df2.columns)} columns")
            st.write(f"Unique dataset_ids: {df2['dataset_id'].nunique()}")
            st.write(f"Unique tactic_ids: {df2['tactic_id'].nunique()}")
            st.write(f"History rows: {len(df2[df2['recency_flag'] == 'history'])}")
        
        # Show recency flag distribution
        st.subheader("📊 Recency Flag Distribution")
        col1, col2 = st.columns(2)
        with col1:
            st.write("**File A Recency Flags:**")
            st.write(df1['recency_flag'].value_counts().to_dict())
        with col2:
            st.write("**File B Recency Flags:**")
            st.write(df2['recency_flag'].value_counts().to_dict())
        
        # Perform comparison
        with st.spinner("Comparing history rows by dataset_id groups and tactic_id rows (ignoring description column)..."):
            result = compare_dataframes_by_groups(df1.copy(), df2.copy())
        
        # Display validation messages if any
        if result.get("validation_messages"):
            st.subheader("⚠️ Validation Messages")
            for msg in result["validation_messages"]:
                st.warning(msg)
        
        # Display results
        st.header("📊 Comparison Results (History Only)")
        
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Groups Only in File A", len(result["groups_only_in_df1"]))
        with col2:
            st.metric("Groups Only in File B", len(result["groups_only_in_df2"]))
        with col3:
            st.metric("Modified Groups", len(result["modified_groups"]))
        with col4:
            st.metric("Identical Groups", len(result["identical_groups"]))
        
        # Additional metrics
        total_tactic_recency_changes = sum(len(changes.get("tactic_recency_changes", {})) for changes in result["modified_groups"].values())
        total_cell_changes = sum(len(changes.get("cell_changes", [])) for changes in result["modified_groups"].values())
        total_unmatched_combinations = sum(len(changes.get("unmatched_combinations", {}).get("only_in_group1", [])) + 
                                         len(changes.get("unmatched_combinations", {}).get("only_in_group2", [])) 
                                         for changes in result["modified_groups"].values())
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Tactic+Recency Changes", total_tactic_recency_changes)
        with col2:
            st.metric("Total Cell Changes", total_cell_changes)
        with col3:
            st.metric("Unmatched Combinations", total_unmatched_combinations)
        
        # Column differences
        if result["column_differences"]["only_in_df1"] or result["column_differences"]["only_in_df2"]:
            st.subheader("🔄 Column Differences")
            if result["column_differences"]["only_in_df1"]:
                st.warning(f"**Columns only in File A:** {', '.join(result['column_differences']['only_in_df1'])}")
            if result["column_differences"]["only_in_df2"]:
                st.warning(f"**Columns only in File B:** {', '.join(result['column_differences']['only_in_df2'])}")
        
        # Groups only in File A
        if result["groups_only_in_df1"]:
            st.subheader("➖ Groups Only in File A (Removed)")
            st.write(f"Dataset IDs: {', '.join(map(str, sorted(result['groups_only_in_df1'])))}")
            
            removed_data = []
            for dataset_id in sorted(result["groups_only_in_df1"]):
                group_data = df1[(df1['dataset_id'] == dataset_id) & (df1['recency_flag'] == 'history')]
                for _, row in group_data.iterrows():
                    removed_data.append(row.to_dict())
            
            if removed_data:
                st.dataframe(pd.DataFrame(removed_data), use_container_width=True)
        
        # Groups only in File B
        if result["groups_only_in_df2"]:
            st.subheader("➕ Groups Only in File B (Added)")
            st.write(f"Dataset IDs: {', '.join(map(str, sorted(result['groups_only_in_df2'])))}")
            
            added_data = []
            for dataset_id in sorted(result["groups_only_in_df2"]):
                group_data = df2[(df2['dataset_id'] == dataset_id) & (df2['recency_flag'] == 'history')]
                for _, row in group_data.iterrows():
                    added_data.append(row.to_dict())
            
            if added_data:
                st.dataframe(pd.DataFrame(added_data), use_container_width=True)
        
        # Modified groups
        if result["modified_groups"]:
            st.subheader("🛠️ Modified Groups")
            
            for dataset_id in sorted(result["modified_groups"].keys()):
                with st.expander(f"Dataset ID: {dataset_id}", expanded=False):
                    changes = result["modified_groups"][dataset_id]
                    
                    # Show group-level summary
                    st.write(f"**Group Summary:**")
                    st.write(f"- File A: {changes['group1_tactic_recency_count']} tactic+recency combination(s)")
                    st.write(f"- File B: {changes['group2_tactic_recency_count']} tactic+recency combination(s)")
                    
                    # Show unmatched combinations in simplified format
                    if changes.get("unmatched_combinations"):
                        unmatched = changes["unmatched_combinations"]
                        
                        if unmatched.get("only_in_group1"):
                            st.error("**❌ Tactic+Recency combinations only in File A (Removed):**")
                            unmatched_df = pd.DataFrame(unmatched["only_in_group1"])
                            # Display with additional info
                            display_cols = ['dataset_nm', 'tactic_id', 'tactic_nm', 'channel_nm', 'recency_flag', 'count']
                            st.dataframe(unmatched_df[display_cols], use_container_width=True)
                        
                        if unmatched.get("only_in_group2"):
                            st.success("**➕ Tactic+Recency combinations only in File B (Added):**")
                            unmatched_df = pd.DataFrame(unmatched["only_in_group2"])
                            # Display with additional info
                            display_cols = ['dataset_nm', 'tactic_id', 'tactic_nm', 'channel_nm', 'recency_flag', 'count']
                            st.dataframe(unmatched_df[display_cols], use_container_width=True)
                    
                    # Tactic+Recency level changes
                    if changes.get("tactic_recency_changes"):
                        st.write("**🔄 Modified Tactic+Recency Combinations:**")
                        
                        for combo_key, combo_change in changes["tactic_recency_changes"].items():
                            tactic_id, recency_flag = combo_key
                            # Handle NULL tactic_id display
                            display_tactic = "NULL" if tactic_id == 'NULL' else tactic_id
                            
                            # Display header with additional info
                            st.warning(
                                f"**🔄 Tactic {display_tactic} ({combo_change.get('tactic_nm', 'N/A')}), "
                                f"Recency {recency_flag} - Modified**\n"
                                f"**Dataset:** {combo_change.get('dataset_nm', 'N/A')} | "
                                f"**Channel:** {combo_change.get('channel_nm', 'N/A')}"
                            )
                            
                            if combo_change.get("cell_changes"):
                                cell_df = pd.DataFrame(combo_change["cell_changes"])
                                # Reorder columns to show identifying info first
                                col_order = [
                                    'dataset_nm', 'tactic_id', 'tactic_nm', 'channel_nm', 'recency_flag',
                                    'Column', 'File_A_Value', 'File_B_Value', 'Change_Type'
                                ]
                                # Only include columns that exist in the dataframe
                                col_order = [col for col in col_order if col in cell_df.columns]
                                st.dataframe(cell_df[col_order], use_container_width=True)
                    
                    # Overall cell changes for this group
                    if changes.get("cell_changes"):
                        st.write("**📋 All Cell Changes in Group:**")
                        cell_changes_df = pd.DataFrame(changes["cell_changes"])
                        # Reorder columns to show identifying info first
                        col_order = [
                            'dataset_nm', 'tactic_id', 'tactic_nm', 'channel_nm', 'recency_flag',
                            'Column', 'File_A_Value', 'File_B_Value', 'Change_Type'
                        ]
                        # Only include columns that exist in the dataframe
                        col_order = [col for col in col_order if col in cell_changes_df.columns]
                        st.dataframe(cell_changes_df[col_order], use_container_width=True)
        
        # Identical groups
        if result["identical_groups"]:
            st.subheader("✅ Identical Groups")
            st.write(f"Dataset IDs with no changes: {', '.join(map(str, sorted(result['identical_groups'])))}")
        
        # Download options
        st.subheader("📥 Download Reports")
        
        # Prepare detailed changes report
        detailed_changes = []
        tactic_recency_summary = []
        unmatched_summary = []
        
        for dataset_id, changes in result["modified_groups"].items():
            # Collect cell changes
            if changes.get("cell_changes"):
                for change in changes["cell_changes"]:
                    change_record = change.copy()
                    change_record["dataset_id"] = dataset_id
                    detailed_changes.append(change_record)
            
            # Collect tactic+recency level summary
            if changes.get("tactic_recency_changes"):
                for (tactic_id, recency_flag), combo_change in changes["tactic_recency_changes"].items():
                    tactic_recency_summary.append({
                        "dataset_id": dataset_id,
                        "dataset_nm": combo_change.get("dataset_nm", "N/A"),
                        "tactic_id": tactic_id if tactic_id != 'NULL' else None,
                        "tactic_nm": combo_change.get("tactic_nm", "N/A"),
                        "channel_nm": combo_change.get("channel_nm", "N/A"),
                        "recency_flag": recency_flag,
                        "change_type": "modified",
                        "cell_changes_count": len(combo_change.get("cell_changes", []))
                    })
            
            # Collect unmatched combinations
            if changes.get("unmatched_combinations"):
                unmatched = changes["unmatched_combinations"]
                for combo in unmatched.get("only_in_group1", []):
                    unmatched_summary.append({
                        "dataset_id": dataset_id,
                        "dataset_nm": combo.get("dataset_nm", "N/A"),
                        "tactic_id": combo["tactic_id"] if combo["tactic_id"] != 'NULL' else None,
                        "tactic_nm": combo.get("tactic_nm", "N/A"),
                        "channel_nm": combo.get("channel_nm", "N/A"),
                        "recency_flag": combo["recency_flag"],
                        "status": "only_in_file_a",
                        "change_type": "removed"
                    })
                for combo in unmatched.get("only_in_group2", []):
                    unmatched_summary.append({
                        "dataset_id": dataset_id,
                        "dataset_nm": combo.get("dataset_nm", "N/A"),
                        "tactic_id": combo["tactic_id"] if combo["tactic_id"] != 'NULL' else None,
                        "tactic_nm": combo.get("tactic_nm", "N/A"),
                        "channel_nm": combo.get("channel_nm", "N/A"),
                        "recency_flag": combo["recency_flag"],
                        "status": "only_in_file_b",
                        "change_type": "added"
                    })
        
        # Download buttons
        if detailed_changes:
            changes_df = pd.DataFrame(detailed_changes)
            st.download_button(
                "📊 Download Detailed Cell Changes Report",
                changes_df.to_csv(index=False),
                "detailed_cell_changes_report.csv",
                mime="text/csv"
            )
        
        if tactic_recency_summary:
            tactic_recency_df = pd.DataFrame(tactic_recency_summary)
            st.download_button(
                "🎯 Download Tactic+Recency Summary Report",
                tactic_recency_df.to_csv(index=False),
                "tactic_recency_summary.csv",
                mime="text/csv"
            )
        
        if unmatched_summary:
            unmatched_df = pd.DataFrame(unmatched_summary)
            st.download_button(
                "⚠️ Download Unmatched Combinations Report",
                unmatched_df.to_csv(index=False),
                "unmatched_combinations_report.csv",
                mime="text/csv"
            )
        
        # Overall summary report
        summary_data = {
            "Metric": [
                "Total Groups in File A",
                "Total Groups in File B", 
                "Groups Only in File A",
                "Groups Only in File B",
                "Modified Groups",
                "Identical Groups",
                "Total Tactic+Recency Changes",
                "Total Cell Changes",
                "Total Unmatched Combinations"
            ],
            "Count": [
                df1['dataset_id'].nunique(),
                df2['dataset_id'].nunique(),
                len(result["groups_only_in_df1"]),
                len(result["groups_only_in_df2"]),
                len(result["modified_groups"]),
                len(result["identical_groups"]),
                total_tactic_recency_changes,
                total_cell_changes,
                total_unmatched_combinations
            ]
        }
        summary_df = pd.DataFrame(summary_data)
        
        st.download_button(
            "📋 Download Overall Summary Report",
            summary_df.to_csv(index=False),
            "overall_comparison_summary.csv",
            mime="text/csv"
        )
        
    except Exception as e:
        st.error(f"❌ An error occurred: {str(e)}")
        st.write("Please make sure both files are valid CSV files with required columns.")
        st.exception(e)