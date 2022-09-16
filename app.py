import dash
from dash import html
from dash import dcc
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output

import pandas as pd
import datetime
from datetime import date
import calendar
import json
import base64
import altair as alt

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP, "/css/button.css"]
)

app.title = "Personal Finance Tracker"
server = app.server

LEFT_STYLE = {
    "background-color": "#0000ff",
    'border': '1px solid #d3d3d3'
}

RIGHT_STYLE = {
    "top": 0,
    "right": 0,
    "left": 0,
    "height": "2rem",
    "margin-right": "10rem",
    "padding": "0rem 0rem",
    "background-color": "#0000ff",
    'border': '1px solid #d3d3d3'
}

# Constants
BUDGET = 1500
WARNING = 1600
CURRENCY = "$"
WINDOW_SIZE = 12

N_CATEGORIES = 5
EATING_OUT_BUDGET = 600
GROCERIES_BUDGET = 600
TRANSPORT_BUDGET = 100
ENTERTAINMENT_BUDGET = 100
MISC_BUDGET = 100
CATEGORY_BUDGETS = {
    "Eating out": EATING_OUT_BUDGET,
    "Groceries": GROCERIES_BUDGET,
    "Transport": TRANSPORT_BUDGET,
    "Entertainment": ENTERTAINMENT_BUDGET,
    "Misc.": MISC_BUDGET
}

if sum(CATEGORY_BUDGETS.values()) > BUDGET:
    print("Budget allocation incorrect")

TODAY = date.today()
END_DATE = datetime.date(TODAY.year, TODAY.month, calendar.monthrange(TODAY.year, TODAY.month)[1])

def get_period_data(month, year):
    return data[
        (data["Month"] == month) &
        (data["Year"] == year)
        ]

# Read data
data = pd.read_csv("finances.csv")
data[["Date"]] = data[["Date"]].fillna(method="ffill")
data["Date"] = pd.to_datetime(data["Date"])

# Load known categories and merchants
with open('categories.json', 'r') as f:
    CATEGORIES = json.load(f)

ALL_MERCHANTS = {i for j in CATEGORIES.values() for i in j}

flag_merchant = False
for i in data["Item"].unique():
    if i not in ALL_MERCHANTS:
        flag_merchant = True
        print(f"{i} is a new merchant")

if not flag_merchant:
    print("All merchants accounted for")

data_categories = []
for i in data["Item"]:
    for j in list(CATEGORIES.keys()):
        if i in CATEGORIES[j]:
            data_categories.append(j)
            break
data["Category"] = data_categories

data["Month"] = data["Date"].dt.month_name()
data["Year"] = data["Date"].dt.year

per_period = (
    data.groupby(by=["Year", "Month"]).sum()
    .reset_index().sort_values(by=["Year", "Month"], ascending=True).tail(WINDOW_SIZE)
)
per_period["Period"] = [
    f"{i} {j}" for i, j in zip(per_period['Month'], per_period['Year'])
]

available_months = list(per_period["Period"].unique())

# Days left in the month
@app.callback(
    [
        Output("strong-remaining-days", "children"),
        Output("budget-pie", "value"),
        Output("budget-pie", "label"),
        Output("budget-pie", "color"),
        Output("spend-amount", "children")
    ],
    Input("select-period", "value")
)
def update_remaining_days(value):
    END_DATE = datetime.date(TODAY.year, TODAY.month, calendar.monthrange(TODAY.year, TODAY.month)[1])
    month, year = value.split()
    period_data = get_period_data(month, int(year))
    total_spending = round(period_data["Price"].sum(), 2)
    projected_spending = round(total_spending * END_DATE.day / TODAY.day, 2)

    if projected_spending <= BUDGET:
        budget_pie_color = "success"
    elif BUDGET < projected_spending <= WARNING:
        budget_pie_color = "warning"
    else:
        budget_pie_color = "danger"

    if not month == TODAY.strftime('%B') and not year == TODAY.year:
        return (
            f"0 days left in {month} {year}",
            100,
            f"100% of the month",
            budget_pie_color,
            f"You've spent {int(100 * total_spending / BUDGET)}% of your budget "
            f"({CURRENCY}{total_spending} out of {CURRENCY}{BUDGET})")
    else:
        END_DATE = datetime.date(TODAY.year, TODAY.month, calendar.monthrange(TODAY.year, TODAY.month)[1])
        remaining_days = (END_DATE - TODAY).days
        current_progress = int(100 * (TODAY.day / (TODAY.day + remaining_days)))
        return (
            f"{remaining_days} days left in {TODAY.strftime('%B')} {TODAY.year}",
            current_progress,
            f"{current_progress}% of the month",
            budget_pie_color,
            f"You've spent {int(100 * total_spending / BUDGET)}% of your budget "
            f"({CURRENCY}{total_spending} out of {CURRENCY}{BUDGET})"
            )

