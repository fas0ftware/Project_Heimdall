# Heimdall | Market Dashboard

> *"Data is merely noise until logic gives it a voice."*

An interactive stock dashboard that turns raw market data into signals: RSI tracking, split-adjusted return simulation and automatic stock split detection.

## ◼ Overview

**Heimdall** bridges the gap between raw market data and readable insight. This repository contains the **web dashboard**, built with Streamlit and Plotly. A lightweight terminal scanner for quick RSI checks lives in the companion project, [Project_Hugnin](https://github.com/fas0ftware/Project_Hugnin).

## ◼ Preview

![Dashboard preview](dashboard_preview.png)

## ◼ Features

**Interactive dashboard**
- **Live tracking:** Fetches current data for major US tech stocks (AAPL, TSLA, NVDA and more).
- **RSI indicator:** Flags oversold (below 30) and overbought (above 70) conditions automatically.
- **Interactive charts:** Zoomable Plotly visualizations.

**Time machine simulation (ROI calculator)**
- **"What if" scenarios:** Shows what an investment of a chosen amount, made a chosen number of years ago, would be worth today.
- **Split-adjusted logic:** Historical prices are adjusted for stock splits so the results stay accurate.

**Split hunter**
- **Auto-detection:** Scans price history for stock splits.
- **Visual markers:** Highlights split events directly on the chart (for example, NVIDIA's 10-for-1 split) so they are not mistaken for price crashes.

## ◼ Project structure

```
Project_Heimdall/
├── dashboard.py          # Streamlit app
├── dashboard_preview.png # Screenshot used in this README
└── requirements.txt      # Dependencies
```

## ◼ Requirements

- Python 3.9 or newer
- pip
- An internet connection (market data is fetched online)

## ◼ Installation

```bash
git clone https://github.com/fas0ftware/Project_Heimdall.git
cd Project_Heimdall
```

Create and activate a virtual environment.

Linux / macOS:

```bash
python3 -m venv venv
source venv/bin/activate
```

Windows:

```bash
python -m venv venv
venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## ◼ Usage

Launch the dashboard in your default browser:

```bash
streamlit run dashboard.py
```

## ◼ Notes and limitations

- Data availability and accuracy depend on the upstream data provider, and values can be delayed or incomplete.
- The ROI simulation is a historical calculation, not a prediction.
- RSI is one indicator among many and should not be used alone.

## ◼ Disclaimer

This software is for educational and informational purposes only. It does not constitute financial advice.

---

Part of the **FA Software** projects.
