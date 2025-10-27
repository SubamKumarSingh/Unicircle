# fundraisers/views.py
from decimal import Decimal, InvalidOperation
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpResponseForbidden, JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Fundraiser, Donation
from .forms import FundraiserCreateForm


import stripe
from django.conf import settings

from django.views.decorators.csrf import csrf_exempt
import json
from django.db import transaction

stripe.api_key = settings.STRIPE_SECRET_KEY

@require_POST
def create_checkout_session(request, pk):

    fundraiser = get_object_or_404(Fundraiser, pk=pk, active=True)
    amount_raw = request.POST.get("amount")
    try:
        amount_dec = Decimal(str(amount_raw))
    except Exception:
        return JsonResponse({"error": "Invalid amount"}, status=400)
    if amount_dec <= 0:
        return JsonResponse({"error": "Amount must be > 0"}, status=400)

    # Stripe expects smallest currency unit (paise)
    amount_paise = int(amount_dec * 100)

    try:
        # create Checkout Session
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="payment",
            line_items=[{
                "price_data": {
                    "currency": "inr",
                    "product_data": {"name": f"Donation — {fundraiser.title}"},
                    "unit_amount": amount_paise,
                },
                "quantity": 1,
            }],
            metadata={
                "fundraiser_id": str(fundraiser.pk),
                "user_id": str(request.user.pk) if request.user.is_authenticated else "anonymous",
            },
            success_url=request.build_absolute_uri(fundraiser.get_absolute_url()) + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=request.build_absolute_uri(fundraiser.get_absolute_url()) + "?canceled=1",
        )
    except Exception as e:
        return JsonResponse({"error": "Stripe error: " + str(e)}, status=500)

    # create pending donation record (status pending)
    donation = Donation.objects.create(
        fundraiser=fundraiser,
        user=request.user if request.user.is_authenticated else None,
        amount=amount_dec,
        currency="INR",
        payment_method=Donation.PAYMENT_EXTERNAL,
        status=Donation.STATUS_PENDING,
        stripe_session_id=session.id
    )

    return JsonResponse({
        "ok": True,
        "sessionId": session.id,
        "publishableKey": settings.STRIPE_PUBLISHABLE_KEY
    })



# @csrf_exempt
# @require_POST
# def stripe_webhook(request):
#     payload = request.body
#     sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')
#     webhook_secret = settings.STRIPE_WEBHOOK_SECRET  # set from stripe listen output or dashboard

#     try:
#         event = stripe.Webhook.construct_event(payload=payload, sig_header=sig_header, secret=webhook_secret)
#     except ValueError:
#         return HttpResponse(status=400)
#     except stripe.error.SignatureVerificationError:
#         return HttpResponse(status=400)

#     # Handle the event
#     if event['type'] == 'checkout.session.completed':
#         session = event['data']['object']
#         # session contains metadata we set earlier
#         fundraiser_id = session.get('metadata', {}).get('fundraiser_id')
#         # Look up donation by session id, mark succeeded & update fundraiser totals
#         with transaction.atomic():
#             donation = Donation.objects.select_for_update().filter(stripe_session_id=session.get('id')).first()
#             if donation and donation.status != Donation.STATUS_SUCCEEDED:
#                 donation.status = Donation.STATUS_SUCCEEDED
#                 donation.stripe_payment_intent = session.get('payment_intent')
#                 donation.stripe_payment_status = session.get('payment_status')
#                 donation.save(update_fields=['status', 'stripe_payment_intent', 'stripe_payment_status'])
#                 f = Fundraiser.objects.select_for_update().get(pk=donation.fundraiser_id)
#                 f.raised = (f.raised or Decimal("0.00")) + donation.amount
#                 f.donors_count = (f.donors_count or 0) + 1
#                 f.save(update_fields=['raised', 'donors_count'])

#     # Return 200 for received events
#     return HttpResponse(status=200)


@csrf_exempt
@require_POST
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    webhook_secret = settings.STRIPE_WEBHOOK_SECRET

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)

    # Example: handle checkout.session.completed
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        print("Payment succeeded for session:", session.get("id"))

    return HttpResponse(status=200)


