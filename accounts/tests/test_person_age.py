from datetime import date, timedelta

from django.test import TestCase
from django.utils import timezone

from accounts.models import Person


def _make_person(birth_date):
    return Person(first_name="Test", last_name_paterno="Person", birth_date=birth_date)


class PersonAgeTests(TestCase):
    def test_age_for_birthday_already_passed_this_year(self):
        today = timezone.now().date()
        birth_date = today.replace(year=today.year - 20) - timedelta(days=1)
        person = _make_person(birth_date)
        self.assertEqual(person.age, 20)

    def test_age_for_birthday_today(self):
        today = timezone.now().date()
        birth_date = today.replace(year=today.year - 18)
        person = _make_person(birth_date)
        self.assertEqual(person.age, 18)
        self.assertFalse(person.is_minor)

    def test_age_for_birthday_not_yet_reached_this_year(self):
        today = timezone.now().date()
        future_this_year = today + timedelta(days=2)
        birth_date = future_this_year.replace(year=future_this_year.year - 18)
        person = _make_person(birth_date)
        self.assertEqual(person.age, 17)
        self.assertTrue(person.is_minor)

    def test_is_minor_true_for_a_child(self):
        person = _make_person(date(2015, 6, 1))
        self.assertTrue(person.is_minor)

    def test_is_minor_false_for_an_adult(self):
        person = _make_person(date(1990, 1, 1))
        self.assertFalse(person.is_minor)
