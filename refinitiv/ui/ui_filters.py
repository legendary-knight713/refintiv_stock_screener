import streamlit as st
import pandas as pd
import os
import json
from refinitiv.ui.ui_components import render_kpi_multiselect

def render_filters(all_instruments_df, all_countries_df, all_markets_df, all_sectors_df, all_branches_df):
    # Use the data provided by the API (mock data for now)
    df_countries = all_countries_df
    df_markets = all_markets_df
    df_sectors = all_sectors_df
    df_branches = all_branches_df
    
    # Countries
    if 'name' in df_countries.columns:
        df_countries = df_countries.sort_values(by='name')
    country_options = list(df_countries['name'])
    
    # For mock data, create simple mapping
    if all_instruments_df is None or all_instruments_df.empty:
        country_id_name_map = {row['name']: row['id'] for _, row in df_countries.iterrows()}
        st.info("ℹ️ Using mock instruments data for UI demonstration")
    else:
        available_country_ids = set(pd.Series(all_instruments_df['countryId']).tolist())
        country_id_name_map = {row['name']: row['id'] for _, row in df_countries.iterrows() if row['id'] in available_country_ids}

    selected_countries = st.multiselect(
        'Countries',
        options=country_options,
        format_func=lambda x: x,
        placeholder='--- Choose countries ---',
        key='selected_countries'
    )

    # Markets
    if not isinstance(df_markets, pd.DataFrame):
        df_markets = pd.DataFrame(df_markets)
    selected_markets = set()
    if selected_countries:
        for country_id in [country_id_name_map[c] for c in selected_countries if c in country_id_name_map]:
            country_name = df_countries[df_countries['id'] == country_id]['name'].iloc[0] if isinstance(df_countries, pd.DataFrame) else df_countries[df_countries['id'] == country_id]['name'][0]
            df_markets_country = df_markets[df_markets['countryId'] == country_id]
            if isinstance(df_markets_country, pd.DataFrame) and 'name' in df_markets_country.columns:
                df_markets_country = df_markets_country.sort_values(by='name')
            
            # For mock data, show all markets for the country
            if all_instruments_df is None or all_instruments_df.empty:
                market_options = [row['name'] for _, row in df_markets_country.iterrows()]
                market_ids = [row['id'] for _, row in df_markets_country.iterrows()]
            else:
                available_market_ids = set(pd.Series(all_instruments_df[all_instruments_df['countryId'] == country_id]['marketId']).tolist())
                market_options = [row['name'] for _, row in df_markets_country.iterrows() if row['id'] in available_market_ids]
                market_ids = [row['id'] for _, row in df_markets_country.iterrows() if row['id'] in available_market_ids]
            
            market_id_name_map = dict(zip(market_options, market_ids))
            st.write(f"Markets in {country_name}")
            select_all_key = f"select_all_markets_{country_id}"
            if st.button("Select All", key=select_all_key):
                for m_id in market_ids:
                    st.session_state[f"market_{country_id}_{m_id}"] = True
            for i in range(0, len(market_options), 3):
                cols = st.columns(3)
                for j, m_name in enumerate(market_options[i:i+3]):
                    m_id = market_id_name_map[m_name]
                    key = f"market_{country_id}_{m_id}"
                    if key not in st.session_state:
                        st.session_state[key] = False
                    cb = cols[j].checkbox(str(m_name), key=key)
                    if st.session_state[key]:
                        selected_markets.add(m_id)
                    else:
                        selected_markets.discard(m_id)

    # Sectors
    if isinstance(df_sectors, pd.DataFrame) and 'name' in df_sectors.columns:
        df_sectors = df_sectors.sort_values(by='name')
    sector_options = list(df_sectors['name'])
    
    # For mock data, create simple mapping
    if all_instruments_df is None or all_instruments_df.empty:
        sector_id_name_map = {row['name']: row['id'] for _, row in df_sectors.iterrows()}
    else:
        available_sector_ids = set(pd.Series(all_instruments_df['sectorId']).tolist())
        sector_id_name_map = {row['name']: row['id'] for _, row in df_sectors.iterrows() if row['id'] in available_sector_ids}
    
    selected_sectors = st.multiselect(
        'Sectors', 
        options=sector_options, 
        key='selected_sectors', 
        placeholder='--- Choose sectors ---')

    # Industries
    selected_industries = set()
    if selected_sectors:
        if 'name' in df_branches.columns:
            df_branches = df_branches.sort_values(by='name')
        for sector_id in [sector_id_name_map[s] for s in selected_sectors if s in sector_id_name_map]:
            sector_name = df_sectors[df_sectors['id'] == sector_id]['name'].iloc[0]
            
            if all_instruments_df is None or all_instruments_df.empty:
                sector_branches = df_branches[df_branches['sectorId'] == sector_id]
                industry_options = [row['name'] for _, row in sector_branches.iterrows()]
                industry_ids = [row['id'] for _, row in sector_branches.iterrows()]
            else:
                sector_data = pd.DataFrame(all_instruments_df[all_instruments_df['sectorId'] == sector_id])
                unique_branch_ids = set(pd.Series(sector_data['branchId']).dropna().unique())
                industry_options = []
                industry_ids = []
                for branch_id in unique_branch_ids:
                    if pd.notna(branch_id):
                        branch_info = df_branches[df_branches['id'] == branch_id]
                        if not branch_info.empty:
                            industry_name = branch_info.iloc[0]['name']
                            industry_id = int(branch_id)
                            industry_options.append(industry_name)
                            industry_ids.append(industry_id)
            
            industry_id_name_map = dict(zip(industry_options, industry_ids))
            st.write(f"Industries in {sector_name}")
            select_all_ind_key = f"select_all_industries_{sector_id}"
            if st.button("Select All", key=select_all_ind_key):
                for i_id in industry_ids:
                    st.session_state[f"industry_{sector_id}_{i_id}"] = True
            for i_id in industry_ids:
                key = f"industry_{sector_id}_{i_id}"
                if key not in st.session_state:
                    st.session_state[key] = False
                cb = st.checkbox(str(industry_id_name_map[i_id]), key=key)
                if st.session_state[key]:
                    selected_industries.add(i_id)
                else:
                    selected_industries.discard(i_id)

    # Stock Indice Combo Box
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(BASE_DIR, '../data/stock_indices.json')
    with open(json_path, 'r') as f:
        stock_indice_options = json.load(f)
    stock_indice_options = ['--- Choose stock indice ---'] + stock_indice_options
    selected_stock_indice = st.selectbox(
        'Select stock indice', 
        stock_indice_options, 
        key='stock_indice',
        index=0
    )

    return selected_countries, selected_markets, selected_sectors, selected_industries, selected_stock_indice, country_id_name_map, sector_id_name_map

