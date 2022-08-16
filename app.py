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
WINDOW_SIZE = 5

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

total_spending = round(data["Price"].sum(), 2)

TODAY = date.today()
END_DATE = datetime.date(TODAY.year, TODAY.month, calendar.monthrange(TODAY.year, TODAY.month)[1])
remaining_days = (END_DATE - TODAY).days

projected_spending = round(total_spending * END_DATE.day / TODAY.day, 2)
current_progress = int(100 * (TODAY.day / (TODAY.day + remaining_days)))

# Overall budget summary
budget_pie = dbc.Progress(
    value=current_progress,
    label=f"{current_progress}%",
    style={"padding": "0rem 0rem", "margin-left": "0.5rem"}
    )

if projected_spending <= BUDGET:
    budget_pie.color = "success"
elif BUDGET < projected_spending <= WARNING:
    budget_pie.color = "warning"
else:
    budget_pie.color = "danger"

# Per-category budget
per_category = (
    data.groupby("Category")["Price"].sum()
    .reset_index().rename(columns={"Price": "Total"})
)

category_pies = []
category_text = []
category_names = []
for _, i in per_category.iterrows():
    c = i["Category"]
    t = round(i["Total"], 2)
    b = CATEGORY_BUDGETS[c]
    perc = int(100 * t / b)
    category_pie = dbc.Progress(
        value=perc,
        label=f"{perc}%",
        style={"padding": "0rem 0rem", "margin-left": "0.5rem"}
        )
    category_pies.append(category_pie)
    text = f"{CURRENCY}{t} spent out of {CURRENCY}{b}"
    category_text.append(text)
    category_names.append(c)

dbc_categories = [html.Div("Per category spending:")]
for i, j, k in zip(category_pies, category_text, category_names):
    dbc_categories.append(html.Strong(k))
    dbc_categories.append(i)
    dbc_categories.append(html.Div(j, style={"margin-bottom": "0.5rem"}))

# Spending timeline
data["Month"] = data["Date"].dt.month_name()
data["Year"] = data["Date"].dt.year

per_period = (
    data.groupby(by=["Year", "Month"]).sum()
    .reset_index().sort_values(by=["Year", "Month"], ascending=True).tail(WINDOW_SIZE)
)
per_period["Period"] = [
    f"{i} {j}" for i, j in zip(per_period['Month'], per_period['Year'])
]
spending_timeline = per_period.plot.line(x="Period", y="Price", legend=False)
per_period.plot.scatter(x="Period", y="Price", legend=False, ax=spending_timeline)
spending_timeline.set_xlabel(" ")
spending_timeline.set_ylabel("Total spending")
spending_timeline.figure.savefig("spending-timeline.png")

encoded_image = base64.b64encode(open("spending-timeline.png", 'rb').read())

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP, "/css/button.css"]
)

app.title = "Personal Finance Tracker"
server = app.server

app.layout = html.Div(
    [
        dbc.Row(
            [
                dbc.Col(width=1),
                dbc.Col(
                    [
                        dbc.Row(style={"margin-bottom": "5rem"}),
                        dbc.Row(
                            [
                                html.Strong(f"{remaining_days} days left in {TODAY.strftime('%B')}", style={"margin-bottom": "0.5rem"}),
                                budget_pie,
                                html.Div(f"You've spent {int(100 * total_spending / BUDGET)}% of your budget ({CURRENCY}{total_spending} out of {CURRENCY}{BUDGET})",
                                style={"margin-top": "0.5rem"}),
                            ]
                        ),
                        dbc.Row(style={"margin-bottom": "3rem"}),
                        dbc.Row(
                            dbc_categories
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