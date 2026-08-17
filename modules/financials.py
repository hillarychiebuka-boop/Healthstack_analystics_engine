import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from db import db

@st.cache_data(ttl=3600)
def load_financial_data():
    """
    Fetches raw billing documents via MongoDB Aggregation Pipeline,
    transforms types, cleans string representations, and constructs standard accounting metrics + AR Aging.
    """
    collection = db['bills']
    pipeline = [
        {"$match": {"createdAt": {"$exists": True, "$ne": None}}},
        {
            "$lookup": {
                "from": "facilities",
                "localField": "participantInfo.billingFacility",
                "foreignField": "_id",
                "as": "facilityInfo"
            }
        },
        {
            "$project": {
                "_id": 0,
                "billId": {"$toString": "$_id"},
                "createdAt": "$createdAt",
                "facilityName": {
                    "$cond": [
                        {"$gt": [{"$size": "$facilityInfo"}, 0]},
                        {"$arrayElemAt": ["$facilityInfo.facilityName", 0]},
                        {
                            "$ifNull": [
                                "$orderInfo.orderObj.requestingdoctor_facilityname",
                                "Unassigned Facility"
                            ]
                        }
                    ]
                },
                "totalAmount": {
                    "$ifNull": [
                        "$paymentInfo.amountDue", 
                        {"$ifNull": ["$totalAmount", 0.0]}
                    ]
                },
                "amountPaid": {
                    "$ifNull": [
                        "$paymentInfo.amountpaid", 
                        {"$ifNull": ["$amountPaid", 0.0]}
                    ]
                },
                "outstandingBalance": {
                    "$ifNull": [
                        "$paymentInfo.balance", 
                        0.0
                    ]
                },
                "paymentStatus": {
                    "$ifNull": ["$billing_status", {"$ifNull": ["$status", "UNPAID"]}]
                },
                "payerType": {
                    "$ifNull": [
                        "$participantInfo.paymentmode.name", 
                        {"$ifNull": ["$payerType", "Out-of-Pocket"]}
                    ]
                },
                "clientName": {
                    "$ifNull": [
                        "$orderInfo.orderObj.clientname",
                        "Unknown Client"
                    ]
                }
            }
        }
    ]
    
    raw_bills = list(collection.aggregate(pipeline))
    df = pd.DataFrame(raw_bills)
    
    if df.empty:
        return pd.DataFrame(columns=[
            "billId", "createdAt", "date", "facilityName", "totalAmount", 
            "amountPaid", "outstandingBalance", "paymentStatus", "payerType", 
            "clientName", "days_outstanding", "aging_bucket"
        ])

    # Enforce Correct Data Types
    df['createdAt'] = pd.to_datetime(df['createdAt'], errors='coerce')
    df['date'] = df['createdAt'].dt.date
    
    for col in ['totalAmount', 'amountPaid', 'outstandingBalance']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)

    # Recalculate Outstanding Balance to guarantee accuracy
    df['outstandingBalance'] = df['totalAmount'] - df['amountPaid']

    # Text Cleanups
    for col in ['paymentStatus', 'payerType', 'facilityName']:
        df[col] = df[col].astype(str).str.strip().str.title()
        df[col] = df[col].replace({"Nan": "Unknown", "None": "Unknown", "": "Unknown"})

    # Accounts Receivable (AR) Aging Engine with Non-Negative Safeguard
    today = pd.to_datetime("today").normalize()
    df["days_outstanding"] = np.where(
        df["outstandingBalance"] > 0,
        (today - df["createdAt"]).dt.days,
        0
    )
    # Clip negative values resulting from same-day timezone offsets
    df["days_outstanding"] = df["days_outstanding"].clip(lower=0)

    conditions = [
        (df["outstandingBalance"] <= 0),
        (df["days_outstanding"] <= 30),
        (df["days_outstanding"] > 30) & (df["days_outstanding"] <= 60),
        (df["days_outstanding"] > 60) & (df["days_outstanding"] <= 90),
        (df["days_outstanding"] > 90)
    ]

    choices = [
        "Settled",
        "0-30 Days (Current)",
        "31-60 Days",
        "61-90 Days",
        "90+ Days (Overdue)"
    ]

    df["aging_bucket"] = np.select(conditions, choices, default="Unknown")

    return df


