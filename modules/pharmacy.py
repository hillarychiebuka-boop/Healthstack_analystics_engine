import streamlit as st
import pandas as pd
import plotly.express as px

def format_currency_human(amount):
    if abs(amount) >= 1e9:
        return f"₦{amount / 1e9:,.2f}B"
    elif abs(amount) >= 1e6:
        return f"₦{amount / 1e6:,.2f}M"
    elif abs(amount) >= 1e3:
        return f"₦{amount / 1e3:,.1f}K"
    else:
        return f"₦{amount:,.2f}"

def render_pharmacy_tab(df_inventory, df_sales, selected_facility):
    st.markdown("## 💊 Pharmacy Operations & Inventory Analytics")
    st.markdown("Real-time executive intelligence across drug stock balances, reorder risk levels, sales velocity, and profit margins.")

    if df_inventory.empty and df_sales.empty:
        st.warning(f"No inventory or sales records found for {selected_facility}.")
        return

    # --- 1. Executive Metrics ---
    total_val = df_inventory['computedStockValue'].sum() if not df_inventory.empty else 0
    total_items = len(df_inventory) if not df_inventory.empty else 0
    low_stock_cnt = df_inventory['isLowStock'].sum() if not df_inventory.empty else 0
    
    total_revenue = df_sales['lineRevenue'].sum() if not df_sales.empty else 0
    total_profit = df_sales['lineProfit'].sum() if not df_sales.empty else 0
    profit_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0

    kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
    kpi1.metric("📦 Inventory Portfolio", format_currency_human(total_val), help=f"Exact Value: ₦{total_val:,.2f}")
    kpi2.metric("🏷️ Tracked SKUs", f"{total_items:,}")
    kpi3.metric("⚠️ Reorder / Low Stock", f"{low_stock_cnt:,}", delta="-Risk Alert" if low_stock_cnt > 0 else "Optimal", delta_color="inverse")
    kpi4.metric("💳 Pharmacy Revenue", format_currency_human(total_revenue), help=f"Exact Revenue: ₦{total_revenue:,.2f}")
    kpi5.metric("📈 Gross Margin", f"{profit_margin:.1f}%", delta=f"{format_currency_human(total_profit)} Profit")

    st.markdown("---")

    # --- 2. Analytics Charts ---
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.markdown("**🔥 Fast-Moving Medications (Top 10 Volume)**")
        if not df_sales.empty:
            top_sales = df_sales.groupby("itemName")["qtySold"].sum().reset_index()
            top_sales = top_sales.sort_values("qtySold", ascending=False).head(10)
            
            fig_sales = px.bar(
                top_sales,
                x="qtySold",
                y="itemName",
                orientation="h",
                text_auto=".2s",
                labels={"qtySold": "Units Dispensed", "itemName": "Medication Name"},
                color="qtySold",
                color_continuous_scale="Viridis"
            )
            fig_sales.update_layout(yaxis={'categoryorder': 'total ascending'}, margin=dict(l=20, r=20, t=20, b=20))
            st.plotly_chart(fig_sales, use_container_width=True)

    with col_chart2:
        st.markdown("**💰 Top Revenue Generating Medications**")
        if not df_sales.empty:
            top_rev = df_sales.groupby("itemName")["lineRevenue"].sum().reset_index()
            top_rev = top_rev.sort_values("lineRevenue", ascending=False).head(10)
            
            fig_rev = px.bar(
                top_rev,
                x="lineRevenue",
                y="itemName",
                orientation="h",
                text_auto=".2s",
                labels={"lineRevenue": "Revenue (₦)", "itemName": "Medication Name"},
                color="lineRevenue",
                color_continuous_scale="Tealgrn"
            )
            fig_rev.update_layout(yaxis={'categoryorder': 'total ascending'}, margin=dict(l=20, r=20, t=20, b=20))
            st.plotly_chart(fig_rev, use_container_width=True)

    st.markdown("---")

    # --- 3. Operational Master Tables ---
    tab_inv, tab_ledger = st.tabs(["📋 Inventory Master & Stock Alerts", "🧾 Dispensing & Sales Ledger"])

    with tab_inv:
        if not df_inventory.empty:
            st.subheader("Inventory Stock Audit")
            filter_low = st.checkbox("Show Only Reorder/Low Stock Items", value=False)
            display_inv = df_inventory[df_inventory['isLowStock'] == True] if filter_low else df_inventory
            
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
                    "costPrice": st.column_config.NumberColumn("Cost (₦)", format="₦%.2f"),
                    "sellingPrice": st.column_config.NumberColumn("Selling (₦)", format="₦%.2f"),
                    "computedStockValue": st.column_config.NumberColumn("Total Value (₦)", format="₦%.2f"),
                    "isLowStock": st.column_config.CheckboxColumn("Low Stock Alert")
                },
                use_container_width=True,
                hide_index=True
            )

    with tab_ledger:
        df_sales['billingType'] = df_sales['lineRevenue'].apply(lambda x: "Subsidized/NHIS" if x == 0 else "Standard Billing")
        if not df_sales.empty:
            st.subheader("Pharmacy Transaction Log")
            st.dataframe(
                df_sales[[
                    'transactionDate', 'documentNo', 'itemName', 'facilityName', 
                    'sourceClient', 'qtySold', 'unitPrice', 'lineRevenue', 'lineProfit', 'billingType'
                ]],
                column_config={
                    "transactionDate": st.column_config.DatetimeColumn("Date & Time", format="YYYY-MM-DD HH:mm"),
                    "documentNo": "Doc Ref",
                    "itemName": "Medication Name",
                    "facilityName": "Facility",
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