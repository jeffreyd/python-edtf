import calendar
import re
from datetime import date
from dateutil.parser import parse
from dateutil.relativedelta import relativedelta
from edtf import appsettings


EARLIEST = 'earliest'
LATEST = 'latest'


class EDTFObject(object):
    """
    Object to attact to a parser to become instantiated when the parser
    completes.
    """
    parser = None

    @classmethod
    def set_parser(cls, p):
        cls.parser = p
        p.addParseAction(cls.parse_action)

    @classmethod
    def parse_action(cls, toks):
        kwargs = toks.asDict()
        try:
            return cls(**kwargs) # replace the token list with the class
        except Exception as e:
            print "trying to %s.__init__(**%s)" % (cls.__name__, kwargs)
            raise(e)

    @classmethod
    def parse(cls, s):
        return cls.parser.parseString(s)[0]

    def __repr__(self):
        return "%s: '%s'" % (type(self).__name__, unicode(self))

    def __init__(self, *args, **kwargs):
        str = "%s.__init__(*%s, **%s)" % (
            type(self).__name__,
            args, kwargs,
        )
        raise NotImplementedError("%s is not implemented." % str)

    def __unicode__(self):
        raise NotImplementedError

    def _strict_date(self, lean):
        raise NotImplementedError

    def lower_start_strict(self):
        return self._strict_date(lean=EARLIEST)

    def upper_end_strict(self):
        return self._strict_date(lean=LATEST)

    def _get_padding(self, multiplier):
        """
        Subclasses should override this to pad based on how precise they are.
        """
        return relativedelta(0)

    def get_is_approximate(self):
        return getattr(self, '_is_approximate', False)
    def set_is_approximate(self, val):
        self._is_approximate = val
    is_approximate = property(get_is_approximate, set_is_approximate)

    def get_is_uncertain(self):
        return getattr(self, '_is_uncertain', False)
    def set_is_uncertain(self, val):
        self._is_uncertain = val
    is_uncertain = property(get_is_uncertain, set_is_uncertain)

    def _adjust_for_precision(self, dt, lean):
        if self.is_approximate or self.is_uncertain:
            multiplier = appsettings.PADDING_MULTIPLIER
            if self.is_approximate and self.is_uncertain:
                multiplier *= 2.0
            if lean == EARLIEST:
                return dt - self._get_padding(multiplier)
            else:
                return dt + self._get_padding(multiplier)
        else:
            return dt

    def lower_start_fuzzy(self):
        dt = self.lower_start_strict()
        return self._adjust_for_precision(dt, lean=EARLIEST)

    def upper_end_fuzzy(self):
        dt = self.upper_end_strict()
        return self._adjust_for_precision(dt, lean=LATEST)


# (* ************************** Level 0 *************************** *)


class Date(EDTFObject):

    def set_year(self, y):
        if y is None:
            raise AttributeError("Year must not be None")
        self._year = y
    def get_year(self):
        return self._year
    year = property(get_year, set_year)

    def set_month(self, m):
        self._month = m
        if m == None:
            self.day = None
    def get_month(self):
        return self._month
    month = property(get_month, set_month)

    def __init__(self, year=None, month=None, day=None, **kwargs):
        for param in ('date', 'lower', 'upper'):
            if param in kwargs:
                self.__init__(**kwargs[param])
                return

        self.year = year # Year is required, but sometimes passed in as a 'date' dict.
        self.month = month
        self.day = day

    def __unicode__(self):
        r = self.year
        if self.month:
            r += u"-%s" % self.month
            if self.day:
                r += u"-%s" % self.day
        return r

    def as_iso(self, default=date.max):
        return u"%s-%02d-%02d" % (
            self.year,
            int(self.month or default.month),
            int(self.day or default.day),
        )

    def _precise_year(self, lean):
        "Replace any ambiguous characters in the year string with 0s or 9s"
        if lean == EARLIEST:
            return int(re.sub(r'[xu]', r'0', self.year))
        else:
            return int(re.sub(r'[xu]', r'9', self.year))

    def _precise_month(self, lean):
        if self.month and self.month != "uu":
            return int(self.month)
        else:
            return 1 if lean == EARLIEST else 12

    @staticmethod
    def _days_in_month(yr, month):
        return calendar.monthrange(int(yr), int(month))[1]

    def _precise_day(self, lean):
        if not self.day or self.day == 'uu':
            if lean == EARLIEST:
                return 1
            else:
                return self._days_in_month(
                    self._precise_year(LATEST), self._precise_month(LATEST)
                )
        else:
            return int(self.day)

    def _strict_date(self, lean):
        parts = {
            'year': self._precise_year(lean),
            'month': self._precise_month(lean),
            'day': self._precise_day(lean),
        }

        isoish = u"%(year)s-%(month)02d-%(day)02d" % parts

        try:
            dt = parse(
                isoish,
                fuzzy=True,
                yearfirst=True,
                dayfirst=False,
                default=date.max if lean == LATEST else date.min
            )
            return dt

        except ValueError:  # year is out of range
            if isoish < date.min.isoformat():
                return date.min
            else:
                return date.max


