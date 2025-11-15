"""
    -   Parses originally scraped data and separates columns into their own respective columns (ex. significant strikes landed goes from "1 of 20" 
            to significant strikes attempted "1" and significant strikes landed "20")
    -   Converts to usable types for database
"""
import pandas as pd
from config import DATARAWPATH, DATACLEANPATH


def convert_to_inches(value_to_conv):
    """
        -   Converts passed object to inches
        -   RETURNS: total inches
    """
    if value_to_conv != '--':
        stripped_str = value_to_conv.replace("'", '').replace('"', '')  # Removes ' and " from string
        split_str = stripped_str.split(' ')
        feet = int(split_str[0])
        inches = int(split_str[1])
        total_inches = (feet * 12) + inches  # Converts feet to inches and adds inches to get total inches
        return total_inches
    else:
        return None


def convert_time_to_seconds(time_to_conv):
    """
        -   Converts given time to seconds (ex. 2:30 = 150)
        -   RETURNS: time in seconds 
    """
    if not time_to_conv or pd.isna(time_to_conv) or time_to_conv == '--':
        return 0
    try:
        minutes, seconds = map(int, str(time_to_conv).split(':'))
        return minutes * 60 + seconds
    except (ValueError, AttributeError):
        return 0


def format_date(date_to_format):
    """
        -   Formats date to yyyy-mm-dd
        -   RETURNS: formatted date
    """
    if date_to_format != '--':
        return pd.to_datetime(date_to_format)
    else:
        return None


def split_x_of_y(ratio_col):
    """
        -   Splits column of ratio into two individual numeric columns for (completed and attempted)
        -   RETURNS: tuple of (completed, attempted) Series.
    """
    split_values = ratio_col.apply(lambda x: x.split(' ') if pd.notnull(x) else [None, 'of', None])  # Splits ratio into [x, of, x]
    completed = split_values.apply(lambda x: int(x[0]) if x[0] is not None else None)
    attempted = split_values.apply(lambda x: int(x[2]) if x[2] is not None else None)
    return completed, attempted


def get_winner(row):
    """
        -   Parses bout and outcome
        -   RETURNS: name of winner for fight (ex. Conor McGregor vs. Khabib Nurmagomedov L/W returns Khabib Nurmagomedov)
    """
    names = row['BOUT'].split(' vs. ')
    outcome = row['OUTCOME'].replace('/', '')

    if len(names) != 2 or 'W' not in outcome:
        return None  # Can't determine winner

    winner_index = outcome.find('W')

    if winner_index not in (0, 1):
        return None  # Invalid structure

    winner = names[winner_index]
    return winner


def get_fight_outcome(row, df):
    """
        -  Determines the outcome of the fight for the fighter
        -  RETURNS: Char indicating outcome of fight for fighter
    """
    event = row['event']
    bout = row['bout']
    fighter = row['fighter']

    fight_row = df.loc[(df['event'] == event) & (df['bout'] == bout)]  # Parses through ufc_fight_results df; finds bouts row

    if not fight_row.empty:
        names = fight_row.iloc[0]['bout'].split(' vs. ')
        outcomes = fight_row.iloc[0]['outcome'].replace('/', '')

        if len(names) != 2 or not any(x in outcomes for x in ['W', 'L', 'D']):
            return None

        # Determines the fighter's outcome by determining index in title; uses index to determine their outcome
        fighter_index = names.index(fighter)
        outcome = outcomes[fighter_index]
        return outcome


def count_total_outcomes(value, type):
    """
        -   Counts the total number of passed in outcome
        -   RETURNS: Integer representing total of passed in outcome
    """
    if value is not None:
        return str(value).count(type)
    
def normalize_text(text):
    """
        -   Normalize any text with extra spaces in it
        -   RETURNS: String with only one space between text
    """
    if isinstance(text, str):
        return " ".join(text.strip().split())
    return text

#--------------- FILE PARSERS ---------------#

def parse_fighters():
    """
        -   Parses all fighter data and stores into 'fighters_metadata_clean.csv'
    """
    try:
        df1 = pd.read_csv(f'{DATARAWPATH}/ufc_fighter_details.csv')
        df2 = pd.read_csv(f'{DATARAWPATH}/ufc_fighter_tott.csv')
    except FileNotFoundError as e:
        print(f"ERROR: Missing file - {e}")
        return

    main_df = pd.DataFrame()

    # Adds names to main_df
    main_df['first_name'] = df1['FIRST']
    main_df['last_name'] = df1['LAST']
    main_df["full_name"] = (main_df["first_name"].fillna("") + " " + main_df["last_name"].fillna("")).str.strip() # Constructs a full name field; replaces NaN with an empty string
    main_df['nick_name'] = df1['NICKNAME'].apply(lambda x: x.replace(',', '') if isinstance(x, str) else x) # Removes commas from nicknames

    # Adds height, weight, reach, stance, dob to main_df
    main_df['height'] = df2['HEIGHT'].apply(convert_to_inches)
    main_df['weight'] = df2['WEIGHT'].apply(lambda x: int(x.split(" ")[0]) if x != '--' else None)
    main_df['reach'] = df2['REACH'].apply(lambda x: int(x.replace('"', '')) if x != '--' else None)
    main_df['stance'] = df2['STANCE']
    main_df['dob'] = df2['DOB'].apply(format_date)  # Converts date string to datetime so Django can handle db population later

    if main_df is not None and not main_df.empty:
        try:
            main_df.to_csv(f"{DATACLEANPATH}/fighters_metadata_clean.csv", index=False)  # Writes main_df to file
            print(f"Successfully saved cleaned fighter metadata to {DATACLEANPATH}")
        except Exception as e:
            print(f"ERROR: Failed to save file due to unexpected error: {e}")


