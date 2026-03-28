import pandas as pd
import streamlit as st

st.set_page_config(layout="wide")

# ==============================
# TITLE
# ==============================
st.title("🚚 Shipment Analytics Dashboard")

try:
    import os

    st.write("Current directory:", os.getcwd())
    st.write("Files available:", os.listdir())

    file_path = "shipments.xlsx"

    df = pd.read_excel(file_path)
    df.columns = df.columns.str.strip()

    # ==============================
    # CLEAN DATA
    # ==============================
    df['Arrival Port PTA Custom'] = pd.to_datetime(df['Arrival Port PTA Custom'], errors='coerce')
    df['ATA At Arrival Port'] = pd.to_datetime(df['ATA At Arrival Port'], errors='coerce')

    df = df.dropna(subset=['Arrival Port PTA Custom', 'ATA At Arrival Port'])
    df = df.drop_duplicates()

    # ==============================
    # FEATURE ENGINEERING
    # ==============================
    df['delay_days'] = (df['ATA At Arrival Port'] - df['Arrival Port PTA Custom']).dt.days

    def classify(x):
        if abs(x) <= 2:
            return "On-Time"
        elif x > 2:
            return "Delayed"
        else:
            return "Early"

    df['status'] = df['delay_days'].apply(classify)

    # ==============================
    # Z-SCORE ANOMALY
    # ==============================
    mean_delay = df['delay_days'].mean()
    std_delay = df['delay_days'].std()

    df['z_score'] = (df['delay_days'] - mean_delay) / std_delay
    df['anomaly'] = df['z_score'].apply(lambda x: "Anomaly" if abs(x) > 2 else "Normal")

    # ==============================
    # IQR ANOMALY
    # ==============================
    Q1 = df['delay_days'].quantile(0.25)
    Q3 = df['delay_days'].quantile(0.75)
    IQR = Q3 - Q1

    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR

    df['iqr_anomaly'] = df['delay_days'].apply(
        lambda x: "Anomaly" if (x < lower_bound or x > upper_bound) else "Normal"
    )
    
    # ==============================
    # 🔍 ADVANCED FILTERS (ADD HERE)
    # ==============================

    carrier_sel = st.sidebar.selectbox(
        "Select Carrier (Advanced)",
        ["All"] + sorted(df['Carrier Name'].dropna().unique().tolist())
    )

    pol_sel = st.sidebar.selectbox(
        "Select POL (Advanced)",
        ["All"] + sorted(df['POL'].dropna().unique().tolist())
    )

    pod_sel = st.sidebar.selectbox(
        "Select POD (Advanced)",
        ["All"] + sorted(df['POD'].dropna().unique().tolist())
    )
    
    # ==============================
    # BASE DF FOR CASCADING
    # ==============================
    df_filter = df.copy()

    # ==============================
    # FILTERS
    # ==============================
    st.sidebar.header("🔍 Filters")

    carrier_filter = st.sidebar.multiselect(
        "Select Carrier",
        options=df['Carrier Name'].dropna().unique(),
        default=df['Carrier Name'].dropna().unique()
    )

    pol_filter = st.sidebar.multiselect(
        "Select POL",
        options=df['POL'].dropna().unique(),
        default=df['POL'].dropna().unique()
    )
    
    pod_filter = st.sidebar.multiselect(
        "Select POD",
        options=df['POD'].dropna().unique(),
        default=df['POD'].dropna().unique()
    )
    
    pod_filter = st.sidebar.multiselect(
        "Select SCAC Code",
        options=df['SCAC Code'].dropna().unique(),
        default=df['SCAC Code'].dropna().unique()
    )
    
    pod_filter = st.sidebar.multiselect(
        "Select Creation Date",
        options=df['Creation Date'].dropna().unique(),
        default=df['Creation Date'].dropna().unique()
    )
    
    pod_filter = st.sidebar.multiselect(
        "Select Supplier",
        options=df['Supplier'].dropna().unique(),
        default=df['Supplier'].dropna().unique()
    )
    
    pod_filter = st.sidebar.multiselect(
        "Select Ship From",
        options=df['Ship From'].dropna().unique(),
        default=df['Ship From'].dropna().unique()
    )
    
    pod_filter = st.sidebar.multiselect(
        "Select Vessel",
        options=df['Vessel'].dropna().unique(),
        default=df['Vessel'].dropna().unique()
    )

    df = df[
        (df['Carrier Name'].isin(carrier_filter)) &
        (df['POL'].isin(pol_filter))
    ]
    
    # ==============================
    # 🔥 CASCADING FILTERS
    # ==============================

    # Carrier
    carrier_sel = st.sidebar.selectbox(
        "Select Carrier",
        ["All"] + sorted(df_filter['Carrier Name'].dropna().unique().tolist())
    )

    if carrier_sel != "All":
        df_filter = df_filter[df_filter['Carrier Name'] == carrier_sel]

    # POL
    pol_sel = st.sidebar.selectbox(
        "Select POL",
        ["All"] + sorted(df_filter['POL'].dropna().unique().tolist())
    )

    if pol_sel != "All":
        df_filter = df_filter[df_filter['POL'] == pol_sel]

    # POD
    pod_sel = st.sidebar.selectbox(
        "Select POD",
        ["All"] + sorted(df_filter['POD'].dropna().unique().tolist())
    )

    if pod_sel != "All":
        df_filter = df_filter[df_filter['POD'] == pod_sel]
    
    df = df_filter.copy()

    # ==============================
    # KPI
    # ==============================
    accuracy = (df['status'] == "On-Time").mean() * 100
    avg_delay = df['delay_days'].mean()

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Shipments", len(df))
    col2.metric("Tracking Accuracy (%)", round(accuracy, 2))
    col3.metric("Avg Delay (days)", round(avg_delay, 2))

    if avg_delay > 2:
        st.error("⚠️ High delay detected")
    else:
        st.success("✅ Stable performance")

    # ==============================
    # STATUS + DRILL DOWN
    # ==============================
    st.subheader("📦 Shipment Status")
    st.bar_chart(df['status'].value_counts())

    selected_status = st.selectbox("Select Status", df['status'].unique())
    st.dataframe(
        df[df['status'] == selected_status][
            ['Shipment No','Container No','Carrier Name','delay_days']
        ]
    )

    # ==============================
    # CARRIER
    # ==============================
    st.subheader("🚢 Carrier Performance")
    carrier_perf = df.groupby('Carrier Name')['delay_days'].mean().sort_values(ascending=False)
    st.bar_chart(carrier_perf)

    # ==============================
    # ROUTE + DRILL DOWN
    # ==============================
    st.subheader("🌍 Top Delayed Routes")

    route_perf = df.groupby(['POL','POD'])['delay_days'].mean().reset_index()
    route_perf = route_perf.sort_values(by='delay_days', ascending=False)

    st.dataframe(route_perf.head(10))

    selected_route = st.selectbox(
        "Select Route",
        route_perf.apply(lambda x: f"{x['POL']} → {x['POD']}", axis=1)
    )

    pol_sel, pod_sel = selected_route.split(" → ")

    st.dataframe(
        df[(df['POL'] == pol_sel) & (df['POD'] == pod_sel)][
            ['Shipment No','Container No','Carrier Name','delay_days']
        ]
    )

    # ==============================
    # HIGH DELAY
    # ==============================
    st.subheader("🚨 High Delay Shipments")
    high_delay = df[df['delay_days'] > 7]

    st.dataframe(
        high_delay[
            ['Shipment No','Container No','Carrier Name','POL','POD','delay_days']
        ]
    )

    # ==============================
    # IQR ANOMALY
    # ==============================
    st.subheader("🧠 IQR Anomalies")
    iqr_anomalies = df[df['iqr_anomaly'] == "Anomaly"]

    st.dataframe(
        iqr_anomalies[
            ['Shipment No','Container No','Carrier Name','POL','POD','delay_days']
        ]
    )

    # ==============================
    # ANOMALY BY CARRIER
    # ==============================
    st.subheader("🚨 Anomalies by Carrier")
    anomaly_by_carrier = df[df['anomaly'] == "Anomaly"].groupby('Carrier Name').size()
    st.bar_chart(anomaly_by_carrier)

    # ==============================
    # ANOMALY RATE
    # ==============================
    carrier_total = df.groupby('Carrier Name').size()
    carrier_anomaly = df[df['anomaly'] == "Anomaly"].groupby('Carrier Name').size()

    anomaly_rate = (carrier_anomaly / carrier_total * 100).fillna(0)
    st.subheader("📊 Anomaly Rate (%)")
    st.bar_chart(anomaly_rate)

    # ==============================
    # ANOMALY ROUTES + DRILL DOWN
    # ==============================
    st.subheader("🚨 Top Anomaly Routes")

    anomaly_routes = df[df['anomaly'] == "Anomaly"] \
        .groupby(['Carrier Name','POL','POD']) \
        .size() \
        .reset_index(name='count') \
        .sort_values(by='count', ascending=False)

    st.dataframe(anomaly_routes.head(10))

    selected_combo = st.selectbox(
        "Select Carrier + Route",
        anomaly_routes.apply(lambda x: f"{x['Carrier Name']} | {x['POL']} → {x['POD']}", axis=1)
    )

    carrier_sel, route = selected_combo.split(" | ")
    pol_sel, pod_sel = route.split(" → ")

    st.dataframe(
        df[
            (df['Carrier Name'] == carrier_sel) &
            (df['POL'] == pol_sel) &
            (df['POD'] == pod_sel)
        ][['Shipment No','Container No','delay_days']]
    )

    # ==============================
    # EXCEPTION
    # ==============================
    st.subheader("⚠️ Exception Status")
    st.bar_chart(df['Header Exception Status'].value_counts())

    # ==============================
    # DOWNLOAD
    # ==============================
    csv = df.to_csv(index=False).encode('utf-8')

    st.download_button(
        "⬇️ Download Data",
        csv,
        "shipment_analysis.csv",
        "text/csv"
    )

except Exception as e:
    st.error(f"❌ Error: {e}")