class DateAndTime(EDTFObject):
    def __init__(self, date, time):
        self.date = date
        self.time = time

    def __unicode__(self):
        return self.as_iso()

    def as_iso(self):
        return self.date.as_iso()+"T"+self.time

    def _strict_date(self, lean):
        return self.date._strict_date(lean)


class Interval(EDTFObject):
    def __init__(self, lower, upper):
        self.lower = lower
        self.upper = upper

    def __unicode__(self):
        return u"%s/%s" % (self.lower, self.upper)

    def _strict_date(self, lean):
        if lean == EARLIEST:
            try:
                r = self.lower._strict_date(lean)
                if r is None:
                    raise AttributeError
                return r
            except AttributeError: # it's a string, or no date. Result depends on the upper date
                upper = self.upper._strict_date(LATEST)
                return upper - appsettings.DELTA_IF_UNKNOWN
        else:
            try:
                r = self.upper._strict_date(lean)
                if r is None:
                    raise AttributeError
                return r
            except AttributeError: # an 'unknown' or 'open' string - depends on the lower date
                if self.upper and (self.upper == "open" or self.upper.date == "open"):
                    return date.today() # it's still happening
                else:
                    lower = self.lower._strict_date(EARLIEST)
                    return lower + appsettings.DELTA_IF_UNKNOWN


# (* ************************** Level 1 *************************** *)


class UA(EDTFObject):
    @classmethod
    def parse_action(cls, toks):
        args = toks.asList()
        return cls(*args)

    def __init__(self, *args):
        assert len(args)==1
        ua = args[0]

        self.is_uncertain = "?" in ua
        self.is_approximate = "~" in ua

    def __unicode__(self):
        d = ""
        if self.is_uncertain:
            d += "?"
        if self.is_approximate:
            d += "~"
        return d


class UncertainOrApproximate(EDTFObject):
    def __init__(self, date, ua):
        self.date = date
        self.ua = ua

    def __unicode__(self):
        if self.ua:
            return u"%s%s" % (self.date, self.ua)
        else:
            return unicode(self.date)

    def _strict_date(self, lean):
        if self.date in ("open", "unknown"):
            return None
        return self.date._strict_date(lean)


class Unspecified(Date):
    pass


class Level1Interval(Interval):
    def __init__(self, lower, upper):
        self.lower = UncertainOrApproximate(**lower)
        self.upper = UncertainOrApproximate(**upper)


class LongYear(EDTFObject):
    def __init__(self, year):
        self.year = year

    def __unicode__(self):
        return "y%s" % self.year

    def _precise_year(self):
        return int(self.year)

    def _strict_date(self, lean):
        py = self._precise_year()
        if py >= date.max.year:
            return date.max
        if py <= date.min.year:
            return date.min

        if lean == EARLIEST:
            return date(py, 1, 1)
        else:
            return date(py, 12, 31)


class Season(Date):
    def __init__(self, year, season, **kwargs):
        self.year = year
        self.season = season # use season to look up month
        # day isn't part of the 'season' spec, but it helps the inherited
        # `Date` methods do their thing.
        self.day = None

    def __unicode__(self):
        return "%s-%s" % (self.year, self.season)

    def _precise_month(self, lean):
        rng = appsettings.SEASON_MONTHS_RANGE[int(self.season)]
        if lean == EARLIEST:
            return rng[0]
        else:
            return rng[1]


# (* ************************** Level 2 *************************** *)