def parse_events():
    """
        -   Parses all event data and stores into 'event_data_clean.csv'
    """
    try:
        df = pd.read_csv(f'{DATARAWPATH}/ufc_event_details.csv')
    except FileNotFoundError:
        print("ERROR: Could not find file 'ufc_event_details.csv'.")
        return

    main_df = pd.DataFrame()

    # Adds event info to main_df
    main_df['event'] = df['EVENT']
    main_df['date'] = df['DATE'].apply(format_date)  # Converts date string to datetime so Django can handle db population later
    main_df['location'] = df['LOCATION']

    if main_df is not None and not main_df.empty:
        try:
            main_df.to_csv(f"{DATACLEANPATH}/event_data_clean.csv", index=False)
            print(f"Successfully saved event data to {DATACLEANPATH}")
        except Exception as e:
            print(f"ERROR: Failed to save file due to unexpected error: {e}")


def parse_fight_round_stats():
    """
        -   Parses all fights per round data and stores into 'round_stats_clean.csv'
    """
    main_df = pd.DataFrame()
    column_names = ['SIG.STR.', 'TOTAL STR.', 'TD', 'HEAD', 'BODY', 'LEG', 'DISTANCE', 'CLINCH', 'GROUND']
    split_columns = {}

    try:
        df = pd.read_csv(f'{DATARAWPATH}/ufc_fight_stats.csv')
    except FileNotFoundError:
        print("ERROR: Could not find file 'ufc_fight_stats.csv'.")
        return

    # Splits every column listed in column names; stores results in split_columns dict
    for col in column_names:
        landed, attempted = split_x_of_y(df[col])
        split_columns[col] = landed, attempted

    # Adds round stats to main_df
    main_df['event'] = df['EVENT']
    main_df['bout'] = df['BOUT'].apply(normalize_text)
    main_df['round_number'] = df['ROUND'].apply(lambda x: int(str(x).replace('Round ', '')) if pd.notnull(x) and 'Round' in str(x) else None)
    main_df['fighter'] = df['FIGHTER']
    main_df['kd'] = df['KD']
    main_df['sig_str_landed'] = split_columns['SIG.STR.'][0]
    main_df['sig_str_attempted'] = split_columns['SIG.STR.'][1]
    main_df['total_str_landed'] = split_columns['TOTAL STR.'][0]
    main_df['total_str_attempted'] = split_columns['TOTAL STR.'][1]
    main_df['td_landed'] = split_columns['TD'][0]
    main_df['td_attempted'] = split_columns['TD'][1]
    main_df['sub_att'] = df['SUB.ATT']
    main_df['ctrl_time'] = df['CTRL'].apply(convert_time_to_seconds)
    main_df['reversals'] = df['REV.']
    main_df['head_str_landed'] = split_columns['HEAD'][0]
    main_df['head_str_attempted'] = split_columns['HEAD'][1]
    main_df['body_str_landed'] = split_columns['BODY'][0]
    main_df['body_str_attempted'] = split_columns['BODY'][1]
    main_df['leg_str_landed'] = split_columns['LEG'][0]
    main_df['leg_str_attempted'] = split_columns['LEG'][1]
    main_df['distance_str_landed'] = split_columns['DISTANCE'][0]
    main_df['distance_str_attempted'] = split_columns['DISTANCE'][1]
    main_df['clinch_str_landed'] = split_columns['CLINCH'][0]
    main_df['clinch_str_attempted'] = split_columns['CLINCH'][1]
    main_df['ground_str_landed'] = split_columns['GROUND'][0]
    main_df['ground_str_attempted'] = split_columns['GROUND'][1]

    if main_df is not None and not main_df.empty:
        try:
            main_df.to_csv(f"{DATACLEANPATH}/round_stats_clean.csv", index=False)
            print(f"Successfully saved round data to {DATACLEANPATH}")
        except Exception as e:
            print(f"ERROR: Failed to save file due to unexpected error: {e}")


