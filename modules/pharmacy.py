import streamlit as st
import pandas as pd
import plotly.express as px

def format_currency_human(amount):
    try:
        amount = float(amount)
    except (ValueError, TypeError):
        amount = 0.0

    if abs(amount) >= 1e9:
        return f"₦{amount / 1e9:,.2f}B"
    elif abs(amount) >= 1e6:
        return f"₦{amount / 1e6:,.2f}M"
    elif abs(amount) >= 1e3:
        return f"₦{amount / 1e3:,.1f}K"
    else:
        return f"₦{amount:,.2f}"

def render_pharmacy_tab(df_inventory, df_sales, selected_facility):
    st.markdown(f"## 💊 Pharmacy Operations & Inventory Analytics — [{selected_facility}]")
    st.markdown("Real-time executive intelligence across drug stock balances, reorder risk levels, sales velocity, and profit margins.")

    # Convert to DataFrames if None passed
    df_inv = df_inventory.copy() if df_inventory is not None else pd.DataFrame()
    df_sls = df_sales.copy() if df_sales is not None else pd.DataFrame()

    if df_inv.empty and df_sls.empty:
        st.warning(f"⚠️ No inventory or sales records found for {selected_facility}.")
        return

    # Ensure required Inventory Columns
    inv_defaults = {
        'computedStockValue': 0.0,
        'isLowStock': False,
        'itemName': 'Unknown SKU',
        'facilityName': selected_facility,
        'quantity': 0,
        'reorderLevel': 0,
        'baseUnit': 'Unit',
        'costPrice': 0.0,
        'sellingPrice': 0.0
    }
    for col, def_val in inv_defaults.items():
        if col not in df_inv.columns:
            df_inv[col] = def_val

    # Ensure required Sales Columns
    sales_defaults = {
        'lineRevenue': 0.0,
        'lineProfit': 0.0,
        'qtySold': 0,
        'itemName': 'Unknown SKU',
        'transactionDate': None,
        'documentNo': 'N/A',
        'facilityName': selected_facility,
        'sourceClient': 'Direct Sale',
        'unitPrice': 0.0
    }
    for col, def_val in sales_defaults.items():
        if col not in df_sls.columns:
            df_sls[col] = def_val

    # Executive Metrics Calculations
    total_val = pd.to_numeric(df_inv['computedStockValue'], errors='coerce').fillna(0).sum() if not df_inv.empty else 0
    total_items = len(df_inv) if not df_inv.empty else 0
    low_stock_cnt = int(df_inv['isLowStock'].astype(bool).sum()) if not df_inv.empty else 0
    
    total_revenue = pd.to_numeric(df_sls['lineRevenue'], errors='coerce').fillna(0).sum() if not df_sls.empty else 0
    total_profit = pd.to_numeric(df_sls['lineProfit'], errors='coerce').fillna(0).sum() if not df_sls.empty else 0
    profit_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0.0

    kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
    kpi1.metric("📦 Inventory Portfolio", format_currency_human(total_val), help=f"Exact Value: ₦{total_val:,.2f}")
    kpi2.metric("🏷️ Tracked SKUs", f"{total_items:,}")
    kpi3.metric("⚠️ Reorder / Low Stock", f"{low_stock_cnt:,}", delta="-Risk Alert" if low_stock_cnt > 0 else "Optimal", delta_color="inverse")
    kpi4.metric("💳 Pharmacy Revenue", format_currency_human(total_revenue), help=f"Exact Revenue: ₦{total_revenue:,.2f}")
    kpi5.metric("📈 Gross Margin", f"{profit_margin:.1f}%", delta=f"{format_currency_human(total_profit)} Profit")

    st.markdown("---")

    # Analytics Charts
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.markdown("**🔥 Fast-Moving Medications (Top 10 Volume)**")
        if not df_sls.empty:
            top_sales = df_sls.groupby("itemName")["qtySold"].sum().reset_index()
            top_sales = top_sales.sort_values("qtySold", ascending=False).head(10)
            
            fig_sales = px.bar(
                top_sales,
                x="qtySold",
                y="itemName",
                orientation="h",
                text_auto=".2s",
                labels={"qtySold": "Units Dispensed", "itemName": "Medication Name"},
                color="qtySold",
                color_continuous_scale="Viridis",
                template="plotly_dark"
            )
            fig_sales.update_layout(yaxis={'categoryorder': 'total ascending'}, margin=dict(l=20, r=20, t=20, b=20), height=380)
            st.plotly_chart(fig_sales, use_container_width=True)
        else:
            st.info("No dispensing transactions recorded for chart rendering.")

    with col_chart2:
        st.markdown("**💰 Top Revenue Generating Medications**")
        if not df_sls.empty:
            top_rev = df_sls.groupby("itemName")["lineRevenue"].sum().reset_index()
            top_rev = top_rev.sort_values("lineRevenue", ascending=False).head(10)
            
            fig_rev = px.bar(
                top_rev,
                x="lineRevenue",
                y="itemName",
                orientation="h",
                text_auto=".2s",
                labels={"lineRevenue": "Revenue (₦)", "itemName": "Medication Name"},
                color="lineRevenue",
                color_continuous_scale="Tealgrn",
                template="plotly_dark"
            )
            fig_rev.update_layout(yaxis={'categoryorder': 'total ascending'}, margin=dict(l=20, r=20, t=20, b=20), height=380)
            st.plotly_chart(fig_rev, use_container_width=True)
        else:
            st.info("No sales revenue records found for chart rendering.")

    st.markdown("---")

    # Master Tables
    tab_inv, tab_ledger = st.tabs(["📋 Inventory Master & Stock Alerts", "🧾 Dispensing & Sales Ledger"])

    with tab_inv:
        if not df_inv.empty:
            st.subheader("Inventory Stock Audit")
            filter_low = st.checkbox("Show Only Reorder/Low Stock Items", value=False)
            display_inv = df_inv[df_inv['isLowStock'] == True] if filter_low else df_inv
            
            st.dataframe(
                display_inv[[
                    'itemName', 'facilityName', 'quantity', 'reorderLevel', 
                    'baseUnit', 'costPrice', 'sellingPrice', 'computedStockValue', 'isLowStock'
                ]].sort_values('quantity', ascending=True),
                column_config={
                    "itemName": "Medication Name",
                    "facilityName": "Facility",
                    "quantity": st.column_config.NumberColumn("Stock Qty", format="%d"),
                    "reorderLevel": st.column_config.NumberColumn("Reorder Level", format="%d"),
                    "baseUnit": "Unit",
                    "costPrice": st.column_config.NumberColumn("Cost (₦)", format="₦%.2f"),
                    "sellingPrice": st.column_config.NumberColumn("Selling (₦)", format="₦%.2f"),
                    "computedStockValue": st.column_config.NumberColumn("Total Value (₦)", format="₦%.2f"),
                    "isLowStock": st.column_config.CheckboxColumn("Low Stock Alert")
                },
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No inventory items found.")

    with tab_ledger:
        if not df_sls.empty:
            df_sls['billingType'] = df_sls['lineRevenue'].apply(lambda x: "Subsidized/NHIS" if x == 0 else "Standard Billing")
            st.subheader("Pharmacy Transaction Log (Filtered Duration)")
            
            cols_to_display = [
                'transactionDate', 'documentNo', 'itemName', 'facilityName', 
                'sourceClient', 'qtySold', 'unitPrice', 'lineRevenue', 'lineProfit', 'billingType'
            ]
            available_cols = [c for c in cols_to_display if c in df_sls.columns]

            if 'transactionDate' in df_sls.columns and pd.api.types.is_datetime64_any_dtype(df_sls['transactionDate']):
                date_fmt = st.column_config.DatetimeColumn("Date & Time", format="YYYY-MM-DD HH:mm:ss")
            else:
                date_fmt = "Date & Time"

            st.dataframe(
                df_sls[available_cols].sort_values('transactionDate', ascending=False),
                column_config={
                    "transactionDate": date_fmt,
                    "documentNo": "Doc Ref",
                    "itemName": "Medication Name",
                    "facilityName": "Facility Name",
                    "sourceClient": "Patient / Source",
                    "qtySold": st.column_config.NumberColumn("Qty Sold", format="%d"),
                    "unitPrice": st.column_config.NumberColumn("Unit Price (₦)", format="₦%.2f"),
                    "lineRevenue": st.column_config.NumberColumn("Revenue (₦)", format="₦%.2f"),
                    "lineProfit": st.column_config.NumberColumn("Profit (₦)", format="₦%.2f"),
                    "billingType": st.column_config.SelectboxColumn("Billing Type", options=["Subsidized/NHIS", "Standard Billing"])
                },
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No sales transactions found.")
