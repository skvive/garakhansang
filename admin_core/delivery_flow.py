"""Role-scoped delivery workflow domain. No PG/FCM/Maps side effects here.
The persistence and push adapter must verify identity before calling transition().
"""
from dataclasses import dataclass,replace

@dataclass(frozen=True)
class DeliveryOrder:
    order_id: str
    merchant_id: str
    state: str="payment_pending"
    rider_id: str|None=None
    version: int=0

@dataclass(frozen=True)
class Outcome:
    order: DeliveryOrder
    notifications: tuple[str,...]

class OrderFlowError(ValueError):
    pass

# Format: (current, event): (next, role, notification)
RULES={
    ("payment_pending","payment_verified"):("paid","payment_service","merchant:new_paid_order"),
    ("paid","merchant_accept"):("merchant_accepted","merchant","customer:merchant_accepted"),
    ("merchant_accepted","merchant_prepare"):("preparing","merchant","customer:preparing"),
    ("preparing","merchant_ready"):("ready_for_pickup","merchant","customer:ready_for_pickup"),
    ("ready_for_pickup","merchant_request_dispatch"):("dispatch_requested","merchant","rider_pool:job_available"),
    ("dispatch_requested","rider_accept"):("rider_assigned","rider","merchant:rider_assigned"),
    ("rider_assigned","rider_pickup"):("picked_up","rider","customer:picked_up"),
    ("picked_up","rider_start_delivery"):("in_transit","rider","customer:in_transit"),
    ("in_transit","rider_deliver"):("delivered","rider","customer:delivered"),
    ("paid","merchant_reject"):("refund_pending","merchant","ops:refund_required"),
    ("paid","customer_cancel"):("refund_pending","customer","ops:refund_required"),
    ("refund_pending","refund_verified"):("refunded","payment_service","customer:refund_completed"),
}

def transition(order:DeliveryOrder,event:str,role:str,actor_id:str,
               expected_version:int,verified_provider_event:bool=False)->Outcome:
    if expected_version!=order.version:
        raise OrderFlowError("stale order version")
    rule=RULES.get((order.state,event))
    if rule is None:raise OrderFlowError("state transition not allowed")
    state,required_role,notice=rule
    if role!=required_role:raise OrderFlowError("actor role not authorized")
    if not isinstance(actor_id,str) or not actor_id.strip():
        raise OrderFlowError("actor id required")
    if role=="merchant" and actor_id!=order.merchant_id:
        raise OrderFlowError("merchant does not own order")
    if role=="rider" and order.rider_id is not None and actor_id!=order.rider_id:
        raise OrderFlowError("delivery not assigned to rider")
    if role=="payment_service" and not verified_provider_event:
        raise OrderFlowError("provider-verified payment or refund event required")
    rider=order.rider_id
    if event=="rider_accept":
        if rider is not None:raise OrderFlowError("delivery already assigned")
        rider=actor_id
    return Outcome(replace(order,state=state,rider_id=rider,version=order.version+1),(notice,))