class PartialUncertainOrApproximate(Date):

    def set_year(self, y): # Year can be None.
        self._year = y
    year = property(Date.get_year, set_year)

    def __init__(
        self, year=None, month=None, day=None,
        year_ua = False, month_ua = False, day_ua = False,
        year_month_ua = False, month_day_ua = False,
        ssn=None, season_ua=False, all_ua=False
    ):
        self.year = year
        self.month = month
        self.day = day

        self.year_ua = year_ua
        self.month_ua = month_ua
        self.day_ua = day_ua

        self.year_month_ua = year_month_ua
        self.month_day_ua = month_day_ua

        self.season = ssn
        self.season_ua = season_ua

        self.all_ua = all_ua

    def __unicode__(self):

        if self.season_ua:
            return "%s%s" % (self.season, self.season_ua)

        if self.year_ua:
            y = "%s%s" % (self.year, self.year_ua)
        else:
            y = unicode(self.year)

        if self.month_ua:
            m = "(%s)%s" % (self.month, self.month_ua)
        else:
            m = unicode(self.month)

        if self.day:
            if self.day_ua:
                d = "(%s)%s" % (self.day, self.day_ua)
            else:
                d = unicode(self.day)
        else:
            d = None

        if self.year_month_ua: # year/month approximate. No brackets needed.
            ym = "%s-%s%s" % (y, m, self.year_month_ua)
            if d:
                result = "%s-%s" % (ym, d)
            else:
                result = ym
        elif self.month_day_ua:
            if self.year_ua: # we don't need the brackets round month and day
                result = "%s-%s-%s%s" % (y, m, d, self.month_day_ua)
            else:
                result = "%s-(%s-%s)%s" % (y, m, d, self.month_day_ua)
        else:
            if d:
                result = "%s-%s-%s" % (y, m, d)
            else:
                result = "%s-%s" % (y, m)

        if self.all_ua:
            result = "(%s)%s" % (result, self.all_ua)

        return result

    def _precise_year(self, lean):
        if self.season:
            return self.season._precise_year(lean)
        return super(PartialUncertainOrApproximate, self)._precise_year(lean)

    def _precise_month(self, lean):
        if self.season:
            return self.season._precise_month(lean)
        return super(PartialUncertainOrApproximate, self)._precise_month(lean)

    def _precise_day(self, lean):
        if self.season:
            return self.season._precise_day(lean)
        return super(PartialUncertainOrApproximate, self)._precise_day(lean)


class PartialUnspecified(Unspecified):
    pass


class Consecutives(Interval):
    # Treating Consecutive ranges as intervals where one bound is optional
    def __init__(self, lower=None, upper=None):
        if lower and not isinstance(lower, EDTFObject):
            self.lower = Date.parse(lower)
        else:
            self.lower = lower

        if upper and not isinstance(upper, EDTFObject):
            self.upper = Date.parse(upper)
        else:
            self.upper = upper


    def __unicode__(self):
        return u"%s..%s" % (self.lower or '', self.upper or '')


class EarlierConsecutives(Consecutives):
    pass


class LaterConsecutives(Consecutives):
    pass


class OneOfASet(EDTFObject):
    @classmethod
    def parse_action(cls, toks):
        args = [t for t in toks.asList() if isinstance(t, EDTFObject)]
        return cls(*args)

    def __init__(self, *args):
        self.objects = args

    def __unicode__(self):
        return u"[%s]" % (", ".join([unicode(o) for o in self.objects]))

    def _strict_date(self, lean):
        if lean == LATEST:
            return max([x._strict_date(lean) for x in self.objects])
        else:
            return min([x._strict_date(lean) for x in self.objects])


class MultipleDates(EDTFObject):
    @classmethod
    def parse_action(cls, toks):
        args = [t for t in toks.asList() if isinstance(t, EDTFObject)]
        return cls(*args)

    def __init__(self, *args):
        self.objects = args

    def __unicode__(self):
        return u"{%s}" % (", ".join([unicode(o) for o in self.objects]))

    def _strict_date(self, lean):
        if lean == LATEST:
            return max([x._strict_date(lean) for x in self.objects])
        else:
            return min([x._strict_date(lean) for x in self.objects])


class MaskedPrecision(Date):
    pass


class Level2Interval(Level1Interval):
    def __init__(self, lower, upper):
        self.lower = lower
        self.upper = upper


class ExponentialYear(LongYear):
    def __init__(self, base, exponent, precision=None):
        self.base = base
        self.exponent = exponent
        self.precision = precision

    def _precise_year(self):
        return pow(int(self.base), int(self.exponent))

    def get_year(self):
        if self.precision:
            return '%se%sp%s' % (self.base, self.exponent, self.precision)
        else:
            return '%se%s' % (self.base, self.exponent)
    year = property(get_year)