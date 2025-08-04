import streamlit as st
import pandas as pd
import datetime
from refinitiv.ui.ui_helpers import fetch_yearly_kpi_history
from refinitiv.filters.filter_engine import filter_data_by_time_range

def show_results(
    filtered_instruments,
    kpi_options,  # <-- Use this instead of kpi_short_to_refinitiv
    all_markets_df,
    all_sectors_df,
    all_countries_df,
    all_branches_df,
    PAGE_SIZE,
    current_page,
    pagination_controls,
    api,
):
    st.subheader('Sorting Options')
    sorter_options = ['None', 'CAGR', 'Market', 'Ticker']
    if 'sorter' not in st.session_state:
        st.session_state['sorter'] = 'None'
    st.session_state['sorter'] = st.selectbox(
        'Sort Option',
        sorter_options,
        index=sorter_options.index(st.session_state['sorter']) if st.session_state['sorter'] in sorter_options else 0,
        key='sorter_select'
    )

    def show_cagr_options(kpi_options):
        cagr_kpi = st.selectbox('CAGR KPI', [''] + kpi_options, key='cagr_kpi_stable')
        years = [''] + list(range(1995, datetime.datetime.now().year + 1))
        start_year = st.selectbox('CAGR Start Year', years, key='cagr_start_year_stable')
        end_year = st.selectbox('CAGR End Year', years, key='cagr_end_year_stable')
        calculate_cagr_clicked = st.button('Calculate CAGR', key='calculate_cagr_btn_stable')
        return cagr_kpi, start_year, end_year, calculate_cagr_clicked

    def calculate_cagr(start, end, n_years):
        try:
            if start is None or end is None or n_years <= 0:
                return None
            if start == 0:
                return None
            if (start < 0 and end > 0) or (start > 0 and end < 0):
                return None
            result = (end / start) ** (1 / n_years) - 1
            if isinstance(result, complex):
                return None
            return result
        except Exception:
            return None

    sorter = st.session_state['sorter']
    cagr_kpi, cagr_start_year, cagr_end_year, calculate_cagr_clicked = None, None, None, False
    if sorter == 'CAGR':
        st.subheader('CAGR Calculation Settings')
        cagr_kpi, cagr_start_year, cagr_end_year, calculate_cagr_clicked = show_cagr_options(kpi_options)

    total_results = len(filtered_instruments)
    total_pages = max(1, (total_results + PAGE_SIZE - 1) // PAGE_SIZE)
    if current_page >= total_pages:
        st.session_state['current_page'] = total_pages - 1
        st.rerun()
    start = current_page * PAGE_SIZE
    end = start + PAGE_SIZE
    paginated_instruments = filtered_instruments.iloc[start:end].copy()

    sort_columns = []
    ascending = []
    cagr_col = None
    market_id_to_name = {row['id']: row['name'] for _, row in all_markets_df.iterrows()}
    if 'marketId' in paginated_instruments.columns:
        paginated_instruments['market'] = paginated_instruments['marketId'].map(market_id_to_name)

    if sorter == 'CAGR':
        if calculate_cagr_clicked and cagr_kpi and cagr_start_year and cagr_end_year:
            st.info(f"Calculating CAGR for {cagr_kpi} from {cagr_start_year} to {cagr_end_year}...")
            cagr_kpi_refinitiv = cagr_kpi 
            if cagr_kpi_refinitiv is not None:
                n_years = int(cagr_end_year) - int(cagr_start_year)
                cagr_col = f'CAGR_{cagr_kpi}_{cagr_start_year}_{cagr_end_year}'
                if n_years > 0:
                    id_col = None
                    for candidate in ['insId', 'id', 'instrumentId']:
                        if candidate in paginated_instruments.columns:
                            id_col = candidate
                            break
                    page_stock_ids = list(paginated_instruments['ticker'])
                    kpi_id = cagr_kpi  

                    if kpi_id is None:
                        st.warning(f"Could not find KPI ID for {cagr_kpi} (mapped: {cagr_kpi_refinitiv})")
                    else:
                        rows = []
                        for stock in page_stock_ids:
                            # update needed for start and end date as -nY format
                            cur_year = datetime.datetime.now().year
                            start_date = f"-{cur_year - int(cagr_start_year)}Y"
                            end_date = f"-{cur_year - int(cagr_end_year)}Y"
                            try:
                                data = api.fetch_datastream_timeseries(instrument=stock, datatypes=[cagr_kpi], start=start_date, end=end_date, frequency='Y', kind=1)
                                for kpi, records in data.items():
                                    for date, value in records:
                                        if isinstance(value, (int, float)):
                                            rows.append({'insId': stock, 'year': date, 'kpiValue': value})
                            
                            except:
                                st.warning(f"No data available for KPI '{cagr_kpi}' for stock '{stock}'")
                                continue      
                        kpi_df = pd.DataFrame(rows)
                        kpi_lookup = {}
                        if kpi_df is not None and not kpi_df.empty:
                            for _, row in kpi_df.iterrows():
                                stock = row.get('insId')
                                year = row.get('year').split('.')[0]
                                value = row.get('kpiValue')
                                if stock is not None and year is not None and value is not None:
                                    try:
                                        kpi_lookup[(stock, year)] = float(value)
                                    except Exception as e:
                                        continue
                        cagr_values = []
                        for idx, row in paginated_instruments.iterrows():
                            stock = row['ticker']
                            try:
                                start_val = kpi_lookup.get((stock, str(cagr_start_year)))
                                end_val = kpi_lookup.get((stock, str(cagr_end_year)))
                            except Exception as e:
                                start_val = None
                                end_val = None
                            cagr = calculate_cagr(start_val, end_val, n_years)
                            cagr_values.append(cagr)
                        paginated_instruments[cagr_col] = cagr_values
                        sort_columns.append(cagr_col)
                        ascending.append(False)
    if sorter == 'Market':
        market_cap_col = None
        for col in ['market', 'Market']:
            if col in paginated_instruments.columns:
                market_cap_col = col
                break
        if market_cap_col:
            sort_columns.append(market_cap_col)
            ascending.append(False)
    if sorter == 'Ticker':
        ticker_col = None
        for col in ['ticker', 'Ticker', 'symbol', 'Symbol', 'ticker_symbol']:
            if col in paginated_instruments.columns:
                ticker_col = col
                break
        if ticker_col:
            sort_columns.append(ticker_col)
            ascending.append(True)
        else:
            st.warning("Ticker column not found. Available columns: " + ", ".join(paginated_instruments.columns))
    if sort_columns:
        paginated_instruments = paginated_instruments.sort_values(by=sort_columns, ascending=ascending, na_position='last')

    # Prepare columns to display in the table
    display_columns = ['name', 'ticker']
    
    # Show market column if sorting by Market
    if sorter == 'Market' and 'market' in paginated_instruments.columns:
        display_columns.append('market')

    # Add KPI filter value columns if KPI filters were applied and data is available
    if st.session_state.get('kpi_filters') and len(st.session_state['kpi_filters']) > 0:
        # Get KPI data for current page stocks
        id_col = None
        for candidate in ['insId', 'id', 'instrumentId']:
            if candidate in paginated_instruments.columns:
                id_col = candidate
                break
        
        # Only add KPI columns if we have the KPI data available
        if id_col and 'kpi_data' in st.session_state:
            # Add a column for each KPI filter showing the actual values
            for kf in st.session_state['kpi_filters']:
                kpi_name = kf['kpi']
                duration_type = kf.get('duration_type', 'Last N Quarters')
                operator = kf.get('operator', '')
                value = kf.get('value', '')
                last_n = kf.get('last_n', 1)
                method = kf.get('method', '')

                # Build duration string
                if duration_type == 'Custom Range' and kf.get('start_date') and kf.get('end_date'):
                    duration_str = f"({kf['start_date']} → {kf['end_date']})"
                else:
                    duration_str = f"(last {last_n} quarters)"

                # Build method-specific header
                if method == 'Absolute':
                    operator = kf.get('operator', '')
                    value = kf.get('value', '')
                    column_header = f"{kpi_name} {operator} {value} {duration_str}"
                elif method == 'Relative':
                    rel_operator = kf.get('rel_operator', '')
                    rel_value = kf.get('rel_value', '')
                    rel_mode = kf.get('rel_mode', 'Year-over-Year (YoY)')
                    # Use shorter version for display
                    if rel_mode == 'Quarter-over-Quarter (QoQ)':
                        display_mode = 'QoQ'
                    elif rel_mode == 'Year-over-Year (YoY)':
                        display_mode = 'YoY'
                    else:
                        display_mode = rel_mode
                    column_header = f"{kpi_name} {display_mode} {rel_operator} {rel_value}% {duration_str}"
                elif method == 'Direction':
                    direction = kf.get('direction', 'either')
                    column_header = f"{kpi_name} Direction: {direction} {duration_str}"
                else:
                    column_header = f"{kpi_name} {duration_str}"
                
                # Get actual KPI values for each stock
                kpi_values = []
                for _, stock in paginated_instruments.iterrows():
                    stock_id = stock['ticker']
                    kpi_df = st.session_state['kpi_data'].get(kpi_name, pd.DataFrame())
                    # Filter for this stock
                    stock_kpi_df = kpi_df[kpi_df['insId'] == stock_id] if not kpi_df.empty else pd.DataFrame()
                    if not stock_kpi_df.empty:
                        if not stock_kpi_df.empty and 'kpiValue' in stock_kpi_df.columns:
                            values = stock_kpi_df['kpiValue'].tolist()
                        else:
                            values = []
                        # Format values based on method type
                        if method == 'Trend':
                            values = values[-last_n:]
                            if len(values) > 1:
                                values_str = ' → '.join([f"{v:.4f}" for v in values])
                            else:
                                values_str = f"{values[0]:.4f}" if values else 'N/A'
                        elif method == 'Relative':
                            if len(values) > 1:
                                values_str = ' → '.join([f"{v:.4f}" for v in values])
                            else:
                                values_str = f"{values[0]:.4f}" if values else 'N/A'
                        else:
                            values_str = ', '.join([f"{v:.4f}" for v in values])
                        kpi_values.append(values_str)
                    else:
                        kpi_values.append('N/A')
                
                # Add the column to the DataFrame
                paginated_instruments[column_header] = kpi_values
                display_columns.append(column_header)
    
    if cagr_col is not None and cagr_col in paginated_instruments.columns:
        display_columns.append(cagr_col)
    # Only include columns that exist in the DataFrame
    display_columns = [col for col in display_columns if col in paginated_instruments.columns]

    st.write(f"Showing {len(paginated_instruments)} stocks for selected countries")
    # Show the results table
    paginated_instruments_display = paginated_instruments.copy().reset_index(drop=True)
    st.dataframe(paginated_instruments_display[display_columns])

    if total_pages > 1:
        pagination_controls(st.session_state['current_page'], total_pages, total_results)

    # --- Historical Price Export Date Range Selection ---
    st.markdown('---')
    st.subheader('Export Historical Stock Prices')
    today = datetime.date.today()
    default_from = today.replace(year=today.year-20) if today.year > 20 else today
    from_date = st.date_input('From date', value=default_from, key='price_history_from_date', max_value=today)
    to_date = st.date_input('To date (optional)', value=today, key='price_history_to_date', max_value=today)
    # If user selects a future to_date, reset to today
    if to_date > today:
        to_date = today

    # --- Date range validation ---
    valid_date_range = True
    if from_date and to_date and from_date > to_date:
        st.warning('From date cannot be after To date.')
        valid_date_range = False
    export_to_date = to_date if to_date and from_date <= to_date else today
    export_from_date = from_date
    # The export button and logic will use export_from_date and export_to_date
    # Build mapping dictionaries for export
    sector_id_to_name = {row['id']: row['name'] for _, row in all_sectors_df.iterrows()}
    market_id_to_name = {row['id']: row['name'] for _, row in all_markets_df.iterrows()}
    country_id_to_name = {row['id']: row['name'] for _, row in all_countries_df.iterrows()}
    branch_id_to_name = {row['id']: row['name'] for _, row in all_branches_df.iterrows()}

    # --- Export to Excel button and batch price fetching logic ---
    export_enabled = valid_date_range and not paginated_instruments.empty
    export_clicked = st.button('Export to Excel', disabled=not export_enabled)
    price_history_data = None
    if export_clicked and export_enabled:
        st.info('Fetching historical price data. This may take a while for many stocks...')
        import tempfile
        import io
        id_col = None
        for candidate in ['insId', 'id', 'instrumentId']:
            if candidate in paginated_instruments.columns:
                id_col = candidate
                break
        stock_ids = list(paginated_instruments['ticker'])
        rows = []
        for stock in stock_ids:
            try:
                data = api.fetch_datastream_timeseries(
                    instrument=stock,
                    datatypes=['P'],
                    start=export_from_date.strftime('%Y-%m-%d'),
                    end=export_to_date.strftime('%Y-%m-%d'),
                    frequency='D',  # or 'Y', 'Q', etc. as needed
                    kind=1
                )
                for kpi, records in data.items():
                    for date, value in records:
                        rows.append({
                            'stock_id': stock,
                            'date': date,
                            kpi.lower(): value
                        })
            except Exception as e:
                st.warning(f'Error fetching price for {stock}: {e}')
        if rows:
            price_history_data = pd.DataFrame(rows)
            st.success(f'Fetched price history for {len(stock_ids)} stocks.')
        else:
            price_history_data = pd.DataFrame()
            st.warning('No price history data was fetched for the selected stocks and date range.')

        # --- Excel export logic ---
        try:
            if price_history_data is not None and not price_history_data.empty:
                # Prepare summary sheet (filtered stocks, as before)
                summary_df = paginated_instruments_display.copy()
                # Prepare price history sheets
                with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
                    with pd.ExcelWriter(tmp.name, engine='xlsxwriter') as writer:
                        summary_df.to_excel(writer, sheet_name='Summary', index=False)
                        workbook  = writer.book
                        # Format for bold header
                        header_format = workbook.add_format({'bold': True})
                        # Autofit columns for summary sheet
                        worksheet = writer.sheets['Summary']
                        for i, col in enumerate(summary_df.columns):
                            max_len = max(
                                summary_df[col].astype(str).map(len).max(),
                                len(str(col))
                            ) + 2
                            worksheet.set_column(i, i, max_len)
                        # Apply bold to header row
                        for col_num, value in enumerate(summary_df.columns.values):
                            worksheet.write(0, col_num, value, header_format)
                        # Group price data by stock_id
                        price_cols = ['stock_id', 'date', 'p']
                        price_history_data = price_history_data[price_cols]
                        price_history_data.to_excel(writer, sheet_name='Price History', index=False)
                        ws = writer.sheets['Price History']
                        for i, col in enumerate(price_history_data.columns):
                            max_len = max(
                                price_history_data[col].astype(str).map(len).max(),
                                len(str(col))
                            ) + 2
                            ws.set_column(i, i, max_len)
                        for col_num, value in enumerate(price_history_data.columns.values):
                            ws.write(0, col_num, value, header_format)
                            
                    tmp.seek(0)
                    excel_bytes = tmp.read()
                st.download_button(
                    label='Download Excel File',
                    data=excel_bytes,
                    file_name='filtered_stocks_with_price_history.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
            else:
                st.warning('No price history data was fetched for the selected stocks and date range.')
        except Exception as e:
            st.error(f'Error during Excel export: {e}')

    if not paginated_instruments.empty:
        # Map IDs to names for export
        if 'sectorId' in paginated_instruments.columns:
            paginated_instruments['sector'] = paginated_instruments['sectorId'].map(sector_id_to_name)
        if 'marketId' in paginated_instruments.columns:
            paginated_instruments['market'] = paginated_instruments['marketId'].map(market_id_to_name)
        if 'countryId' in paginated_instruments.columns:
            paginated_instruments['country'] = paginated_instruments['countryId'].map(country_id_to_name)
        if 'branchId' in paginated_instruments.columns:
            paginated_instruments['branch'] = paginated_instruments['branchId'].map(branch_id_to_name)
        # Optionally drop the ID columns
        paginated_instruments = paginated_instruments.drop(columns=['sectorId', 'marketId', 'countryId', 'branchId'], errors='ignore')