# Eating out spending
@app.callback(
    [Output("eating-out-progress", "value"), Output("eating-out-progress", "label"), Output("eating-out-text", "children")],
    Input("select-period", "value")
)
def update_eating_out(value):
    month, year = value.split()
    period_data = get_period_data(month, int(year))
    cat_data = period_data.query("Category == 'Eating out'")

    cat_total = round(cat_data["Price"].sum(), 2)
    perc_budget = int(100 * cat_total / CATEGORY_BUDGETS["Eating out"])

    return (perc_budget,
    f"{perc_budget}%",
    f"{CURRENCY}{cat_total} spent out of {CURRENCY}{CATEGORY_BUDGETS['Eating out']}"
    )


# Groceries spending
@app.callback(
    [Output("groceries-progress", "value"), Output("groceries-progress", "label"), Output("groceries-text", "children")],
    Input("select-period", "value")
)
def update_groceries(value):
    month, year = value.split()
    period_data = get_period_data(month, int(year))
    cat_data = period_data.query("Category == 'Groceries'")

    cat_total = round(cat_data["Price"].sum(), 2)
    perc_budget = int(100 * cat_total / CATEGORY_BUDGETS["Groceries"])

    return (perc_budget,
    f"{perc_budget}%",
    f"{CURRENCY}{cat_total} spent out of {CURRENCY}{CATEGORY_BUDGETS['Groceries']}"
    )


# Entertainment spending
@app.callback(
    [Output("entertainment-progress", "value"), Output("entertainment-progress", "label"), Output("entertainment-text", "children")],
    Input("select-period", "value")
)
def update_groceries(value):
    month, year = value.split()
    period_data = get_period_data(month, int(year))
    cat_data = period_data.query("Category == 'Entertainment'")

    cat_total = round(cat_data["Price"].sum(), 2)
    perc_budget = int(100 * cat_total / CATEGORY_BUDGETS["Entertainment"])

    return (perc_budget,
    f"{perc_budget}%",
    f"{CURRENCY}{cat_total} spent out of {CURRENCY}{CATEGORY_BUDGETS['Entertainment']}"
    )


# Transport spending
@app.callback(
    [Output("transport-progress", "value"), Output("transport-progress", "label"), Output("transport-text", "children")],
    Input("select-period", "value")
)
def update_groceries(value):
    month, year = value.split()
    period_data = get_period_data(month, int(year))
    cat_data = period_data.query("Category == 'Transport'")

    cat_total = round(cat_data["Price"].sum(), 2)
    perc_budget = int(100 * cat_total / CATEGORY_BUDGETS["Transport"])

    return (perc_budget,
    f"{perc_budget}%",
    f"{CURRENCY}{cat_total} spent out of {CURRENCY}{CATEGORY_BUDGETS['Transport']}"
    )


# Misc spending
@app.callback(
    [Output("misc-progress", "value"), Output("misc-progress", "label"), Output("misc-text", "children")],
    Input("select-period", "value")
)
def update_groceries(value):
    month, year = value.split()
    period_data = get_period_data(month, int(year))
    cat_data = period_data.query("Category == 'Misc.'")

    cat_total = round(cat_data["Price"].sum(), 2)
    perc_budget = int(100 * cat_total / CATEGORY_BUDGETS["Misc."])

    return (perc_budget,
    f"{perc_budget}%",
    f"{CURRENCY}{cat_total} spent out of {CURRENCY}{CATEGORY_BUDGETS['Misc.']}"
    )



