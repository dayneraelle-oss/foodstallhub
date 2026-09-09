from app.models.order import PaymentMethod
from app.services import delivery_service, payment_service


def test_cod_payment_stays_pending():
    result = payment_service.initiate_payment(PaymentMethod.cod, 120.5)
    assert result.payment_status.value == "pending"


def test_digital_payment_is_authorized():
    result = payment_service.initiate_payment(PaymentMethod.upi, 120.5, user_id=1)
    assert result.payment_status.value == "paid"
    assert result.reference_id.startswith("UPI-")


def test_delivery_estimate_and_fee_are_deterministic():
    assert delivery_service.estimate_delivery_minutes() == delivery_service.estimate_delivery_minutes()
    assert delivery_service.calculate_delivery_fee(distance_km=2) == 0.0
    assert delivery_service.calculate_delivery_fee(distance_km=5) > 0.0
    assert delivery_service.assign_driver(1) == delivery_service.assign_driver(1)


def test_top_metro_gets_traffic_buffer():
    city_time = delivery_service.estimate_delivery_minutes(city="mumbai")
    plain_time = delivery_service.estimate_delivery_minutes(city="kochi")
    assert city_time > plain_time