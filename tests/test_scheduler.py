from renew_curve.scheduler import forgetting_curve_days


def test_forgetting_curve_days_for_five_reviews():
    assert forgetting_curve_days(5) == [1, 3, 7, 14, 30]
