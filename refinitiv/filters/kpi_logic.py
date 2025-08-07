import pandas as pd
from refinitiv.api.refinitiv_api import RefinitivAPI

def convert_groups_to_old_format(filter_groups):
    """Convert the new group format to the old kpi_filters format for compatibility."""
    old_filters = []
    for group_idx, group in enumerate(filter_groups):
        for kpi_idx, kpi_name in enumerate(group['filters']):
            kpi_instance_key = f"{kpi_name}_{kpi_idx}"
            kpi_settings = group.get('filter_settings', {}).get(kpi_instance_key, {})
            methods = kpi_settings.get('methods', [])
            for method_idx, method_config in enumerate(methods):
                old_filter = {
                    'kpi': kpi_name,
                    'method': method_config.get('type', 'Absolute'),
                    'group_id': group_idx,
                    'group_operator': group['operator'],
                    'method_id': method_idx,
                    'method_operator': kpi_settings.get('method_operator', 'AND')
                }
                # Add method-specific parameters
                if method_config.get('type') == 'Absolute':
                    if method_config.get('operator_abs') is not None:
                        old_filter['operator'] = method_config.get('operator_abs')
                    if method_config.get('value') is not None:
                        old_filter['value'] = method_config.get('value')
                    if method_config.get('duration_type') is not None:
                        old_filter['duration_type'] = method_config.get('duration_type')
                    if method_config.get('last_n') is not None:
                        old_filter['last_n'] = method_config.get('last_n')
                    if method_config.get('start_date'):
                        old_filter['start_date'] = method_config.get('start_date')
                    if method_config.get('end_date'):
                        old_filter['end_date'] = method_config.get('end_date')
                    if method_config.get('data_frequency') is not None:
                        old_filter['data_frequency'] = method_config.get('data_frequency')
                elif method_config.get('type') == 'Relative':
                    if method_config.get('rel_operator') is not None:
                        old_filter['rel_operator'] = method_config.get('rel_operator')
                    if method_config.get('rel_value') is not None:
                        old_filter['rel_value'] = method_config.get('rel_value')
                    if method_config.get('rel_mode') is not None:
                        old_filter['rel_mode'] = method_config.get('rel_mode')
                    if method_config.get('duration_type') is not None:
                        old_filter['duration_type'] = method_config.get('duration_type')
                    if method_config.get('last_n') is not None:
                        old_filter['last_n'] = method_config.get('last_n')
                    if method_config.get('start_date'):
                        old_filter['start_date'] = method_config.get('start_date')
                    if method_config.get('end_date'):
                        old_filter['end_date'] = method_config.get('end_date')
                    if method_config.get('data_frequency') is not None:
                        old_filter['data_frequency'] = method_config.get('data_frequency')
                elif method_config.get('type') == 'Direction':
                    if method_config.get('direction') is not None:
                        old_filter['direction'] = method_config.get('direction')
                    if method_config.get('duration_type') is not None:
                        old_filter['duration_type'] = method_config.get('duration_type')
                    if method_config.get('last_n') is not None:
                        old_filter['last_n'] = method_config.get('last_n')
                    if method_config.get('start_date'):
                        old_filter['start_date'] = method_config.get('start_date')
                    if method_config.get('end_date'):
                        old_filter['end_date'] = method_config.get('end_date')
                    if method_config.get('data_frequency') is not None:
                        old_filter['data_frequency'] = method_config.get('data_frequency')
                elif method_config.get('type') == 'Trend':
                    if method_config.get('trend_type') is not None:
                        old_filter['trend_type'] = method_config.get('trend_type')
                    if method_config.get('trend_n') is not None:
                        old_filter['trend_n'] = method_config.get('trend_n')
                    if method_config.get('trend_m') is not None:
                        old_filter['trend_m'] = method_config.get('trend_m')
                    if method_config.get('data_frequency') is not None:
                        old_filter['data_frequency'] = method_config.get('data_frequency')
                old_filters.append(old_filter)
    return old_filters


