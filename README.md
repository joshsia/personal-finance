# Personal finance tracking tool

Developer: Joshua Sia

## About

Find out what your spending habits are like!

![screenshot](https://github.com/joshsia/personal-finance/blob/main/app-screenshot.png)

## How to use

1. Clone this repository
2. Navigate to the repository
3. Download necessary packages by running in the terminal:
```sh
conda env create -f personal-finance.yaml
```
4. Create your own `finances.csv` file or replace the data in `sample-finances.csv`
5. Activate the conda environment using
```sh
conda activate personal-finance
```
6. Run the dashboard using the following command and find where the app is running
```sh
python app.py
Dash is running on http://127.0.0.1:8050/
```
7. Go to the dashboard (typically `http://127.0.0.1:8050/`)

If you created your own `finances.csv`, then modify line 71 of `app.py` to read data from `finances.csv`.

If the app is running properly, you should see the message "All merchants accounted for" in the terminal. Otherwise, you will need to manually add new merchants to `categories.json`.