# def plot_spending_timeline():
#     timeline_data = data.sort_values("Date", ascending=True).set_index("Date").last(f"{WINDOW_SIZE}M")

#     chart = (alt.Chart(data))


# plot_spending_timeline()

# # Spending timeline
# spending_timeline = per_period.plot.line(x="Period", y="Price", legend=False)
# per_period.plot.scatter(x="Period", y="Price", legend=False, ax=spending_timeline)
# spending_timeline.set_xlabel(" ")
# spending_timeline.set_ylabel("Total spending")
# spending_timeline.figure.savefig("spending-timeline.png")

# encoded_image = base64.b64encode(open("spending-timeline.png", 'rb').read())

app.layout = html.Div(
    [
        dbc.Row(
            [
                dbc.Col(width=1),
                dbc.Col(
                    [
                        dbc.Row(style={"margin-bottom": "2rem"}),
                        dbc.Row(
                            dcc.Dropdown(
                                id="select-period",
                                placeholder="Select a month",
                                value=f"{TODAY.strftime('%B')} {TODAY.year}",
                                options=[
                                    {"label": i, "value": i} for i in available_months
                                ]
                            ), style={"margin-bottom": "2rem"}
                        ),
                        dbc.Row(
                            html.Div(id='my-output')
                        ),
                        dbc.Row(
                            [
                                html.Div(html.Strong("Placeholder days remaining", id="strong-remaining-days")),
                                html.Div(style={"margin-bottom": "0.5rem"}),
                                dbc.Progress(
                                    id="budget-pie",
                                    value=0,
                                    label="Placeholder % month remaining",
                                    style={"padding": "0rem 0rem", "margin-left": "0.5rem"}
                                ),
                                html.Div(style={"margin-bottom": "0.5rem"}),
                                html.Div("Placeholder spend amount", id="spend-amount"),
                            ]
                        ),
                        dbc.Row(style={"margin-bottom": "3rem"}),
                        dbc.Row(
                            [
                                html.Div("Per category spending:"),

                                html.Strong("Eating out"),
                                dbc.Progress(
                                    id="eating-out-progress",
                                    value=0,
                                    label=f"{0}%",
                                    style={"padding": "0rem 0rem", "margin-left": "0.5rem"}
                                ),
                                html.Div("Placeholder eating out", id="eating-out-text"),
                                html.Div(style={"margin-bottom": "0.5rem"}),

                                html.Strong("Groceries"),
                                dbc.Progress(
                                    id="groceries-progress",
                                    value=0,
                                    label=f"{0}%",
                                    style={"padding": "0rem 0rem", "margin-left": "0.5rem"}
                                ),
                                html.Div("Placeholder groceries", id="groceries-text"),
                                html.Div(style={"margin-bottom": "0.5rem"}),

                                html.Strong("Entertainment"),
                                dbc.Progress(
                                    id="entertainment-progress",
                                    value=0,
                                    label=f"{0}%",
                                    style={"padding": "0rem 0rem", "margin-left": "0.5rem"}
                                ),
                                html.Div("Placeholder entertainment", id="entertainment-text"),
                                html.Div(style={"margin-bottom": "0.5rem"}),

                                html.Strong("Transport"),
                                dbc.Progress(
                                    id="transport-progress",
                                    value=0,
                                    label=f"{0}%",
                                    style={"padding": "0rem 0rem", "margin-left": "0.5rem"}
                                ),
                                html.Div("Placeholder transport", id="transport-text"),
                                html.Div(style={"margin-bottom": "0.5rem"}),

                                html.Strong("Misc."),
                                dbc.Progress(
                                    id="misc-progress",
                                    value=0,
                                    label=f"{0}%",
                                    style={"padding": "0rem 0rem", "margin-left": "0.5rem"}
                                ),
                                html.Div("Placeholder misc", id="misc-text")
                            ]
                        ),
                    ],
                    width=4
                    ),
                dbc.Col(width=2),
                dbc.Col(
                    [
                        html.Div("Something"),
                        html.Div("Spending timeline")
                    ],
                    width=4, style={"border": "1px solid #eeeeee"}),
                dbc.Col(width=1)
            ],
            align="center"
        )
    ]
)

if __name__ == '__main__':
    app.run_server(debug=True)


