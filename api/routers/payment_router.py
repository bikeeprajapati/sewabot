import os
import uuid
import base64
import hashlib
import hmac
import httpx
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from api.database import get_db
from api.models import Job, Payment, Worker, User

router = APIRouter(prefix="/payments", tags=["Payments"])

# ── eSewa Sandbox Config ─────────────────────────────────
ESEWA_MERCHANT_CODE = os.getenv("ESEWA_MERCHANT_CODE", "EPAYTEST")
ESEWA_SECRET_KEY    = os.getenv("ESEWA_SECRET_KEY", "8gBm/:&EnhH.1/q")
ESEWA_PAYMENT_URL   = "https://rc-epay.esewa.com.np/api/epay/main/v2/form"
ESEWA_VERIFY_URL    = "https://rc-epay.esewa.com.np/api/epay/transaction/status/"
BASE_URL            = os.getenv("BASE_URL", "http://localhost:8001")

# ── Schemas ──────────────────────────────────────────────
class InitiatePaymentRequest(BaseModel):
    job_id:    str
    client_id: str

# ── Generate eSewa signature ─────────────────────────────
def generate_signature(message: str) -> str:
    """
    eSewa v2 requires HMAC-SHA256 signature.
    message = "total_amount,transaction_uuid,product_code"
    """
    key    = ESEWA_SECRET_KEY.encode("utf-8")
    msg    = message.encode("utf-8")
    digest = hmac.new(key, msg, hashlib.sha256).digest()
    return base64.b64encode(digest).decode("utf-8")

