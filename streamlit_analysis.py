import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from io import StringIO

# Page configuration
st.set_page_config(
    page_title="Talend Migration Analysis",
    page_icon="🔄",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🔄 Talend Migration Analysis Dashboard")
st.markdown("Upload your Talend component data to analyze migration complexity and effort estimation.")

# Sidebar for configuration
st.sidebar.header("Configuration")

# File upload
uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

if uploaded_file is not None:
    # Load data
    try:
        df = pd.read_csv(uploaded_file)
        st.success(f"File uploaded successfully! {len(df)} rows loaded.")
        
        # Validate columns
        expected_columns = ['file', 'component_type', 'unique_name']
        if not all(col in df.columns for col in expected_columns):
            st.error(f"CSV must contain columns: {expected_columns}")
            st.stop()
        
        # Data preprocessing
        st.subheader("📊 Data Overview")
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Raw Data Sample:**")
            st.dataframe(df.head())
        
        with col2:
            st.write("**Data Summary:**")
            st.write(f"Total rows: {len(df)}")
            st.write(f"Unique files: {df['file'].nunique()}")
            st.write(f"Unique components: {df['component_type'].nunique()}")
        
        # Pivot data by file
        file_analysis = df.groupby('file').agg({
            'component_type': ['count', lambda x: list(x.unique())],
            'unique_name': 'count'
        }).round(2)
        
        # Flatten column names
        file_analysis.columns = ['component_count', 'component_types', 'unique_components']
        file_analysis = file_analysis.reset_index()
        
        # Define complexity rules
        snowflake_components = {
            'tMap', 'tSnowflakeCommit', 'tSnowflakeClose', 
            'tSnowflakeConnection', 'tSnowflakeInput', 'tSnowflakeOutput'
        }
        
        # Components that don't add complexity (utility/infrastructure components)
        utility_components = {
            'tDie', 'tSnowflakeConnection', 'tSnowflakeClose', 'tWarn'
        }
        
        high_complexity_components = {
            'tRunJob', 'tJavaRow', 'tJava', 'tPerlRow', 'tPython'
        }
        
        # Database-specific components for categorization
        db2_components = {
            'tDB2Input', 'tDB2Output', 'tDB2Connection', 'tDB2Close',
            'tDB2Commit', 'tDB2Rollback', 'tDB2Row', 'tDB2BulkExec',
            'tDB2TableList', 'tDB2SCD'
        }
        
        oracle_components = {
            'tOracleInput', 'tOracleOutput', 'tOracleConnection', 'tOracleClose',
            'tOracleCommit', 'tOracleRollback', 'tOracleRow', 'tOracleBulkExec',
            'tOracleTableList', 'tOracleSCD'
        }
        
        def categorize_size(count):
            if count < 10:
                return "Small"
            elif count < 20:
                return "Medium"
            elif count < 40:
                return "Large"
            else:
                return "XLarge"
        
        def calculate_complexity(component_types):
            components_set = set(component_types)
            
            # Remove utility components from complexity calculation
            complexity_relevant_components = components_set - utility_components
            
            # If no complexity-relevant components remain, it's low complexity
            if not complexity_relevant_components:
                return "Low"
            
            # Check if only snowflake components (excluding utility)
            if complexity_relevant_components.issubset(snowflake_components):
                return "Low"
            
            # Check for high complexity components
            if any(comp in high_complexity_components for comp in complexity_relevant_components):
                return "High"
            
            # Medium complexity for mixed or other components
            return "Medium"
        
        def categorize_database_usage(component_types):
            components_set = set(component_types)
            
            has_db2 = bool(components_set.intersection(db2_components))
            has_oracle = bool(components_set.intersection(oracle_components))
            has_snowflake = bool(components_set.intersection(snowflake_components))
            
            if has_db2 and has_oracle:
                return "DB2 + Oracle"
            elif has_db2:
                return "DB2 Only"
            elif has_oracle:
                return "Oracle Only"
            elif has_snowflake:
                return "Snowflake Only"
            else:
                return "Other/None"
        
        # Apply categorizations
        file_analysis['size_category'] = file_analysis['component_count'].apply(categorize_size)
        file_analysis['complexity'] = file_analysis['component_types'].apply(calculate_complexity)
        file_analysis['database_usage'] = file_analysis['component_types'].apply(categorize_database_usage)
        
        # Complexity scoring
        complexity_scores = {"Low": 1, "Medium": 3, "High": 5}
        size_multipliers = {"Small": 1, "Medium": 2, "Large": 3, "XLarge": 4}
        
        file_analysis['complexity_score'] = (
            file_analysis['complexity'].map(complexity_scores) * 
            file_analysis['size_category'].map(size_multipliers)
        )
        
        # Display analysis table
        st.subheader("📋 File Analysis Summary")
        
        display_df = file_analysis[['file', 'component_count', 'size_category', 'complexity', 'database_usage', 'complexity_score']].copy()
        display_df = display_df.sort_values('complexity_score', ascending=False)
        
        st.dataframe(
            display_df,
            use_container_width=True,
            column_config={
                "file": "File Name",
                "component_count": "Component Count",
                "size_category": "Size Category", 
                "complexity": "Complexity Level",
                "database_usage": "Database Usage",
                "complexity_score": "Complexity Score"
            }
        )
        
        # Visualizations
        st.subheader("📈 Analysis Visualizations")
        
        # Create tabs for different visualizations
        viz_tab1, viz_tab2, viz_tab3, viz_tab4 = st.tabs(["Complexity Distribution", "Database Usage", "Heatmap", "Top/Bottom Files"])
        
        with viz_tab1:
            col1, col2 = st.columns(2)
            
            with col1:
                # Complexity pie chart
                complexity_counts = file_analysis['complexity'].value_counts()
                fig_pie = px.pie(
                    values=complexity_counts.values,
                    names=complexity_counts.index,
                    title="Complexity Distribution",
                    color_discrete_map={
                        'Low': '#90EE90',
                        'Medium': '#FFD700', 
                        'High': '#FF6B6B'
                    }
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            
            with col2:
                # Size distribution
                size_counts = file_analysis['size_category'].value_counts()
                fig_size = px.bar(
                    x=size_counts.index,
                    y=size_counts.values,
                    title="Size Category Distribution",
                    color=size_counts.index,
                    color_discrete_map={
                        'Small': '#90EE90',
                        'Medium': '#87CEEB',
                        'Large': '#FFD700',
                        'XLarge': '#FF6B6B'
                    }
                )
                fig_size.update_layout(showlegend=False)
                st.plotly_chart(fig_size, use_container_width=True)
        
        with viz_tab2:
            # Database usage analysis
            database_counts = file_analysis['database_usage'].value_counts()
            
            # Define consistent color mapping for database usage
            db_color_map = {
                'Snowflake Only': '#87CEEB',
                'DB2 Only': '#FFB347',
                'Oracle Only': '#FF6B6B',
                'DB2 + Oracle': '#DDA0DD',
                'Other/None': '#D3D3D3'
            }
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Database usage pie chart
                fig_db_pie = px.pie(
                    values=database_counts.values,
                    names=database_counts.index,
                    title="Database Usage Distribution",
                    color_discrete_map=db_color_map
                )
                st.plotly_chart(fig_db_pie, use_container_width=True)
            
            with col2:
                # Database usage bar chart
                fig_db_bar = px.bar(
                    x=database_counts.index,
                    y=database_counts.values,
                    title="Database Usage Count",
                    color=database_counts.index,
                    color_discrete_map=db_color_map
                )
                fig_db_bar.update_layout(showlegend=False, xaxis_tickangle=-45)
                st.plotly_chart(fig_db_bar, use_container_width=True)
            
            # Database usage details table
            st.write("**Database Usage Breakdown:**")
            db_breakdown = file_analysis.groupby('database_usage').agg({
                'file': 'count',
                'complexity_score': 'mean'
            }).round(2)
            db_breakdown.columns = ['File Count', 'Avg Complexity Score']
            st.dataframe(db_breakdown, use_container_width=True)
        
        with viz_tab3:
            # Heatmap of complexity by size and complexity level
            heatmap_data = file_analysis.groupby(['size_category', 'complexity']).size().unstack(fill_value=0)
            
            fig_heatmap = px.imshow(
                heatmap_data.values,
                labels=dict(x="Complexity Level", y="Size Category", color="Number of Files"),
                x=heatmap_data.columns,
                y=heatmap_data.index,
                title="Files Distribution: Size vs Complexity",
                color_continuous_scale="Blues",
                text_auto=True
            )
            st.plotly_chart(fig_heatmap, use_container_width=True)
        
        with viz_tab4:
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**🔥 Top 20 Most Complex Jobs**")
                top_complex = display_df.head(20)
                st.dataframe(
                    top_complex[['file', 'complexity_score', 'complexity', 'size_category', 'database_usage']],
                    use_container_width=True
                )
            
            with col2:
                st.write("**✅ Bottom 20 Easiest Jobs**")
                bottom_easy = display_df.tail(20)
                st.dataframe(
                    bottom_easy[['file', 'complexity_score', 'complexity', 'size_category', 'database_usage']],
                    use_container_width=True
                )
        
        # Effort Calculator
        st.subheader("⏱️ Migration Effort Calculator")
        
        calc_col1, calc_col2, calc_col3 = st.columns(3)
        
        with calc_col1:
            st.write("**Baseline Hours per Size Category:**")
            small_hours = st.number_input("Small files (hours)", value=8.0, min_value=0.1, step=0.5)
            medium_hours = st.number_input("Medium files (hours)", value=16.0, min_value=0.1, step=0.5)
            large_hours = st.number_input("Large files (hours)", value=32.0, min_value=0.1, step=0.5)
            xlarge_hours = st.number_input("XLarge files (hours)", value=64.0, min_value=0.1, step=0.5)
        
        with calc_col2:
            st.write("**Complexity Multipliers:**")
            low_multiplier = st.number_input("Low complexity multiplier", value=0.8, min_value=0.1, step=0.1)
            medium_multiplier = st.number_input("Medium complexity multiplier", value=1.0, min_value=0.1, step=0.1)
            high_multiplier = st.number_input("High complexity multiplier", value=1.5, min_value=0.1, step=0.1)
        
        with calc_col3:
            st.write("**Resources:**")
            num_resources = st.number_input("Number of developers", value=3, min_value=1, step=1)
            hours_per_day = st.number_input("Working hours per day", value=8, min_value=1, step=1)
            days_per_week = st.number_input("Working days per week", value=5, min_value=1, step=1)
        
        # Calculate effort
        size_hours_map = {
            "Small": small_hours,
            "Medium": medium_hours, 
            "Large": large_hours,
            "XLarge": xlarge_hours
        }
        
        complexity_multiplier_map = {
            "Low": low_multiplier,
            "Medium": medium_multiplier,
            "High": high_multiplier
        }
        
        file_analysis['estimated_hours'] = (
            file_analysis['size_category'].map(size_hours_map) * 
            file_analysis['complexity'].map(complexity_multiplier_map)
        )
        
        total_hours = file_analysis['estimated_hours'].sum()
        total_days = total_hours / (num_resources * hours_per_day)
        total_weeks = total_days / days_per_week
        
        # Display effort results
        st.subheader("📊 Effort Estimation Results")
        
        result_col1, result_col2, result_col3, result_col4 = st.columns(4)
        
        with result_col1:
            st.metric("Total Hours", f"{total_hours:.1f}")
        
        with result_col2:
            st.metric("Total Days", f"{total_days:.1f}")
        
        with result_col3:
            st.metric("Total Weeks", f"{total_weeks:.1f}")
        
        with result_col4:
            st.metric("Total Files", len(file_analysis))
        
        # Effort breakdown by category
        st.write("**Effort Breakdown by Category:**")
        effort_breakdown = file_analysis.groupby(['size_category', 'complexity'])['estimated_hours'].sum().unstack(fill_value=0)
        
        fig_effort = px.bar(
            effort_breakdown,
            title="Estimated Hours by Size and Complexity",
            labels={'value': 'Hours', 'index': 'Size Category'},
            color_discrete_map={
                'Low': '#90EE90',
                'Medium': '#FFD700',
                'High': '#FF6B6B'
            }
        )
        st.plotly_chart(fig_effort, use_container_width=True)
        
        # Download results
        st.subheader("💾 Download Results")
        
        # Prepare download data
        download_df = file_analysis[['file', 'component_count', 'size_category', 'complexity', 'database_usage', 'complexity_score', 'estimated_hours']].copy()
        
        csv_buffer = StringIO()
        download_df.to_csv(csv_buffer, index=False)
        csv_data = csv_buffer.getvalue()
        
        st.download_button(
            label="📥 Download Analysis Results (CSV)",
            data=csv_data,
            file_name="talend_migration_analysis.csv",
            mime="text/csv"
        )
        
    except Exception as e:
        st.error(f"Error processing file: {str(e)}")
        st.info("Please ensure your CSV file has the correct format with columns: index, file, component_type, unique_name")

else:
    st.info("👆 Please upload a CSV file to begin analysis")
    
    # Show example data format
    st.subheader("📝 Expected CSV Format")
    example_data = {
        'index': [1, 2, 3, 4, 5],
        'file': ['job1.kjb', 'job1.kjb', 'job2.kjb', 'job2.kjb', 'job3.kjb'],
        'component_type': ['tMap', 'tSnowflakeOutput', 'tRunJob', 'tMap', 'tSnowflakeInput'],
        'unique_name': ['tMap_1', 'tSnowflakeOutput_1', 'tRunJob_1', 'tMap_2', 'tSnowflakeInput_1']
    }
    example_df = pd.DataFrame(example_data)
    st.dataframe(example_df, use_container_width=True)

# Footer
st.markdown("---")
st.markdown("Built with ❤️ using Streamlit for Talend Migration Analysis")
