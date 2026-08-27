"""
Consolidated Financial Statement Calculations Service.
Computes Sales, Expenses, Gross Margins, Cash Breakdown, and Customer Debts.
"""
from datetime import date, timedelta
from decimal import Decimal
from django.db.models import Sum, Q, F
from django.utils import timezone
from apps.pos.models import Sale, SaleItem
from apps.billing.models import Expense
from apps.customers.models import CustomerAccount
from common.utils import parse_flexible_date

def calculate_financial_statement(
    pharmacy,
    period: str = "month",
    start_date: str | date | None = None,
    end_date: str | date | None = None,
    payment_method: str | None = None,
) -> dict:
    """
    Computes consolidated financial statement metrics for the given pharmacy and date interval.
    """
    today = timezone.now().date()

    # Determine date range
    if period == "today":
        start_d = today
        end_d = today
    elif period == "week":
        start_d = today - timedelta(days=7)
        end_d = today
    elif period == "month":
        start_d = today.replace(day=1)
        end_d = today
    elif period == "custom" and start_date:
        start_d = parse_flexible_date(str(start_date)) or today
        end_d = parse_flexible_date(str(end_date)) or today if end_date else today
    else:
        start_d = today.replace(day=1)
        end_d = today

    # Base Sales QuerySet
    sales_qs = Sale.objects.filter(
        tenant=pharmacy,
        created_at__date__gte=start_d,
        created_at__date__lte=end_d,
        status__in=["PAID", "CREDIT"]
    )

    if payment_method:
        sales_qs = sales_qs.filter(payment_method=payment_method)

    # Base Expenses QuerySet
    expenses_qs = Expense.objects.filter(
        tenant=pharmacy,
        date__gte=start_d,
        date__lte=end_d
    )
    if payment_method:
        expenses_qs = expenses_qs.filter(payment_method=payment_method)

    # Compute Aggregate Sales Totals
    sales_agg = sales_qs.aggregate(
        total_ttc=Sum("total_ttc"),
        total_ht=Sum("total_ht"),
        total_tva=Sum("total_tva"),
    )
    total_ventes_ttc = sales_agg["total_ttc"] or Decimal("0.00")
    total_ventes_ht = sales_agg["total_ht"] or Decimal("0.00")
    total_tva_collectee = sales_agg["total_tva"] or Decimal("0.00")
    total_tickets_count = sales_qs.count()

    # Compute Total Expenses
    expenses_agg = expenses_qs.aggregate(total_amount=Sum("amount"))
    total_depenses = expenses_agg["total_amount"] or Decimal("0.00")

    # Solde Net (Cashflow Net)
    solde_net = total_ventes_ttc - total_depenses

    # Compute Cost of Goods Sold (COGS) & Gross Margin
    sale_items = SaleItem.objects.filter(
        tenant=pharmacy,
        sale__in=sales_qs
    ).select_related("product")

    total_cogs = Decimal("0.00")
    for item in sale_items:
        product_purchase_price = item.product.purchase_price_ht if item.product else Decimal("0.00")
        total_cogs += product_purchase_price * item.quantity

    marge_brute_estimee = total_ventes_ht - total_cogs
    taux_marge_pourcentage = (
        round((marge_brute_estimee / total_ventes_ht) * 100, 2)
        if total_ventes_ht > Decimal("0.00") else Decimal("0.00")
    )
    panier_moyen = (
        round(total_ventes_ttc / total_tickets_count, 2)
        if total_tickets_count > 0 else Decimal("0.00")
    )

    # Payment Method Breakdown
    payment_methods_breakdown = {}
    for pm_code, pm_label in Sale.PAYMENT_METHOD_CHOICES:
        sub_total = sales_qs.filter(payment_method=pm_code).aggregate(s=Sum("total_ttc"))["s"] or Decimal("0.00")
        payment_methods_breakdown[pm_code] = {
            "label": str(pm_label),
            "total": str(sub_total),
            "percentage": round(float(sub_total / total_ventes_ttc * 100), 2) if total_ventes_ttc > 0 else 0.0,
        }

    # Expense Categories Breakdown
    expenses_categories_breakdown = []
    for exp in expenses_qs.values("category__name").annotate(total_cat=Sum("amount")).order_by("-total_cat"):
        expenses_categories_breakdown.append({
            "category": exp["category__name"] or "Non classé",
            "total": str(exp["total_cat"] or Decimal("0.00")),
        })

    # Customer Debts & Deposits
    customer_accounts = CustomerAccount.objects.filter(tenant=pharmacy, is_active=True)
    creances_total = Decimal("0.00")
    acomptes_total = Decimal("0.00")
    for acc in customer_accounts:
        if acc.current_balance < 0:
            creances_total += abs(acc.current_balance)
        else:
            acomptes_total += acc.current_balance

    return {
        "period": period,
        "start_date": str(start_d),
        "end_date": str(end_d),
        "pharmacy_name": pharmacy.name,
        "pharmacy_id": str(pharmacy.id),
        "total_ventes_ttc": str(total_ventes_ttc),
        "total_ventes_ht": str(total_ventes_ht),
        "total_tva_collectee": str(total_tva_collectee),
        "total_depenses": str(total_depenses),
        "solde_net": str(solde_net),
        "cout_achat_marchandises": str(total_cogs),
        "marge_brute_estimee": str(marge_brute_estimee),
        "taux_marge_pourcentage": float(taux_marge_pourcentage),
        "total_tickets_count": total_tickets_count,
        "panier_moyen": str(panier_moyen),
        "ventilation_modes_paiement": payment_methods_breakdown,
        "ventilation_categories_depenses": expenses_categories_breakdown,
        "creances_clients_total": str(creances_total),
        "acomptes_clients_total": str(acomptes_total),
    }