def render_financials_tab(filtered_financials, selected_facility):
    """
    Renders Executive Financial Engine Dashboard with KPIs, Payer Channel Distribution,
    HMO Provider Performance, Revenue Trends, and AR Aging Analytics.
    """
    st.header(f"💳 Executive Financial Engine & Billing Analytics — [{selected_facility}]")
    st.caption("Global standard financial overview across billed revenue, patient collections, HMO payer mix, and accounts receivable aging.")

    if not filtered_financials.empty:
        total_billed = filtered_financials['totalAmount'].sum()
        total_collected = filtered_financials['amountPaid'].sum()
        total_outstanding = filtered_financials['outstandingBalance'].sum()
        collection_rate = (total_collected / total_billed * 100) if total_billed > 0 else 0.0

        # Executive KPI Bar
        f1, f2, f3, f4 = st.columns(4)
        f1.metric("Gross Billed Revenue", f"₦{total_billed:,.2f}")
        f2.metric("Total Collections", f"₦{total_collected:,.2f}")
        f3.metric("Outstanding Receivables", f"₦{total_outstanding:,.2f}", delta="Pending Claims/Bills", delta_color="inverse")
        f4.metric("Collection Efficiency Rate", f"{collection_rate:.1f}%")

        st.markdown("---")

        # Row 1: Distribution Charts (Fixing Legend Bug)
        fin_col1, fin_col2 = st.columns(2)

        with fin_col1:
            st.subheader(f"💼 Top Revenue Channels — [{selected_facility}]")
            payer_df = (
                filtered_financials.groupby("payerType", as_index=False)["totalAmount"]
                .sum()
                .sort_values(by="totalAmount", ascending=False)
                .head(10)
            )
            fig_payer = px.bar(
                payer_df,
                x="totalAmount",
                y="payerType",
                orientation="h",
                labels={"payerType": "Payer Channel", "totalAmount": "Total Billed (₦)"},
                color="totalAmount",
                color_continuous_scale="Viridis",
                template="plotly_dark"
            )
            fig_payer.update_layout(height=380, showlegend=False, yaxis={'categoryorder': 'total ascending'}, margin=dict(t=20, b=20, l=10, r=10))
            st.plotly_chart(fig_payer, use_container_width=True)

        with fin_col2:
            st.subheader(f"📊 Payment Settlement Status — [{selected_facility}]")
            status_df = (
                filtered_financials.groupby("paymentStatus", as_index=False)["totalAmount"]
                .sum()
                .sort_values(by="totalAmount", ascending=False)
            )
            fig_status = px.bar(
                status_df,
                x="paymentStatus",
                y="totalAmount",
                labels={"paymentStatus": "Payment Status", "totalAmount": "Total Value (₦)"},
                color="paymentStatus",
                color_discrete_sequence=px.colors.qualitative.Set2,
                template="plotly_dark"
            )
            fig_status.update_layout(height=380, showlegend=False, margin=dict(t=20, b=20, l=10, r=10))
            st.plotly_chart(fig_status, use_container_width=True)

        st.markdown("---")

        # Row 2: HMO / Payer Provider Analysis Sub-Engine
        st.subheader(f"🏥 HMO & Corporate Payer Risk Analysis — [{selected_facility}]")
        
        # Filter for HMO / Non-Cash Channels
        hmo_df = filtered_financials[~filtered_financials["payerType"].isin(["Cash", "Out-Of-Pocket", "Unknown"])]
        
        if not hmo_df.empty:
            hmo_summary = (
                hmo_df.groupby("payerType", as_index=False)[["totalAmount", "amountPaid", "outstandingBalance"]]
                .sum()
                .sort_values(by="outstandingBalance", ascending=False)
            )
            hmo_summary["Collection %"] = np.where(
                hmo_summary["totalAmount"] > 0,
                (hmo_summary["amountPaid"] / hmo_summary["totalAmount"]) * 100,
                0.0
            )

            hmo_col1, hmo_col2 = st.columns([3, 2])

            with hmo_col1:
                fig_hmo = px.bar(
                    hmo_summary.head(8),
                    x="payerType",
                    y=["amountPaid", "outstandingBalance"],
                    title="Billed vs Uncollected Debt by HMO Provider (Top 8)",
                    labels={"value": "Amount (₦)", "payerType": "HMO / Provider", "variable": "Status"},
                    barmode="stack",
                    color_discrete_map={"amountPaid": "#2ec4b6", "outstandingBalance": "#e71d36"},
                    template="plotly_dark"
                )
                fig_hmo.update_layout(height=350, legend=dict(orientation="h", y=1.1), margin=dict(t=20, b=20, l=10, r=10))
                st.plotly_chart(fig_hmo, use_container_width=True)

            with hmo_col2:
                st.markdown("#### 📋 HMO Exposure Matrix")
                st.dataframe(
                    hmo_summary.rename(columns={
                        "payerType": "HMO / Payer",
                        "totalAmount": "Billed (₦)",
                        "outstandingBalance": "Debt (₦)",
                        "Collection %": "Recovery %"
                    })[["HMO / Payer", "Billed (₦)", "Debt (₦)", "Recovery %"]],
                    use_container_width=True,
                    height=290
                )
        else:
            st.info("No dedicated HMO/Insurance transactions recorded for this facility.")

        st.markdown("---")

        # Row 3: Revenue Trend Velocity
        st.subheader(f"📈 Revenue Generation Velocity Over Time — [{selected_facility}]")
        fin_trend = filtered_financials.groupby("date", as_index=False)[["totalAmount", "amountPaid"]].sum()
        fig_fin_trend = px.line(
            fin_trend,
            x="date",
            y=["totalAmount", "amountPaid"],
            labels={"date": "Date", "value": "Amount (₦)", "variable": "Financial Metric"},
            template="plotly_dark"
        )
        fig_fin_trend.update_layout(
            height=380,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(t=20, b=20, l=10, r=10)
        )
        st.plotly_chart(fig_fin_trend, use_container_width=True)

        st.markdown("---")

        # Row 4: Accounts Receivable (AR) Aging Engine
        st.subheader(f"⏳ Accounts Receivable (AR) Aging Breakdown — [{selected_facility}]")
        unpaid_df = filtered_financials[filtered_financials["outstandingBalance"] > 0]

        if unpaid_df.empty:
            st.success("🎉 No outstanding accounts receivable found for this selection!")
        else:
            ar_col1, ar_col2 = st.columns([3, 2])

            with ar_col1:
                aging_summary = (
                    unpaid_df.groupby("aging_bucket", as_index=False)["outstandingBalance"]
                    .sum()
                )
                bucket_order = ["0-30 Days (Current)", "31-60 Days", "61-90 Days", "90+ Days (Overdue)"]
                aging_summary["aging_bucket"] = pd.Categorical(
                    aging_summary["aging_bucket"],
                    categories=bucket_order,
                    ordered=True
                )
                aging_summary = aging_summary.sort_values("aging_bucket")

                fig_aging = px.bar(
                    aging_summary,
                    x="aging_bucket",
                    y="outstandingBalance",
                    text_auto=".2s",
                    color="aging_bucket",
                    color_discrete_map={
                        "0-30 Days (Current)": "#2ec4b6",
                        "31-60 Days": "#ffbf00",
                        "61-90 Days": "#ff9f1c",
                        "90+ Days (Overdue)": "#e71d36"
                    },
                    template="plotly_dark",
                    labels={"outstandingBalance": "Uncollected Balance (₦)", "aging_bucket": "Aging Bracket"}
                )
                fig_aging.update_layout(height=350, showlegend=False, margin=dict(t=20, b=20, l=10, r=10))
                st.plotly_chart(fig_aging, use_container_width=True)

            with ar_col2:
                st.markdown("#### ⚠️ High-Risk Receivables (>90 Days)")
                high_risk = unpaid_df[unpaid_df["aging_bucket"] == "90+ Days (Overdue)"][
                    ["clientName", "days_outstanding", "outstandingBalance"]
                ].sort_values(by="days_outstanding", ascending=False)

                if not high_risk.empty:
                    st.dataframe(
                        high_risk.rename(columns={
                            "clientName": "Client / Patient",
                            "days_outstanding": "Days Overdue",
                            "outstandingBalance": "Balance (₦)"
                        }),
                        use_container_width=True,
                        height=280
                    )
                else:
                    st.info("No accounts currently over 90 days overdue.")

        # Inspect Raw Dataset
        with st.expander("🔍 Inspect Raw Financial & Billing Dataset"):
            st.dataframe(filtered_financials, use_container_width=True)
    else:
        st.warning("⚠️ No billing/financial records found for the selected facility filter.")