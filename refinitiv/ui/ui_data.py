import streamlit as st
import pandas as pd
# --- Single cache function for all initial data ---
@st.cache_data
def fetch(_api):
    # Get instruments data (only local instruments now)
    base_df_local = _api.get_instruments()
    if not isinstance(base_df_local, pd.DataFrame):
        base_df_local = pd.DataFrame(base_df_local)
    all_instruments_df = base_df_local  # Use only local instruments
    
    # Use mock data from RefinitivAPI for UI demonstration
    all_countries_df = _api.get_countries().reset_index()
    all_markets_df = _api.get_markets().reset_index()
    all_sectors_df = _api.get_sectors().reset_index()
    all_branches_df = _api.get_branches().reset_index()
    # No KPI metadata needed for Refinitiv - uses direct field codes
    return (all_instruments_df, all_countries_df, all_markets_df, all_sectors_df, all_branches_df)

def match_country_sector_industry_names(countries_df, sectors_df, industries_df, translation_df):
    #Build a mapping from Swidish to English
    sv_to_en = dict(zip(translation_df['nameSv'], translation_df['nameEn']))

    #Replace in countries
    if 'name' in countries_df.columns:
        countries_df['name'] = countries_df['name'].map(lambda x: sv_to_en.get(x, x))
    
    #Replace in sectors
    if 'name' in sectors_df.columns:
        sectors_df['name'] = sectors_df['name'].map(lambda x: sv_to_en.get(x, x))

    #Replace in industries/branches
    if 'name' in industries_df.columns:
        industries_df['name'] = industries_df['name'].map(lambda x:sv_to_en)

# --- Fetch all stocks (no pagination here) ---
def get_filtered_stocks(all_instruments_df, country_ids=None, market_ids=None) -> pd.DataFrame:
    # For mock data, return the original DataFrame without filtering
    if all_instruments_df is None or all_instruments_df.empty:
        return pd.DataFrame()
    
    df = all_instruments_df.copy()
    if country_ids is not None:
        country_ids = [int(x) for x in list(country_ids)]
        df = pd.DataFrame(df)
        df = df[df['countryId'].isin(country_ids)]
    if market_ids is not None:
        market_ids = [int(x) for x in list(market_ids)]
        df = pd.DataFrame(df)
        available_market_ids = set(df['marketId'].dropna().unique())
        if set(market_ids) == set(available_market_ids):
            df = df[df['marketId'].isin(market_ids) | df['marketId'].isnull()]
        else:
            df = df[df['marketId'].isin(market_ids)]
    return pd.DataFrame(df)
