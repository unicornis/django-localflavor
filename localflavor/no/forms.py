"""
Norwegian-specific Form helpers
"""

from __future__ import absolute_import, unicode_literals

import re
import datetime

from django.core.validators import EMPTY_VALUES
from django.forms import ValidationError
from django.forms.fields import Field, RegexField, Select
from django.utils.translation import ugettext_lazy as _

from .no_municipalities import MUNICIPALITY_CHOICES


class NOZipCodeField(RegexField):
    """
    A form field that validates input as a Norwegian zip code. Valid codes
    have four digits.
    """
    default_error_messages = {
        'invalid': _('Enter a zip code in the format XXXX.'),
    }

    def __init__(self, max_length=None, min_length=None, *args, **kwargs):
        super(NOZipCodeField, self).__init__(r'^\d{4}$',
                                             max_length, min_length, *args, **kwargs)


class NOMunicipalitySelect(Select):
    """
    A Select widget that uses a list of Norwegian municipalities (fylker)
    as its choices.
    """
    def __init__(self, attrs=None):
        super(NOMunicipalitySelect, self).__init__(attrs, choices=MUNICIPALITY_CHOICES)


class NOSocialSecurityNumber(Field):
    """
    Algorithm is documented at http://no.wikipedia.org/wiki/Personnummer
    """
    default_error_messages = {
        'invalid': _('Enter a valid Norwegian social security number.'),
    }

    def clean(self, value):
        super(NOSocialSecurityNumber, self).clean(value)
        if value in EMPTY_VALUES:
            return ''

        if not re.match(r'^\d{11}$', value):
            raise ValidationError(self.error_messages['invalid'])

        day = int(value[:2])
        month = int(value[2:4])
        year2 = int(value[4:6])

        inum = int(value[6:9])
        self.birthday = None
        try:
            if 000 <= inum < 500:
                self.birthday = datetime.date(1900 + year2, month, day)
            if 500 <= inum < 750 and year2 > 54:
                self.birthday = datetime.date(1800 + year2, month, day)
            if 500 <= inum < 1000 and year2 < 40:
                self.birthday = datetime.date(2000 + year2, month, day)
            if 900 <= inum < 1000 and year2 > 39:
                self.birthday = datetime.date(1900 + year2, month, day)
        except ValueError:
            raise ValidationError(self.error_messages['invalid'])

        sexnum = int(value[8])
        if sexnum % 2 == 0:
            self.gender = 'F'
        else:
            self.gender = 'M'

        digits = map(int, list(value))
        weight_1 = [3, 7, 6, 1, 8, 9, 4, 5, 2, 1, 0]
        weight_2 = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2, 1]

        def multiply_reduce(aval, bval):
            return sum([(a * b) for (a, b) in zip(aval, bval)])

        if multiply_reduce(digits, weight_1) % 11 != 0:
            raise ValidationError(self.error_messages['invalid'])
        if multiply_reduce(digits, weight_2) % 11 != 0:
            raise ValidationError(self.error_messages['invalid'])

        return value


class NOPhoneNumberField(RegexField):
    """
    Field with phonenumber validation. Requires a phone number with
    8 digits and optional country code
    """
    default_error_messages = {
        'invalid': _('A phone number must be 8 digits and may have country code'),
    }

    def __init__(self, max_length=None, min_length=None, *args, **kwargs):
        super(NOPhoneNumberField, self).__init__(r'^(?:\+47)? ?(\d{3}\s?\d{2}\s?\d{3}|\d{2}\s?\d{2}\s?\d{2}\s?\d{2})$',
                                                 max_length, min_length, *args, **kwargs)


def multiply_reduce(aval, bval):
    return sum([(a * b) for (a, b) in zip(aval, bval)])


class NOBankAccountField(RegexField):
    """
    Validates that the given input is a valid Norwegian bank account number.
    Valid numbers have 11 digits, and uses a checksum algorithm documented at
    http://no.wikipedia.org/wiki/Kontonummer (TODO: replace link with better
    documentation)
    """
    default_error_messages = {'invalid': _("Please enter a valid Norwegian bank account number")}

    def __init__(self, *args, **kwargs):
        kwargs['regex'] = re.compile(r'^(\d{4})[\. ]?(\d{2})[\. ]?(\d{5})$')
        kwargs['max_length'] = 13
        super(NOBankAccountField, self).__init__(*args, **kwargs)

    def to_python(self, value):
        "Normalizes the value by removing periods and spaces."
        return value.replace('.', '').replace(' ', '')

    def clean(self, value):
        "Validate checksum in value"
        value = super(NOBankAccountField, self).clean(value)
        digits, checksum = map(int, list(value)[:10])[::-1], int(value[-1])
        weights = [2, 3, 4, 5, 6, 7, 2, 3, 4, 5]  # see http://no.wikipedia.org/wiki/MOD11
        calculated_checksum = (11 - multiply_reduce(digits, weights) % 11)
        if calculated_checksum == 11:
            calculated_checksum = 0
        if calculated_checksum != checksum:
            raise ValidationError(self.default_error_messages['invalid'], code='invalid')
        return value


class NOOrganisationNumberField(RegexField):
    """
    Validates the input as a Norwegian "organisasjonsnummer", which is a 9
    digit number with a checksum using modulus 11. The format is documented at
    http://www.brreg.no/samordning/organisasjonsnummer.html (in Norwegian).
    """

    default_error_messages = {'invalid': _("Please enter a valid Norwegian organisation number")}

    def __init__(self, *args, **kwargs):
        kwargs['regex'] = re.compile(r'^(NO )?(\d{3}) ?(\d{3}) ?(\d{3})( MVA)?$', re.IGNORECASE)
        kwargs['max_length'] = 18
        super(NOOrganisationNumberField, self).__init__(*args, **kwargs)

    def to_python(self, value):
        match = self.regex.match(value)
        if match:
            groups = match.groups ()
            prefix, suffix = groups[0] if groups[0] else '', groups[-1] if groups[-1] else ''
            return prefix + ''.join(match.groups()[1:4]) + suffix
        return value

    def clean(self, value):
        value = super(NOOrganisationNumberField, self).clean(value)
        number = ''.join(self.regex.match(value).groups()[1:4])
        digits, checksum = map(int, list(number)[:8]), int(number[-1])
        weights = [3, 2, 7, 6, 5, 4, 3, 2]
        calculated_checksum = (11 - multiply_reduce(digits, weights) % 11)
        if calculated_checksum == 10 or calculated_checksum != checksum:
            raise ValidationError(self.default_error_messages['invalid'], code='invalid')
        return value
