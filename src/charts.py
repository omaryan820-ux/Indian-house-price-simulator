import plotly.graph_objects as go
import streamlit as st

BLUE = "#1D5FD0"
LIGHT_BLUE = "#8FB6F5"
AMBER = "#D98A00"
RED = "#C53030"


def chart_title(text):
    """Title shown above a chart as normal text, so it wraps on small screens."""
    st.markdown("**" + text + "**")


def show(fig):
    """Draw a chart with a small toolbar: zoom in/out, autoscale, reset."""
    config = {
        "displaylogo": False,
        "displayModeBar": True,
        "modeBarButtons": [["zoomIn2d", "zoomOut2d", "autoScale2d", "resetScale2d"]],
    }
    st.plotly_chart(fig, width="stretch", config=config)


def style(fig, height=380):
    """Same clean look for every chart."""
    fig.update_layout(
        height=height, margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor="white", plot_bgcolor="white",
        font=dict(family="Inter, Segoe UI, sans-serif", color="#111827"),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0),
        dragmode=False,
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="#E5E7EB")
    return fig


def heatmap(matrix, text_matrix, x_title, y_title, colorscale="Blues", height=320):
    """matrix = numbers for colour, text_matrix = the text to print in each cell."""
    fig = go.Figure(go.Heatmap(
        z=matrix.values, x=[str(c) for c in matrix.columns], y=[str(i) for i in matrix.index],
        text=text_matrix, texttemplate="%{text}", colorscale=colorscale, showscale=False,
        hoverinfo="skip",
    ))
    fig.update_xaxes(title=x_title, side="bottom")
    fig.update_yaxes(title=y_title)
    return style(fig, height)