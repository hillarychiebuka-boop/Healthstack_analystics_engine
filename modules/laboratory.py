import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

def render_laboratory_tab(df_lab, selected_facility="All Facilities"):
    """
    Renders the Laboratory & Diagnostic Operations Analytics Module.
    """
    st.subheader("🔬 Laboratory & Diagnostics Operations Engine")
    st.markdown("Real-time operational tracking for diagnostic orders, fulfillment efficiency, turnaround times, and facility workloads.")

    if df_lab.empty:
        st.warning("⚠️ No diagnostic or laboratory records available for the selected facility.")
        return

    # --- KPI METRICS CARDS ---
    total_orders = len(df_lab)
    completed_orders = int(df_lab['isFulfilled'].sum())
    pending_orders = total_orders - completed_orders
    fulfillment_rate = (completed_orders / total_orders * 100) if total_orders > 0 else 0.0
    avg_tat = df_lab['valid_tat_hours'].mean()

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Total Diagnostic Orders", f"{total_orders:,}")
    m2.metric("Completed / Verified", f"{completed_orders:,}")
    m3.metric("Pending Fulfillment", f"{pending_orders:,}")
    m4.metric("Fulfillment Rate", f"{fulfillment_rate:.1f}%")
    m5.metric("Avg Turnaround Time", f"{avg_tat:.2f} hrs" if pd.notnull(avg_tat) else "N/A")
    

    st.markdown("---")

    # --- CHARTS SECTION 1: TOP TESTS & STATUS DISTRIBUTION ---
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("📊 Top 10 Requested Investigations")
        top_tests = df_lab['testName'].value_counts().head(10).reset_index()
        top_tests.columns = ['Test Name', 'Order Count']
        
        fig_tests = px.bar(
            top_tests,
            x='Order Count',
            y='Test Name',
            orientation='h',
            color='Order Count',
            color_continuous_scale='Tealgrn',
            text='Order Count'
        )
        fig_tests.update_layout(
            yaxis={'categoryorder': 'total ascending'},
            showlegend=False,
            height=380,
            margin=dict(l=10, r=10, t=30, b=10)
        )
        st.plotly_chart(fig_tests, use_container_width=True)

    with c2:
        st.subheader("📈 Diagnostic Fulfillment Breakdown")
        status_counts = df_lab['status'].astype(str).str.title().value_counts().reset_index()
        status_counts.columns = ['Status', 'Count']

        fig_pie = px.pie(
            status_counts,
            names='Status',
            values='Count',
            hole=0.45,
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        fig_pie.update_layout(height=380, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig_pie, use_container_width=True)

    # --- CHARTS SECTION 2: WORKLOAD BY FACILITY & TAT DISTRIBUTION ---
    if selected_facility == "All Facilities":
        st.markdown("---")
        st.subheader("🏢 Diagnostic Workload & Fulfillment Rate Across Facilities")
        
        fac_summary = df_lab.groupby('facilityName').agg(
            Total_Orders=('isFulfilled', 'count'),
            Completed=('isFulfilled', 'sum')
        ).reset_index()
        fac_summary['Fulfillment_Rate'] = (fac_summary['Completed'] / fac_summary['Total_Orders']) * 100
        fac_summary = fac_summary.sort_values('Total_Orders', ascending=False).head(12)

        fig_fac = go.Figure()
        fig_fac.add_trace(go.Bar(
            x=fac_summary['facilityName'],
            y=fac_summary['Total_Orders'],
            name='Total Orders',
            marker_color='#1f77b4'
        ))
        fig_fac.add_trace(go.Bar(
            x=fac_summary['facilityName'],
            y=fac_summary['Completed'],
            name='Completed Tests',
            marker_color='#2ca02c'
        ))
        fig_fac.update_layout(
            barmode='group',
            xaxis_tickangle=-45,
            height=400,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_fac, use_container_width=True)

    # --- DETAILED DATA TABLE ---
    st.markdown("---")
    st.subheader("📑 Real-Time Laboratory & Diagnostic Records")
    
    display_df = df_lab[['orderDate', 'testName', 'facilityName', 'status', 'tat_hours', 'doctor', 'rawDiagnosis']].copy()
    display_df['status'] = display_df['status'].astype(str).str.title()
    
    st.dataframe(
        display_df,
        column_config={
            "orderDate": st.column_config.DatetimeColumn("Order Timestamp", format="DD/MM/YYYY HH:mm"),
            "testName": "Investigation Name",
            "facilityName": "Facility Location",
            "status": "Order Status",
            "tat_hours": st.column_config.NumberColumn("Turnaround (Hrs)", format="%.2f"),
            "doctor": "Ordering Clinician",
            "rawDiagnosis": "Associated Clinical Diagnosis"
        },
        use_container_width=True,
        height=380
    )