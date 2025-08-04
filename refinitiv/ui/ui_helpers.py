# ui_helpers.py
import pandas as pd
import streamlit as st

def fetch_yearly_kpi_history(api, stock_ids, kpi_id):
    """Fetch yearly KPI history for each stock and return a DataFrame with columns: insId, year, kpiValue"""
    all_rows = []
    for ins_id in stock_ids:
        try:
            df = api.get_kpi_history(ins_id, kpi_id, report_type='year', price_type='mean')
            if df is not None and not df.empty:
                for idx, row in df.iterrows():
                    if isinstance(idx, tuple):
                        year = idx[0]
                    else:
                        year = idx
                    kpi_value = row.get('kpiValue') or row.get('value') or row.get('v')
                    if year is not None and kpi_value is not None:
                        try:
                            year_int = int(year) if year is not None else None
                            ins_id_int = int(ins_id) if ins_id is not None else None
                            if year_int is not None and ins_id_int is not None:
                                all_rows.append({
                                    'insId': ins_id_int,
                                    'year': year_int,
                                    'kpiValue': kpi_value
                                })
                        except (ValueError, TypeError):
                            continue
        except Exception as e:
            continue
    df_result = pd.DataFrame(all_rows)
    if not df_result.empty:
        df_result['insId'] = df_result['insId'].astype(int)
        df_result['year'] = df_result['year'].astype(int)
    return df_result

def test_kpi_quarterly_availability(api, kpi_filters, stock_ids, df_kpis, kpi_short_to_refinitiv):
    # For Refinitiv DSWS, we don't need to test quarterly availability
    # since we use direct field codes (PL, ROIC, etc.)
    return []

def create_method_config(method_type, kpi_name, method_count):
    """Create a new method configuration with None defaults"""
    return {
        'type': method_type,
        'id': f'{kpi_name}_{method_type}_{method_count}',
        # Initialize with None/empty values - will be set when user interacts
        'operator_abs': None,
        'value': None,
        'duration_type': None,
        'last_n': None,
        'start_date': '',
        'end_date': '',
        'rel_operator': None,
        'rel_value': None,
        'rel_period': None,
        'direction': None,
        'trend_type': None,
        'trend_n': None,
        'trend_m': None,
        'data_frequency': 'Quarterly'
    }