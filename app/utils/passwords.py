"""Shared password policy for account setup, creation and reset."""


def valid_password(value):
    return isinstance(value, str) and 10 <= len(value) <= 256
