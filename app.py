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
import altair as alt

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP, "/css/button.css"]
)

app.title = "Personal Finance Tracker"
server = app.server

# Constants
BUDGET = 1500
WARNING = 1600
CURRENCY = "$"
WINDOW_SIZE = 12

N_CATEGORIES = 5
EATING_OUT_BUDGET = 550
GROCERIES_BUDGET = 500
TRANSPORT_BUDGET = 100
ENTERTAINMENT_BUDGET = 100
MISC_BUDGET = 250
CATEGORY_BUDGETS = {
    "Eating out": EATING_OUT_BUDGET,
    "Groceries": GROCERIES_BUDGET,
    "Transport": TRANSPORT_BUDGET,
    "Entertainment": ENTERTAINMENT_BUDGET,
    "Misc.": MISC_BUDGET
}
EXCLUDED_CATEGORY = ["Holiday"]

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
data["Month"] = data["Date"].dt.month
data["Year"] = data["Date"].dt.year

unique_holidays = data["Notes"].dropna().unique().tolist()

per_period = (
    data.groupby(by=["Year", "Month"]).sum()
    .reset_index().sort_values(by=["Year", "Month"], ascending=True).tail(WINDOW_SIZE)
)
per_period["Month"] = [datetime.datetime.strptime(str(i), "%m") for i in per_period["Month"]]
per_period["Month"] = per_period["Month"].dt.month_name()

per_period["Period"] = [
    f"{i} {j}" for i, j in zip(per_period['Month'], per_period['Year'])
]

available_months = list(per_period["Period"].unique())

if f"{TODAY.strftime('%B')} {TODAY.year}" not in available_months:
    available_months.append(f"{TODAY.strftime('%B')} {TODAY.year}")

data["Month"] = [datetime.datetime.strptime(str(i), "%m") for i in data["Month"]]
data["Month"] = data["Month"].dt.month_name()

# Days left in the month
@app.callback(
    [
        Output("strong-remaining-days", "children"),
        Output("budget-pie", "value"),
        Output("budget-pie", "label"),
        Output("budget-pie", "color"),
        Output("spend-amount", "children")
    ],
    [
        Input("select-period", "value"),
        Input("include-holiday", "value")
    ]
)
def update_remaining_days(value, include_holiday):
    END_DATE = datetime.date(TODAY.year, TODAY.month, calendar.monthrange(TODAY.year, TODAY.month)[1])

    if value is None:
        period_data = data
        month = TODAY.strftime('%B')
        year = TODAY.year
    else:
        month, year = value.split()
        period_data = get_period_data(month, int(year))

    if not include_holiday:
        period_data = period_data[period_data["Notes"].isna()]

    total_spending = round(period_data["Price"].sum(), 2)
    projected_spending = round(total_spending * END_DATE.day / TODAY.day, 2)

    if projected_spending <= BUDGET:
        budget_pie_color = "success"
    elif BUDGET < projected_spending <= WARNING:
        budget_pie_color = "warning"
    else:
        budget_pie_color = "danger"

    if not month == TODAY.strftime('%B') and not year == TODAY.year:

        if total_spending < BUDGET:
            budget_pie_color = "success"
        elif total_spending == BUDGET:
            budget_pie_color = "warning"
        else:
            budget_pie_color = "danger"

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


# Top items in period
@app.callback(
    Output("top-items", "children"),
    [Input("select-period", "value"), Input("include-holiday", "value")]
)
def find_top_items(value, include_holiday):
    if value is None:
        period_data = data
    else:
        month, year = value.split()
        period_data = get_period_data(month, int(year))

    if not include_holiday:
        period_data = period_data[period_data["Notes"].isna()]

    top_items = period_data.groupby(by="Item")["Price"].sum().reset_index().sort_values("Price", ascending=False)["Item"].head(5).tolist()
    children = [html.Li(i) for i in top_items]

    return children

