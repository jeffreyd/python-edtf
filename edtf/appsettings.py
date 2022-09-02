from dateutil.relativedelta import relativedelta

try:
    from django.core.exceptions import ImproperlyConfigured
    try:
        from django.conf import settings
        EDTF = getattr(settings, 'EDTF', {})
    except ImproperlyConfigured:
        EDTF = {}
except ImportError:
    EDTF = {}

SEASON_MONTHS_RANGE = EDTF.get('SEASON_MONTHS_RANGE', {
        # season id: [earliest_month, last_month]
        21: [3, 5],
        22: [6, 8],
        23: [9, 11],
        # winter in the northern hemisphere wraps the end of the year, so
        # Winter 2010 could wrap into 2011.
        # For simplicity, we assume it falls at the end of the year, esp since the
        # spec says that sort order goes spring > summer > autumn > winter
        24: [12, 12],
        25: [3, 5],
        26: [6, 8],
        27: [9, 11],
        28: [12, 12],
        29: [9, 11],
        # same here for summer in the southern hemisphere
        30: [12, 12],
        31: [3, 5],
        32: [6, 8],
        33: [1, 3],
        34: [4, 6],
        35: [7, 9],
        36: [10, 12],
        37: [1, 4],
        38: [5, 8],
        39: [9, 12],
        40: [1, 6],
        41: [7, 12]
    }
)

DAY_FIRST = EDTF.get('DAY_FIRST', False)  # Americans!

SEASONS = EDTF.get('SEASONS', {
    21: "spring",
    22: "summer",
    23: "autumn",
    24: "winter",
    25: "spring - northern hemisphere",
    26: "summer - northern hemisphere",
    27: "autumn - northern hemisphere",
    28: "winter - northern hemisphere",
    29: "spring - southern hemisphere",
    30: "summer - southern hemisphere",
    31: "autumn - southern hemisphere",
    32: "winter - southern hemisphere",
    33: "quarter 1",
    34: "quarter 2",
    35: "quarter 3",
    36: "quarter 4",
    37: "quadrimester 1",
    38: "quadrimester 2",
    39: "quadrimester 3",
    40: "semestral 1",
    41: "semestral 2",
})
INVERSE_SEASONS = EDTF.get('INVERSE_SEASONS', {v: k for k, v in SEASONS.items()})
# also need to interpret `fall`
INVERSE_SEASONS['fall'] = 23
INVERSE_SEASONS['fall - southern hemisphere'] = 31

# changing these will break tests
PADDING_DAY_PRECISION = EDTF.get('PADDING_DAY_PRECISION', relativedelta(days=1))
PADDING_MONTH_PRECISION = EDTF.get('PADDING_MONTH_PRECISION', relativedelta(months=1))
PADDING_YEAR_PRECISION = EDTF.get('PADDING_YEAR_PRECISION', relativedelta(years=1))
PADDING_SEASON_PRECISION = EDTF.get('PADDING_SEASON_PRECISION', relativedelta(weeks=12))
MULTIPLIER_IF_UNCERTAIN = EDTF.get('MULTIPLIER_IF_UNCERTAIN', 1.0)
MULTIPLIER_IF_APPROXIMATE = EDTF.get('MULTIPLIER_IF_APPROXIMATE', 1.0)
MULTIPLIER_IF_BOTH = EDTF.get('MULTIPLIER_IF_BOTH', 2.0)

DELTA_IF_UNKNOWN = EDTF.get("DELTA_IF_UNKNOWN", relativedelta(years=10))