def parse_fight_data():
    """
        -   Parses fight results and stores into 'fight_results_clean.csv'
    """
    try:
        df = pd.read_csv(f'{DATARAWPATH}/ufc_fight_results.csv')
    except FileNotFoundError:
        print("ERROR: Could not find file 'ufc_fight_results.csv'.")
        return

    main_df = pd.DataFrame()

    # Adds fight data to main_df
    main_df['event'] = df['EVENT']
    main_df['bout'] = df['BOUT'].apply(normalize_text)
    main_df['weight_class'] = df['WEIGHTCLASS']
    main_df['method'] = df['METHOD']
    main_df['round'] = df['ROUND']
    main_df['round_format'] = df['TIME FORMAT']
    main_df['time'] = df['TIME'].apply(convert_time_to_seconds)
    main_df['winner'] = df.apply(get_winner, axis=1)

    if main_df is not None and not main_df.empty:
        try:
            main_df.to_csv(f"{DATACLEANPATH}/fight_results_clean.csv", index=False)
            print(f"Successfully saved fight results data to {DATACLEANPATH}")
        except Exception as e:
            print(f"ERROR: Failed to save file due to unexpected error: {e}")


def parse_total_fight_stats():
    """
        -   Parses fight results and stores into 'total_fight_stats_clean.csv'
    """
    try:
        df = pd.read_csv(f'{DATACLEANPATH}/round_stats_clean.csv')
        fight_results_df = pd.read_csv(f'{DATARAWPATH}/ufc_fight_results.csv')
        fight_results_df.columns = fight_results_df.columns.str.lower()  # Normalize headers
    except FileNotFoundError as e:
        print(f"ERROR: Missing file - {e}")
        return

    # Removes extra spaces from EVENT and BOUT columns
    fight_results_df['event'] = fight_results_df['event'].apply(normalize_text)
    fight_results_df['bout'] = fight_results_df['bout'].apply(normalize_text)

    # Builds the main_df
    df = df.drop(['round_number'], axis=1)
    main_df = df.groupby(['event', 'bout', 'fighter']).sum().reset_index()  # Sums round data to get total fight data
    main_df['result'] = main_df.apply(get_fight_outcome, axis=1, args=(fight_results_df,))

    if main_df is not None and not main_df.empty:
        try:
            main_df.to_csv(f"{DATACLEANPATH}/total_fight_stats_clean.csv", index=False)
            print(f"Successfully saved total fight stats data to {DATACLEANPATH}")
        except Exception as e:
            print(f"ERROR: Failed to save file due to unexpected error: {e}")


def parse_career_stats():
    """
        -   Parses fight results and stores into 'career_stats_clean.csv'
    """
    try:
        total_fight_stats_df = pd.read_csv(f'{DATACLEANPATH}/total_fight_stats_clean.csv')
        fight_results_clean_df = pd.read_csv(f'{DATACLEANPATH}/fight_results_clean.csv')
    except FileNotFoundError as e:
        print(f"ERROR: Missing file - {e}")
        return

    total_fight_stats_df = total_fight_stats_df.drop(['event', 'bout'], axis=1)

    # Creates smaller df containing each fighter and their methods of victory summed
    summed_methods_df = pd.crosstab(fight_results_clean_df['winner'], fight_results_clean_df['method'])
    summed_methods_df = summed_methods_df.rename_axis('fighter').reset_index() # Renames row axis to fighter from winner and resets index to a column
    summed_methods_df['fighter'] = summed_methods_df['fighter'].apply(normalize_text)

    # Builds the main_df
    main_df = total_fight_stats_df.groupby('fighter').sum().reset_index()  # Sums all columns for a fighter
    # Counts total number of wins, losses, and draws
    main_df['wins'] = main_df['result'].apply(count_total_outcomes, args=('W',))
    main_df['losses'] = main_df['result'].apply(count_total_outcomes, args=('L',))
    main_df['draws'] = main_df['result'].apply(count_total_outcomes, args=('D',))
    main_df['total_fights'] = main_df.apply(lambda x: x['wins'] + x['losses'] + x['draws'], axis=1)
    main_df = main_df.drop(['result'], axis=1)

    # Merges main_df and summed_methods to add method of victories to each fighter
    main_df = main_df.merge(summed_methods_df, on='fighter', how='left')
    main_df = main_df.fillna(0)
    main_df.rename(columns={
        "Decision - Majority ": "majority_decisions",
        "Decision - Split ": "split_decisions",
        "Decision - Unanimous ": "unanimous_decisions",
        "Submission ": "submissions",
        "KO/TKO ": "ko_tko",
        "TKO - Doctor's Stoppage ": "tko_doctor_stoppages",
        "DQ ": "dq"
    }, inplace=True) 

    if main_df is not None and not main_df.empty:
        try:
            main_df.to_csv(f"{DATACLEANPATH}/career_stats_clean.csv", index=False)
            print(f"Successfully saved career stats data to {DATACLEANPATH}")
        except Exception as e:
            print(f"ERROR: Failed to save file due to unexpected error: {e}")

def parse_all_data():
    """
        -   Calls all parsing functions to modify original CSVs into fully usable
                and clean files for DB population
    """
    parse_fighters()
    parse_events()
    parse_fight_round_stats()
    parse_fight_data()
    parse_total_fight_stats()
    parse_career_stats()


parse_all_data()