def render_stocks(all_instruments_df):
    st.subheader(f"Stocks ({len(all_instruments_df)})")
    
    if all_instruments_df is not None and not all_instruments_df.empty:
        # Select relevant columns
        df_display = all_instruments_df[['name', 'ticker']].reset_index(drop=True)
        df_display.index += 1  # Make index start at 1

        st.dataframe(df_display)
    else:
        st.info("No stock data available.")

    
def render_kpi_filter_groups(render_filter_group, kpi_options):
    st.subheader('KPI Filter Groups')
    col1, col2, col3 = st.columns([6, 2, 2])
    with col1:
        st.markdown("""
        <style>
        div[data-testid="stMultiSelect"] > label {
            display: none !important;
            height: 0px !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        </style>
    """, unsafe_allow_html=True)
        selected_kpis = render_kpi_multiselect(kpi_options)
    with col2:
        st.markdown(
            """
            <div style='display:flex; flex-direction:column; justify-content:flex-end;'>
            </div>
            """,
            unsafe_allow_html=True
        )
        add_group_clicked = st.button('Add Group', key='add_group')
    with col3:
        st.markdown(
            """
            <div style='display:flex; flex-direction:column; justify-content:flex-end;'>
            </div>
            """,
            unsafe_allow_html=True
        )
        clear_groups_clicked = st.button('Clear All Groups', key='clear_groups')

    if add_group_clicked:
        st.session_state['filter_groups'].append({
            'id': f'group_{len(st.session_state["filter_groups"])}',
            'filters': [],
            'operator': 'AND',
            'filter_settings': {}
        })
    if clear_groups_clicked:
        st.session_state['filter_groups'] = []
        from refinitiv.ui.ui_components import reset_results
        reset_results()
    if len(st.session_state['filter_groups']) > 1:
        st.session_state['group_relationships'] = st.selectbox(
            'Relationship between groups',
            ['AND', 'OR'],
            index=['AND', 'OR'].index(st.session_state['group_relationships']),
            key='group_relationships_select'
        )
    for group_idx, group in enumerate(st.session_state['filter_groups']):
        render_filter_group(group_idx, group)
    # Logic preview
    def generate_logic_preview():
        group_expressions = []
        for group in st.session_state['filter_groups']:
            kpi_expressions = []
            for kpi_name, kpi_settings in group.get('filter_settings', {}).items():
                methods = kpi_settings.get('methods', [])
                if len(methods) == 1:
                    method_config = methods[0]
                    method_type = method_config.get('type', 'Absolute')
                    if method_type == 'Absolute':
                        op = method_config.get('operator_abs', '>')
                        val = method_config.get('value', 0.0)
                        kpi_expressions.append(f"{kpi_name} {op} {val}")
                    elif method_type == 'Relative':
                        op = method_config.get('rel_operator', '>=')
                        val = method_config.get('rel_value', 0.0)
                        kpi_expressions.append(f"{kpi_name} {op} {val}%")
                    elif method_type == 'Direction':
                        direction = method_config.get('direction', 'positive')
                        kpi_expressions.append(f"{kpi_name} Direction: {direction}")
                    elif method_type == 'Trend':
                        trend_type = method_config.get('trend_type', 'Positive')
                        kpi_expressions.append(f"{kpi_name} Trend: {trend_type}")
                else:
                    method_expressions = []
                    for method_config in methods:
                        method_type = method_config.get('type', 'Absolute')
                        if method_type == 'Absolute':
                            op = method_config.get('operator_abs', '>')
                            val = method_config.get('value', 0.0)
                            method_expressions.append(f"{kpi_name} {op} {val}")
                        elif method_type == 'Relative':
                            op = method_config.get('rel_operator', '>=')
                            val = method_config.get('rel_value', 0.0)
                            method_expressions.append(f"{kpi_name} {op} {val}%")
                        elif method_type == 'Direction':
                            direction = method_config.get('direction', 'positive')
                            method_expressions.append(f"{kpi_name} Direction: {direction}")
                        elif method_type == 'Trend':
                            trend_type = method_config.get('trend_type', 'Positive')
                            method_expressions.append(f"{kpi_name} Trend: {trend_type}")
                    method_operator = kpi_settings.get('method_operator', 'AND')
                    kpi_expressions.append(f" {method_operator} ".join(method_expressions))
            if kpi_expressions:
                if len(kpi_expressions) == 1:
                    group_expr = f"({kpi_expressions[0]})"
                else:
                    joiner = f" {group['operator']} "
                    group_expr = f"({joiner.join(kpi_expressions)})"
                group_expressions.append(group_expr)
        if group_expressions:
            if len(group_expressions) == 1:
                return group_expressions[0]
            else:
                rel = st.session_state.get('group_relationships', 'AND')
                return f" {rel} ".join(group_expressions)
        return ''
    st.session_state['logic_preview'] = generate_logic_preview()
    st.info(f"**Filter Formula:** {st.session_state['logic_preview']}")