def build_group_logic_tree(filter_groups, kpi_filters, group_relationships='AND'):
    """Build the logic tree for group-based filtering."""
    if not filter_groups:
        return None
    group_nodes = []
    for group_idx, group in enumerate(filter_groups):
        if not group['filters']:
            continue
        if len(group['filters']) == 1:
            kpi_name = group['filters'][0]
            kpi_instance_key = f"{kpi_name}_0"
            kpi_settings = group.get('filter_settings', {}).get(kpi_instance_key, {})
            methods = kpi_settings.get('methods', [])
            if len(methods) == 1:
                filter_idx = None
                for old_idx, old_filter in enumerate(kpi_filters):
                    if (old_filter['kpi'] == kpi_name and 
                        old_filter.get('group_id') == group_idx and 
                        old_filter.get('method_id') == 0):
                        filter_idx = old_idx
                        break
                group_node = filter_idx if filter_idx is not None else group_idx
            else:
                method_indices = []
                for method_idx, method_config in enumerate(methods):
                    for old_idx, old_filter in enumerate(kpi_filters):
                        if (old_filter['kpi'] == kpi_name and 
                            old_filter.get('group_id') == group_idx and 
                            old_filter.get('method_id') == method_idx):
                            method_indices.append(old_idx)
                            break
                if method_indices:
                    method_operator = kpi_settings.get('method_operator', 'AND')
                    group_node = {
                        'type': method_operator,
                        'children': method_indices
                    }
                else:
                    group_node = group_idx
        else:
            kpi_indices = []
            for kpi_idx, kpi_name in enumerate(group['filters']):
                kpi_instance_key = f"{kpi_name}_{kpi_idx}"
                kpi_settings = group.get('filter_settings', {}).get(kpi_instance_key, {})
                methods = kpi_settings.get('methods', [])
                if len(methods) == 1:
                    filter_idx = None
                    for old_idx, old_filter in enumerate(kpi_filters):
                        if (old_filter['kpi'] == kpi_name and 
                            old_filter.get('group_id') == group_idx and 
                            old_filter.get('method_id') == 0):
                            filter_idx = old_idx
                            break
                    if filter_idx is not None:
                        kpi_indices.append(filter_idx)
                else:
                    method_indices = []
                    for method_idx, method_config in enumerate(methods):
                        for old_idx, old_filter in enumerate(kpi_filters):
                            if (old_filter['kpi'] == kpi_name and 
                                old_filter.get('group_id') == group_idx and 
                                old_filter.get('method_id') == method_idx):
                                method_indices.append(old_idx)
                                break
                    if method_indices:
                        if len(method_indices) == 1:
                            kpi_indices.append(method_indices[0])
                        else:
                            method_operator = kpi_settings.get('method_operator', 'AND')
                            sub_node = {
                                'type': method_operator,
                                'children': method_indices
                            }
                            group_nodes.append(sub_node)
                            kpi_indices.append(len(group_nodes) - 1)
            if kpi_indices:
                if len(kpi_indices) == 1:
                    group_node = kpi_indices[0]
                else:
                    group_node = {
                        'type': group['operator'],
                        'children': kpi_indices
                    }
            else:
                group_node = group_idx
        group_nodes.append(group_node)
    if len(group_nodes) == 1:
        return group_nodes[0]
    else:
        return {
            'type': group_relationships,
            'children': group_nodes
        }

def validate_logic_tree(tree, kpi_filter_settings):
    """Validate that all indices in the logic tree exist in kpi_filter_settings."""
    if isinstance(tree, int):
        if tree not in kpi_filter_settings:
            print(f"WARNING: Logic tree index {tree} not found in kpi_filter_settings")
            return False
        return True
    elif isinstance(tree, dict) and 'children' in tree:
        for child in tree['children']:
            if not validate_logic_tree(child, kpi_filter_settings):
                return False
        return True
    return False


def fetch_kpi_data_for_calculation(stocks, st, kpi_filter_settings):
    """Fetch KPI data needed for calculations, using correct frequency for each KPI."""
    max_stocks = 1000
    api = RefinitivAPI()
    
    if len(stocks) > max_stocks and st:
        st.warning(f"Too many stocks ({len(stocks)}). Processing first {max_stocks} stocks only.")
        stocks = stocks[:max_stocks]
        
    kpi_data = {}    
    
    for kpi_filter_id, kpi_filter_value in kpi_filter_settings.items():
        kpi_name = kpi_filter_value.get('kpi_name')
        last_n = kpi_filter_value.get('last_n', None)
        start_date = kpi_filter_value.get('start_date', '')
        end_date = kpi_filter_value.get('end_date', '')
        freq = kpi_filter_value.get('data_frequency', 'Quarterly')
        rows = []
        for stock in stocks:
            if freq == 'Yearly':
                if last_n is not None:
                    start_date = f"-{int(last_n) - 1}Y"
                    end_date = '0'
                    data = api.fetch_datastream_timeseries(instrument=stock, datatypes=[kpi_name], start=start_date, end=end_date, frequency='Y', kind=1)
                    for kpi, records in data.items():
                        for date, value in records:
                            if isinstance(value, (int, float)):
                                rows.append({'symbol': stock, 'date': date, 'kpiValue': value})
                else:
                    data = api.fetch_datastream_timeseries(instrument = stock, datatypes = [kpi_name], start = start_date, end = end_date, frequency = 'Y', kind=1)
                    for kpi, records in data.items():
                        for date, value in records:
                            if isinstance(value, (int, float)):
                                rows.append({'symbol': stock, 'date': date, 'kpiValue': value})
                
            else:
                if last_n is not None:
                    start_date = f"-{int(last_n) - 1}Q"
                    end_date = '0'
                    data = api.fetch_datastream_timeseries(instrument=stock, datatypes=[kpi_name], start=start_date, end=end_date, frequency='Q', kind=1)
                    for kpi, records in data.items():
                        for date, value in records:
                            if isinstance(value, (int, float)):
                                rows.append({'symbol': stock, 'date': date, 'kpiValue': value})
                else:
                    data = api.fetch_datastream_timeseries(instrument = stock, datatypes = [kpi_name], start = start_date, end = end_date, frequency = 'Q', kind=1)
                    for kpi, records in data.items():
                        for date, value in records:
                            if isinstance(value, (int, float)):
                                rows.append({'symbol': stock, 'date': date, 'kpiValue': value})

        kpi_data[kpi_name] = pd.DataFrame(rows)
    return kpi_data 