import streamlit as st
import os
import json
from refinitiv.api.refinitiv_api import RefinitivAPI
from refinitiv.ui.ui_layout import setup_page, apply_custom_css
from refinitiv.ui.ui_state import initialize_session_state, kpi_filter_validate, reset_pagination, pagination_controls
from refinitiv.ui.ui_constants import PAGE_SIZE
from refinitiv.ui.ui_data import fetch
from refinitiv.ui.ui_filters import render_kpi_filter_groups, render_stocks
from refinitiv.ui.ui_results import show_results
from refinitiv.ui.ui_components import render_filter_group
from refinitiv.filters.kpi_logic import (
    convert_groups_to_old_format,
    build_group_logic_tree,
    validate_logic_tree,
    fetch_kpi_data_for_calculation,
)
from refinitiv.ui.ui_helpers import fetch_yearly_kpi_history, test_kpi_quarterly_availability
from refinitiv.ui.ui_presets import render_preset_management, apply_pending_preset

def main():
    setup_page()
    apply_custom_css()
    initialize_session_state()
    
    # Apply any pending preset before rendering widgets
    apply_pending_preset()

    api = RefinitivAPI()
    # Note: BorsdataClient is not needed for Refinitiv API
    (all_instruments_df, all_countries_df, all_markets_df, all_sectors_df, all_branches_df) = fetch(api)

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    PACKAGE_ROOT = os.path.dirname(BASE_DIR)
    kpi_json_path = os.path.join(PACKAGE_ROOT, 'data', 'kpi_options.json')
    with open(kpi_json_path, 'r') as f:
        kpi_json = json.load(f)
    kpi_labels = [item['label'] for item in kpi_json]  # Use 'label' for display
    
    render_stocks(all_instruments_df)    
    render_kpi_filter_groups(render_filter_group, kpi_labels)
    kpi_filter_validate()

    # Add preset management functionality
    render_preset_management()

    fetch_clicked = st.button('Fetch Results', key='fetch_results')

    if fetch_clicked:
        reset_pagination()
        st.session_state['kpi_filters'] = convert_groups_to_old_format(st.session_state['filter_groups'])
        if st.session_state['filter_groups']:
            group_relationships = st.session_state.get('group_relationships', 'AND')
            st.session_state['kpi_logic_tree'] = build_group_logic_tree(
                st.session_state['filter_groups'], 
                st.session_state['kpi_filters'],
                group_relationships
            )
        if st.session_state['kpi_filters'] and 'kpi_logic_tree' in st.session_state:
            stock_ids = list(all_instruments_df['ticker'])
            # No KPI metadata needed for Refinitiv - skip quarterly availability test
            problematic_kpis = []
            if problematic_kpis:
                st.warning(f"The following KPIs do not support quarterly data: {', '.join(problematic_kpis)}. Please change their frequency to 'Yearly' or remove them from your filter.")
                st.stop()
            kpi_filter_settings = {}
            for idx, kf in enumerate(st.session_state['kpi_filters']):
                kpi_name = kf['kpi']
                kpi_value = next((item['value'] for item in kpi_json if item['label'] == kpi_name), None)
                kpi_filter_settings[idx] = {
                    'abs_enabled': kf['method'] == 'Absolute',
                    'abs_operator': kf.get('operator'),
                    'abs_value': kf.get('value'),
                    'last_n': kf.get('last_n') if kf.get('duration_type', 'Last N Quarters') == 'Last N Quarters' else None,
                    'rel_enabled': kf['method'] == 'Relative',
                    'rel_value': kf.get('rel_value'),
                    'trend_enabled': kf['method'] == 'Trend',
                    'trend_type': kf.get('trend_type'),
                    'trend_n': kf.get('trend_n'),
                    'trend_m': kf.get('trend_m'),
                    'direction_enabled': kf['method'] == 'Direction',
                    'direction': kf.get('direction', 'either'),
                    'kpi_name': kpi_value,
                    'data_frequency': kf.get('data_frequency', 'Quarterly'),
                    'duration_type': kf.get('duration_type', 'Last N Quarters'),
                    'start_date': kf.get('start_date'),
                    'end_date': kf.get('end_date'),
                }
            with st.spinner('Processing KPI data...'):
                try:
                    all_kpi_data = fetch_kpi_data_for_calculation(stock_ids, st=st, kpi_filter_settings=kpi_filter_settings)
                    
                except Exception as e:
                    st.error(f"Error fetching KPI data: {e}")
                    st.stop()
            
            st.session_state['kpi_data'] = all_kpi_data
            tree = st.session_state['kpi_logic_tree']
            if isinstance(tree, int):
                tree = {'type': 'AND', 'children': [tree]}
            if not (isinstance(tree, dict) and 'children' in tree):
                st.warning("Invalid KPI logic tree. Skipping KPI filtering.")
                final_stock_ids = list(all_instruments_df['ticker'])
            else:
                if not validate_logic_tree(tree, kpi_filter_settings):
                    st.error("Logic tree validation failed. Some filter indices are missing. Please check your filter configuration.")
                    st.stop()
                final_stock_ids = []
                passed_count = 0
                total_stocks = len(all_instruments_df['ticker'])
                progress_bar = st.progress(0)
                status_text = st.empty()
                for i, stock_id in enumerate(all_instruments_df['ticker']):
                    try:
                        from refinitiv.filters.filter_engine import evaluate_filter_tree
                        stock_kpis = {kpi_name: kpi_df[kpi_df['insId'] == stock_id] for kpi_name, kpi_df in all_kpi_data.items()}
                        result = evaluate_filter_tree(
                            tree,
                            kpi_filter_settings,
                            stock_kpis
                        )
                        if result:
                            final_stock_ids.append(stock_id)
                            passed_count += 1
                        if i % 100 == 0 or i == total_stocks - 1:
                            progress = (i + 1) / total_stocks
                            progress_bar.progress(progress)
                            status_text.text(f"Filtering stocks: {i + 1}/{total_stocks} ({passed_count} passed)")
                    except Exception as e:
                        st.error(f"Error evaluating stock {stock_id}: {e}")
                        continue
                progress_bar.empty()
                status_text.empty()
            all_instruments_df = all_instruments_df[all_instruments_df['ticker'].isin(list(final_stock_ids))]
            st.session_state['kpi_data'] = all_kpi_data
        st.session_state['filtered_instruments'] = all_instruments_df
        st.session_state['results_ready'] = True
    if st.session_state.get('results_ready') and st.session_state.get('filtered_instruments') is not None:
        all_instruments_df = st.session_state['filtered_instruments']
        show_results(
            all_instruments_df,
            kpi_labels,
            kpi_json,
            all_markets_df,
            all_sectors_df,
            all_countries_df,
            all_branches_df,
            PAGE_SIZE,
            st.session_state['current_page'],
            pagination_controls,
            api,
        )
    elif fetch_clicked:
        st.write("\n_No country or market selected. Please choose at least one country and one market.")

main()
