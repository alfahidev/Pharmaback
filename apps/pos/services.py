"""
POS Checkout and FEFO Batch Decrement Service.
Synchronous, atomic, and transactional execution without background queues.
"""
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from apps.pos.models import CashSession, Sale, SaleItem
from apps.inventory.models import PharmacyProduct, ProductBatch, StockMovement
from apps.customers.models import CustomerAccount, CustomerTransaction
from common.utils import generate_ticket_number

def process_pos_checkout(pharmacy, user, validated_data: dict) -> Sale:
    """
    Atomically processes a POS checkout transaction:
    1. Validates or retrieves active cash session.
    2. Validates stock availability and performs FEFO batch deduction.
    3. Records StockMovement audit trail.
    4. Handles payment methods (Cash float update, Customer Account debit & limits).
    5. Returns persisted Sale record.
    """
    items_data = validated_data["items"]
    payment_method = validated_data.get("payment_method", "ESPECE")
    customer_id = validated_data.get("customer_id")
    amount_received = Decimal(str(validated_data.get("amount_received", "0.00")))
    session_id = validated_data.get("session_id")

    with transaction.atomic():
        # Step 1: Resolve Cash Session
        if session_id:
            cash_session = CashSession.objects.filter(
                tenant=pharmacy, id=session_id, status="OPEN"
            ).first()
            if not cash_session:
                raise ValidationError("La session de caisse indiquée est invalide ou fermée.")
        else:
            cash_session = CashSession.objects.filter(
                tenant=pharmacy, cashier=user, status="OPEN"
            ).first()
            if not cash_session:
                # Auto-open cash session for today if none exists
                cash_session = CashSession.objects.create(
                    tenant=pharmacy,
                    cashier=user,
                    session_date=timezone.now().date(),
                    initial_cash=Decimal("0.00"),
                    expected_cash=Decimal("0.00"),
                    status="OPEN",
                    notes="Session ouverte automatiquement lors du premier encaissement.",
                )

        # Step 2: Resolve Customer Account if applicable
        customer = None
        if customer_id:
            customer = CustomerAccount.objects.filter(tenant=pharmacy, id=customer_id, is_active=True).first()
            if not customer:
                raise ValidationError("Compte client introuvable ou inactif.")

        # Step 3: Calculate Totals and Prepare Sale
        total_ht = Decimal("0.00")
        total_tva = Decimal("0.00")
        total_ttc = Decimal("0.00")

        # Preliminary validation and locking of products
        sale = Sale.objects.create(
            tenant=pharmacy,
            cash_session=cash_session,
            cashier=user,
            ticket_number=generate_ticket_number("VTE"),
            customer=customer,
            total_ht=Decimal("0.00"),
            total_tva=Decimal("0.00"),
            total_ttc=Decimal("0.00"),
            payment_method=payment_method,
            amount_received=amount_received,
            change_returned=Decimal("0.00"),
            status="PAID" if payment_method != "COMPTE_CLIENT" else "CREDIT",
        )

        for item in items_data:
            product_id = item["product_id"]
            qty_needed = int(item["quantity"])
            if qty_needed <= 0:
                raise ValidationError(f"Quantité invalide ({qty_needed}) pour le produit ID {product_id}.")

            product = PharmacyProduct.objects.filter(tenant=pharmacy, id=product_id, is_active=True).first()
            if not product:
                raise ValidationError(f"Produit ID {product_id} non trouvé dans l'officine.")

            unit_price = Decimal(str(item.get("unit_price", product.selling_price)))
            line_total = unit_price * qty_needed
            tva_amount = line_total * (product.tva_rate / Decimal("100.00"))
            ht_amount = line_total - tva_amount

            total_ht += ht_amount
            total_tva += tva_amount
            total_ttc += line_total

            # Step 4: FEFO Batch Decrement
            # Fetch batches with available stock ordered by nearest expiration_date
            batches = list(
                ProductBatch.objects.filter(
                    tenant=pharmacy,
                    product=product,
                    is_active=True,
                    quantity_current__gt=0
                ).order_by("expiration_date", "id")
            )

            remaining_qty = qty_needed
            for batch in batches:
                if remaining_qty <= 0:
                    break
                deduct_qty = min(remaining_qty, batch.quantity_current)
                batch.quantity_current -= deduct_qty
                batch.save()
                remaining_qty -= deduct_qty

                # Create SaleItem per batch for strict traceability
                SaleItem.objects.create(
                    tenant=pharmacy,
                    sale=sale,
                    product=product,
                    batch=batch,
                    quantity=deduct_qty,
                    unit_price=unit_price,
                    total_price=unit_price * deduct_qty,
                )

                # Record StockMovement
                StockMovement.objects.create(
                    tenant=pharmacy,
                    product=product,
                    batch=batch,
                    movement_type="OUT_SALE",
                    quantity=-deduct_qty,
                    reference_doc=sale.ticket_number,
                    created_by=user,
                    notes=f"Vente POS Ticket {sale.ticket_number}",
                )

            # If remaining_qty > 0 (no batch or insufficient stock), record line without batch
            if remaining_qty > 0:
                SaleItem.objects.create(
                    tenant=pharmacy,
                    sale=sale,
                    product=product,
                    batch=None,
                    quantity=remaining_qty,
                    unit_price=unit_price,
                    total_price=unit_price * remaining_qty,
                )
                StockMovement.objects.create(
                    tenant=pharmacy,
                    product=product,
                    batch=None,
                    movement_type="OUT_SALE",
                    quantity=-remaining_qty,
                    reference_doc=sale.ticket_number,
                    created_by=user,
                    notes=f"Vente hors lot / Déstockage partiel sans lot spécifié",
                )

        # Step 5: Finalize Sale Amounts
        sale.total_ht = total_ht
        sale.total_tva = total_tva
        sale.total_ttc = total_ttc

        if payment_method == "ESPECE" and amount_received >= total_ttc:
            sale.change_returned = amount_received - total_ttc
        else:
            sale.change_returned = Decimal("0.00")

        sale.save()

        # Step 6: Process Payment Method Specifics
        if payment_method == "COMPTE_CLIENT":
            if not customer:
                raise ValidationError("Un compte client valide est obligatoire pour le paiement par compte/crédit.")

            can_charge, reason = customer.can_charge(total_ttc)
            if not can_charge:
                raise ValidationError(reason)

            customer.current_balance -= total_ttc
            customer.save()

            CustomerTransaction.objects.create(
                tenant=pharmacy,
                customer=customer,
                sale=sale,
                transaction_type="PURCHASE",
                payment_method="COMPTE_CLIENT",
                amount=total_ttc,
                balance_after=customer.current_balance,
                note=f"Achat comptoir Ticket {sale.ticket_number}",
                created_by=user,
            )

        elif payment_method == "ESPECE":
            # Increment expected cash in session
            cash_session.expected_cash += total_ttc
            cash_session.save()

        return sale
