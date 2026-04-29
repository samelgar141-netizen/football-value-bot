from pathlib import Path

LEAGUE_ID = 'PL'
SEASON = '2425'

BANKROLL = 1000
MIN_EV_THRESHOLD = 0.05
MAX_KELLY_FRACTION = 0.25

BOOKMAKERS = [
    'bet365',
    'betfair',
    'betway',
    'paddypower',
    'williamhill',
    'ladbrokes',
    'skybet',
    'unibet',
]

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / 'data'
RAW_DIR = DATA_DIR / 'raw'
ODDS_DIR = DATA_DIR / 'odds'
PROCESSED_DIR = DATA_DIR / 'processed'
LEDGER_DIR = BASE_DIR / 'ledger'
REPORTS_DIR = BASE_DIR / 'reports'
