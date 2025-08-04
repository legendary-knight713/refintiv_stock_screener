## Refinitiv DataStream REST API Client

A simple Python console client to get started with the Refinitiv DataStream REST API.

> This project demonstrates how to authenticate with a **username/password**, fetch time series and instrument metadata, and export results to Excel or JSON.

## API Access

To use the DataStream REST API, you need valid **Refinitiv credentials**.

- Sign up or request access via your organization's Refinitiv account manager.
- Ensure your user has access to the **DataStream Web Services**.

## Authentication

This client uses **username and password** to obtain an access token. These credentials should be stored securely (e.g., in a `.env` file or external config).

## Installation

Requires Python 3.7+.

Install dependencies using pip:

```bash
pip install -r requirements.txt
