from moneyed.classes import CurrencyDoesNotExist
from decimal import InvalidOperation
from rest_framework import serializers
from djmoney.models.fields import Money


class MoneySerializer(serializers.Field):
    def to_representation(self, obj):
        return {
            'amount': float(obj.amount) if obj.amount else 0,
            'currency': "%s" % obj.currency,
        }

    def to_internal_value(self, data):
        try:
            return Money(data.get('amount'), data.get('currency'))
        except InvalidOperation:
            raise serializers.ValidationError(
                {'error': 'invalid amount of money'})
        except CurrencyDoesNotExist:
            raise serializers.ValidationError({'error': 'invalid currency'})