# Eating out spending
@app.callback(
    [Output("eating-out-progress", "value"), Output("eating-out-progress", "label"), Output("eating-out-text", "children")],
    [Input("select-period", "value"), Input("include-holiday", "value")]
)
def update_eating_out(value, include_holiday):
    if value is None:
        period_data = data
    else:
        month, year = value.split()
        period_data = get_period_data(month, int(year))

    if not include_holiday:
        period_data = period_data[period_data["Notes"].isna()].copy()

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
    [Input("select-period", "value"), Input("include-holiday", "value")]
)
def update_groceries(value, include_holiday):
    if value is None:
        period_data = data
    else:
        month, year = value.split()
        period_data = get_period_data(month, int(year))

    if not include_holiday:
        period_data = period_data[period_data["Notes"].isna()].copy()

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
    [Input("select-period", "value"), Input("include-holiday", "value")]
)
def update_groceries(value, include_holiday):
    if value is None:
        period_data = data
    else:
        month, year = value.split()
        period_data = get_period_data(month, int(year))

    if not include_holiday:
        period_data = period_data[period_data["Notes"].isna()].copy()
    
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
    [Input("select-period", "value"), Input("include-holiday", "value")]
)
def update_groceries(value, include_holiday):
    if value is None:
        period_data = data
    else:
        month, year = value.split()
        period_data = get_period_data(month, int(year))

    if not include_holiday:
        period_data = period_data[period_data["Notes"].isna()].copy()
    
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
    [Input("select-period", "value"), Input("include-holiday", "value")]
)
def update_groceries(value, include_holiday):
    if value is None:
        period_data = data
    else:
        month, year = value.split()
        period_data = get_period_data(month, int(year))
    
    if not include_holiday:
        period_data = period_data[period_data["Notes"].isna()].copy()
    
    cat_data = period_data.query("Category == 'Misc.'")

    cat_total = round(cat_data["Price"].sum(), 2)
    perc_budget = int(100 * cat_total / CATEGORY_BUDGETS["Misc."])

    return (perc_budget,
    f"{perc_budget}%",
    f"{CURRENCY}{cat_total} spent out of {CURRENCY}{CATEGORY_BUDGETS['Misc.']}"
    )


# Spending timeline
@app.callback(
    Output("spending-timeline", "srcDoc"),
    [Input("select-category", "value"), Input("include-holiday", "value")]
)
def plot_spending_timeline(value, include_holiday):
    data["Period"] = [f"{i} {j}" for i, j in zip(data["Month"], data["Year"])]
    my_df = data.sort_values("Date", ascending=True).set_index("Date").last(f"{WINDOW_SIZE}M").reset_index()

    eligible_periods = my_df["Period"].unique().tolist()
    eligible_periods_df = pd.DataFrame({
        "Period": eligible_periods
    })

    my_df = data[data["Period"].isin(eligible_periods)]

    if value is not None:
        my_title = value
        timeline_data = my_df.query("Category == @value")
    else:
        my_title = "All categories"
        timeline_data = my_df

    if not include_holiday:
        timeline_data = timeline_data[timeline_data["Notes"].isna()].copy()

    timeline_data["Month"] = timeline_data["Date"].dt.month
    timeline_data = (
        timeline_data.groupby(by=["Year", "Month"]).sum()
        .reset_index().sort_values(by=["Year", "Month"], ascending=True)
    )

    timeline_data["Month"] = [datetime.datetime.strptime(str(i), "%m") for i in timeline_data["Month"]]
    timeline_data["Month"] = timeline_data["Month"].dt.month_name()

    timeline_data["Period"] = [f"{i} {j}" for i, j in zip(timeline_data['Month'], timeline_data['Year'])]

    timeline_data = timeline_data.merge(eligible_periods_df, on="Period", how="outer")
    timeline_data = timeline_data.fillna(0)

    if value is not None:
        timeline_data["exceed_budget"] = timeline_data["Price"] > CATEGORY_BUDGETS[value]
    else:
        timeline_data["exceed_budget"] = timeline_data["Price"] > BUDGET

    chart = alt.Chart(timeline_data).mark_line().encode(
        alt.X("Period", title=None, sort=timeline_data["Period"].tolist()),
        alt.Y("Price", title="Total spent", axis=alt.Axis(format='~s'), scale=alt.Scale(zero=False))
    ).properties(
        width=350,
        height=175,
        title=my_title
    )

    points = alt.Chart(timeline_data).mark_square(size=60).encode(
        alt.X("Period", title=None, sort=timeline_data["Period"].tolist()),
        alt.Y("Price", title="Total spent"),
        alt.Color("exceed_budget:Q", scale=alt.Scale(scheme='redyellowgreen', domain=[1, 0]), legend=None)
    )

    flag = True

    if value is not None:
        if timeline_data["Price"].max() < 0.9 * CATEGORY_BUDGETS[value]:
            flag = False
        budget = alt.Chart(pd.DataFrame({'y': [CATEGORY_BUDGETS[value]]})).mark_rule(strokeDash=[2,5]).encode(y='y')
    else:
        if timeline_data["Price"].max() < 0.9 * BUDGET:
            flag = False
        budget = alt.Chart(pd.DataFrame({'y': [BUDGET]})).mark_rule(strokeDash=[2,5]).encode(y='y')

    if flag:
        return (chart + points + budget).to_html()
    else:
        return (chart + points).to_html()


# Holiday total
@app.callback(
    Output("holiday-total", "children"),
    Input("select-holiday", "value")
)
def get_total(value):
    return f"Total spending: {CURRENCY}{data[data['Notes'] == value]['Price'].sum()}"


