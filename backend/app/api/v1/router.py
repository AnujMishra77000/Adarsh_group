from fastapi import APIRouter

from app.api.v1.endpoints import analytics, auth, bills, campaigns, chat, customers, health, prescriptions, staff, vendors

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(customers.router)
api_router.include_router(vendors.router)
api_router.include_router(prescriptions.router)
api_router.include_router(bills.router)
api_router.include_router(campaigns.router)
api_router.include_router(analytics.router)
api_router.include_router(staff.router)
api_router.include_router(chat.router)