@login_required(login_url='unicircleapp:landingpage')
def fundraiser_list(request):
    """
    Combined view:
      - GET  → show fundraiser list + create form (your orangered page)
      - POST → handle new fundraiser creation
    Template: fundraisers/list.html
    """
    if request.method == "POST":
        if not request.user.is_authenticated:
            messages.error(request, "Please sign in to create a fundraiser.")
            return redirect("account_login")

        form = FundraiserCreateForm(request.POST, request.FILES)
        if form.is_valid():
            fundraiser = form.save(commit=False)
            fundraiser.owner = request.user
            fundraiser.save()
            messages.success(request, "Fundraiser created successfully!")
            return redirect("fundraisers:allfundraiserspage")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = FundraiserCreateForm()

    fundraisers = Fundraiser.objects.all().order_by("-created_at")
    paginator = Paginator(fundraisers, 12)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "fundraisers.html", {
        "fundraisers": page_obj,
        "form": form,
    })

@csrf_exempt
def fundraiser_detail(request, pk):
    fundraiser = get_object_or_404(Fundraiser, pk=pk, active=True)
    
    return redirect("fundraisers:allfundraiserspage")

    # return render(request, "fundraisers-detail.html", {"fundraiser": fundraiser})


@login_required
@require_POST
def donate_view(request, pk):
    """
    Create a Donation record.
    - offline => mark succeeded immediately
    - external/card => return pending (gateway integration point)
    """
    fundraiser = get_object_or_404(Fundraiser, pk=pk, active=True)
    amount_raw = request.POST.get("amount")
    payment_method = request.POST.get("payment_method") or Donation.PAYMENT_OFFLINE

    try:
        amount = Decimal(str(amount_raw))
    except (InvalidOperation, TypeError):
        return JsonResponse({"error": "Invalid amount"}, status=400)

    if amount <= 0:
        return JsonResponse({"error": "Amount must be greater than 0"}, status=400)

    donation = Donation.objects.create(
        fundraiser=fundraiser,
        user=request.user,
        amount=amount,
        currency="INR",
        payment_method=payment_method,
        status=Donation.STATUS_PENDING,
    )

    # Offline donations are instantly marked successful
    if payment_method == Donation.PAYMENT_OFFLINE:
        donation.mark_succeeded()
        messages.success(request, "Thank you! Your offline donation has been recorded.")
        return JsonResponse({"ok": True, "status": "succeeded", "redirect": fundraiser.get_absolute_url()})

    # External/card flow placeholder (for Stripe later)
    return JsonResponse({
        "ok": True,
        "status": "pending",
        "donation_id": donation.id,
        "message": "Proceed to external payment gateway (to be implemented)."
    })


@login_required
@require_POST
def fundraiser_close(request, pk):
    """
    Owner-only: close (deactivate) the fundraiser so donations cannot be made.
    """
    fundraiser = get_object_or_404(Fundraiser, pk=pk)
    if fundraiser.owner_id != request.user.id:
        return HttpResponseForbidden("Only the owner can perform this action.")

    # close but do not mark completed
    fundraiser.active = False
    fundraiser.save(update_fields=["active", "updated_at"])
    return JsonResponse({"ok": True, "action": "closed", "pk": pk})


@login_required
@require_POST
def fundraiser_mark_completed(request, pk):
    """
    Owner-only: mark fundraiser as completed.
    By default we also set active=False so donations are blocked once completed.
    """
    fundraiser = get_object_or_404(Fundraiser, pk=pk)
    if fundraiser.owner_id != request.user.id:
        return HttpResponseForbidden("Only the owner can perform this action.")

    force = request.POST.get("force", "1")  # keep for future extension
    fundraiser.completed = True
    # optionally also deactivate
    fundraiser.active = False
    fundraiser.save(update_fields=["completed", "active", "updated_at"])
    return JsonResponse({"ok": True, "action": "completed", "pk": pk})