# Top items in holiday
@app.callback(
    Output("top-items-holiday", "children"),
    Input("select-holiday", "value")
)
def find_top_items(value):
    top_items = data[data["Notes"] == value].groupby(by="Item")["Price"].sum().reset_index().sort_values("Price", ascending=False)["Item"].head(6).tolist()
    children = [html.Li(i) for i in top_items[1:]]

    return children

# Holiday bar chart
@app.callback(
    Output("holiday-bar", "srcDoc"),
    Input("select-holiday", "value")
)
def plot_spending_timeline(value):
    my_df = data[data["Notes"] == value].groupby("Category")["Price"].sum().reset_index()
    my_df.columns = ["Category", "Total"]

    chart = alt.Chart(my_df).mark_bar().encode(
        alt.Y("Category", title=None, sort="x"),
        alt.X("Total", title="Total spent"),
        alt.Color("Category", title=None, legend=None)
    ).properties(
        width=300,
        height=150
    )

    return chart.to_html()


app.layout = html.Div(
    [
        dcc.Tabs([
            dcc.Tab(
                label="Regular",
                children=[
                    dbc.Row(
                        [
                            dbc.Col(width=1),
                            dbc.Col(
                                [
                                    dbc.Row(style={"margin-bottom": "2rem"}),
                                    dbc.Row(
                                        [
                                            dcc.Dropdown(
                                                id="select-period",
                                                placeholder="Select a month",
                                                value=f"{TODAY.strftime('%B')} {TODAY.year}",
                                                options=[
                                                    {"label": i, "value": i} for i in available_months
                                                ]
                                            ),
                                            html.Div(style={"margin-bottom": "0.5rem"}),
                                            dcc.Checklist(
                                                id="include-holiday",
                                                options=[
                                                    {"label": " Include holiday", "value": "True"},
                                                ],
                                                value=["True"]
                                            )
                                        ],
                                        style={"margin-bottom": "2rem"}
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
                            dbc.Col(width=1),
                            dbc.Col(
                                [
                                    html.Strong("Top items spent on this period:"),
                                    html.Div(style={"margin-bottom": "0.5rem"}),
                                    html.Ol(
                                        children=[html.Li("Placeholder top item")],
                                        id="top-items",
                                    ),
                                    html.Div(style={"margin-bottom": "4rem"}),
                                    dbc.Row(
                                        dcc.Dropdown(
                                            id="select-category",
                                            placeholder="Select a category",
                                            value=None,
                                            options=[
                                                {"label": i, "value": i} for i in CATEGORIES.keys() if not i in EXCLUDED_CATEGORY
                                            ]
                                        )
                                    ),
                                    html.Div(style={"margin-bottom": "2rem"}),
                                    dbc.Row(
                                        html.Div(
                                            html.Iframe(
                                                id="spending-timeline",
                                                # srcDoc=plot_spending_timeline(),
                                                style={"border-width": "0", "width": "100rem", "height": "200%"}
                                            )
                                        )
                                    )
                                ],
                                width=5),
                            dbc.Col(width=1)
                        ],
                        align="center"
                    )
                ]
            ),
            dcc.Tab(label="Holiday", children=[
                dbc.Row(
                        [
                            dbc.Col(width=1),
                            dbc.Col(
                                [
                                    dbc.Row(style={"margin-bottom": "2rem"}),
                                    dbc.Row(
                                        dcc.Dropdown(
                                            id="select-holiday",
                                            placeholder="Select a holiday",
                                            value=unique_holidays[-1],
                                            options=[
                                                {"label": i, "value": i} for i in unique_holidays
                                            ]
                                        ),
                                        style={"margin-bottom": "2rem"}
                                    ),
                                    dbc.Row(
                                        html.Div("Placeholder spend amount", id="holiday-total"),
                                        style={"margin-bottom": "2rem"}
                                    ),
                                    dbc.Row(
                                        [
                                            html.Div("Per category spending:"),
                                            dbc.Row(
                                            html.Div(
                                                html.Iframe(
                                                    id="holiday-bar",
                                                    style={"border-width": "0", "width": "100rem", "height": "200%"}
                                                )
                                            )
                                    )
                                        ]
                                    ),
                                ],
                                width=4
                                ),
                            dbc.Col(width=1),
                            dbc.Col(
                                [
                                    html.Strong("Top items spent on this holiday:"),
                                    html.Div(style={"margin-bottom": "0.5rem"}),
                                    html.Ol(
                                        children=[html.Li("Placeholder top item")],
                                        id="top-items-holiday",
                                    ),
                                    html.Div(style={"margin-bottom": "4rem"})
                                ],
                                width=5),
                            dbc.Col(width=1)
                        ],
                        align="center"
                    )
            ])
        ])
    ]
)

if __name__ == '__main__':
    app.run_server(debug=True)