# ════════════════════════════════════════════════════════
# INITIATE PAYMENT
# ════════════════════════════════════════════════════════
@router.post("/initiate")
def initiate_payment(
    request: InitiatePaymentRequest,
    db:      Session = Depends(get_db)
):
    """
    Step 1 — Client clicks 'Pay Now'.
    Creates a payment record and returns eSewa redirect URL.
    """

    # Get the job
    job = db.query(Job).filter(Job.id == request.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if not job.worker_id:
        raise HTTPException(status_code=400, detail="No worker assigned to this job yet")

    # Get worker to calculate amount
    worker = db.query(Worker).filter(Worker.id == job.worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")

    # Calculate amounts
    total_amount     = worker.hourly_rate   # Rs. per hour (simplified)
    platform_fee     = int(total_amount * 0.10)   # SewaBot takes 10%
    worker_earning   = total_amount - platform_fee

    # Check no duplicate payment
    existing = db.query(Payment).filter(Payment.job_id == request.job_id).first()
    if existing and existing.status == "completed":
        raise HTTPException(status_code=400, detail="Payment already completed for this job")

    # Create transaction UUID
    transaction_uuid = str(uuid.uuid4())

    # Create payment record in DB
    payment = Payment(
        id             = str(uuid.uuid4()),
        job_id         = request.job_id,
        amount         = total_amount,
        worker_earning = worker_earning,
        platform_fee   = platform_fee,
        method         = "esewa",
        status         = "pending",
        transaction_id = transaction_uuid,
    )
    db.add(payment)
    db.commit()

    # Generate signature
    message   = f"total_amount={total_amount},transaction_uuid={transaction_uuid},product_code={ESEWA_MERCHANT_CODE}"
    signature = generate_signature(message)

    # eSewa payment form data
    esewa_data = {
        "amount":                total_amount,
        "tax_amount":            0,
        "total_amount":          total_amount,
        "transaction_uuid":      transaction_uuid,
        "product_code":          ESEWA_MERCHANT_CODE,
        "product_service_charge":0,
        "product_delivery_charge":0,
        "success_url":           f"{BASE_URL}/payments/esewa/success",
        "failure_url":           f"{BASE_URL}/payments/esewa/failure",
        "signed_field_names":    "total_amount,transaction_uuid,product_code",
        "signature":             signature,
    }

    return {
        "payment_url":       ESEWA_PAYMENT_URL,
        "payment_data":      esewa_data,
        "transaction_uuid":  transaction_uuid,
        "amount":            total_amount,
        "worker_earning":    worker_earning,
        "platform_fee":      platform_fee,
        "message":           "Redirect user to payment_url with payment_data as form POST"
    }


# ════════════════════════════════════════════════════════
# SUCCESS CALLBACK
# eSewa redirects here after successful payment
# ════════════════════════════════════════════════════════
@router.get("/esewa/success")
async def esewa_success(
    data:    str = None,
    db:      Session = Depends(get_db)
):
    """
    Step 2 — eSewa redirects here after payment.
    Verify the payment with eSewa API before updating DB.
    """
    if not data:
        return HTMLResponse(content=error_page("No payment data received"), status_code=400)

    try:
        # Decode base64 response from eSewa
        decoded      = base64.b64decode(data).decode("utf-8")
        import json
        payment_data = json.loads(decoded)

        transaction_uuid = payment_data.get("transaction_uuid")
        total_amount     = payment_data.get("total_amount")
        status           = payment_data.get("status")

        if status != "COMPLETE":
            return HTMLResponse(content=error_page("Payment not completed"), status_code=400)

        # Verify with eSewa API
        async with httpx.AsyncClient() as client:
            verify_response = await client.get(
                ESEWA_VERIFY_URL,
                params={
                    "product_code":     ESEWA_MERCHANT_CODE,
                    "total_amount":     total_amount,
                    "transaction_uuid": transaction_uuid,
                }
            )

        verify_data = verify_response.json()

        if verify_data.get("status") != "COMPLETE":
            return HTMLResponse(content=error_page("Payment verification failed"), status_code=400)

        # Update payment in DB
        payment = db.query(Payment).filter(
            Payment.transaction_id == transaction_uuid
        ).first()

        if not payment:
            return HTMLResponse(content=error_page("Payment record not found"), status_code=404)

        payment.status   = "completed"
        payment.paid_at  = datetime.utcnow()

        # Update job status
        job = db.query(Job).filter(Job.id == payment.job_id).first()
        if job:
            job.status      = "accepted"
            job.accepted_at = datetime.utcnow()

        db.commit()

        return HTMLResponse(content=success_page(payment.amount, transaction_uuid))

    except Exception as e:
        return HTMLResponse(content=error_page(f"Error: {str(e)}"), status_code=500)


# ════════════════════════════════════════════════════════
# FAILURE CALLBACK
# ════════════════════════════════════════════════════════
@router.get("/esewa/failure")
def esewa_failure(db: Session = Depends(get_db)):
    """eSewa redirects here if payment fails or user cancels."""
    return HTMLResponse(content=error_page("Payment cancelled or failed. Please try again."))


# ════════════════════════════════════════════════════════
# CHECK PAYMENT STATUS
# ════════════════════════════════════════════════════════
@router.get("/status/{job_id}")
def payment_status(job_id: str, db: Session = Depends(get_db)):
    """Check current payment status for a job."""
    payment = db.query(Payment).filter(Payment.job_id == job_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="No payment found for this job")

    return {
        "job_id":          job_id,
        "amount":          payment.amount,
        "worker_earning":  payment.worker_earning,
        "platform_fee":    payment.platform_fee,
        "status":          payment.status,
        "method":          payment.method,
        "transaction_id":  payment.transaction_id,
        "paid_at":         payment.paid_at,
    }


# ════════════════════════════════════════════════════════
# HTML RESPONSE PAGES
# ════════════════════════════════════════════════════════
def success_page(amount: int, transaction_id: str) -> str:
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Payment Successful — SewaBot</title>
        <style>
            body {{ font-family: Arial, sans-serif; background: #0a0b0f;
                    color: white; display: flex; align-items: center;
                    justify-content: center; height: 100vh; margin: 0; }}
            .card {{ background: #1a1d26; border: 1px solid #00d4aa;
                    border-radius: 16px; padding: 40px; text-align: center; }}
            .icon {{ font-size: 64px; margin-bottom: 16px; }}
            h1 {{ color: #00d4aa; }}
            .amount {{ font-size: 32px; font-weight: bold; margin: 16px 0; }}
            .txn {{ color: #888; font-size: 12px; margin-top: 8px; }}
            .btn {{ background: #00d4aa; color: #000; border: none;
                    padding: 12px 32px; border-radius: 8px; font-size: 16px;
                    font-weight: bold; cursor: pointer; margin-top: 24px;
                    text-decoration: none; display: inline-block; }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="icon">✅</div>
            <h1>Payment Successful!</h1>
            <div class="amount">Rs. {amount}</div>
            <p>Your worker has been notified and is on the way.</p>
            <div class="txn">Transaction ID: {transaction_id}</div>
            <a href="/" class="btn">Back to SewaBot</a>
        </div>
    </body>
    </html>
    """

def error_page(message: str) -> str:
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Payment Failed — SewaBot</title>
        <style>
            body {{ font-family: Arial, sans-serif; background: #0a0b0f;
                    color: white; display: flex; align-items: center;
                    justify-content: center; height: 100vh; margin: 0; }}
            .card {{ background: #1a1d26; border: 1px solid #ff4757;
                    border-radius: 16px; padding: 40px; text-align: center; }}
            .icon {{ font-size: 64px; margin-bottom: 16px; }}
            h1 {{ color: #ff4757; }}
            .btn {{ background: #ff4757; color: white; border: none;
                    padding: 12px 32px; border-radius: 8px; font-size: 16px;
                    font-weight: bold; cursor: pointer; margin-top: 24px;
                    text-decoration: none; display: inline-block; }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="icon">❌</div>
            <h1>Payment Failed</h1>
            <p>{message}</p>
            <a href="/" class="btn">Try Again</a>
        </div>
    </body>
    </html>
    """