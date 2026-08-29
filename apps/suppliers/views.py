"""
Views for Wholesaler Suppliers, Purchase Orders, Automated Replenishment, and Claims.
"""
import csv
import io
from datetime import date, timedelta
from decimal import Decimal
from django.db import transaction
from django.db.models import Sum, Q
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
from common.viewsets import TenantModelViewSet
from common.utils import parse_flexible_date, parse_decimal_safe, generate_ticket_number
from apps.suppliers.models import Supplier, PurchaseOrder, PurchaseOrderItem, SupplierClaim
from apps.suppliers.serializers import (
    SupplierSerializer,
    PurchaseOrderSerializer,
    PurchaseOrderCreateSerializer,
    SupplierClaimSerializer,
)
from apps.inventory.models import PharmacyProduct, ProductBatch, StockMovement
from apps.pos.models import SaleItem
from tenancy.permissions import IsPharmacistOrAbove

class SupplierViewSet(TenantModelViewSet):
    """
    Wholesaler supplier management.
    """
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [IsPharmacistOrAbove]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "phone", "contact_person"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]


class PurchaseOrderViewSet(TenantModelViewSet):
    """
    Wholesaler purchase orders, replenishment generation, delivery intake and CSV export.
    """
    queryset = PurchaseOrder.objects.all().select_related("supplier", "created_by").prefetch_related("items", "items__product")
    permission_classes = [IsPharmacistOrAbove]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["order_number", "supplier__name", "notes"]
    ordering_fields = ["created_at", "total_amount_ht"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "create":
            return PurchaseOrderCreateSerializer
        return PurchaseOrderSerializer

    def create(self, request, *args, **kwargs):
        serializer = PurchaseOrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        pharmacy = request.user.pharmacy
        if not pharmacy:
            return Response({"error": "Utilisateur non rattaché à une officine."}, status=status.HTTP_400_BAD_REQUEST)

        supplier_id = serializer.validated_data["supplier_id"]
        supplier = Supplier.objects.filter(tenant=pharmacy, id=supplier_id, is_active=True).first()
        if not supplier:
            return Response({"error": "Fournisseur introuvable ou inactif."}, status=status.HTTP_400_BAD_REQUEST)

        items_data = serializer.validated_data["items"]
        notes = serializer.validated_data.get("notes", "")

        with transaction.atomic():
            order = PurchaseOrder.objects.create(
                tenant=pharmacy,
                supplier=supplier,
                order_number=generate_ticket_number("CMD"),
                status="DRAFT",
                total_amount_ht=Decimal("0.00"),
                notes=notes,
                created_by=request.user,
            )

            total_ht = Decimal("0.00")
            for item in items_data:
                product = PharmacyProduct.objects.filter(tenant=pharmacy, id=item["product_id"]).first()
                if not product:
                    continue
                unit_price = Decimal(str(item.get("unit_purchase_price", product.purchase_price_ht)))
                qty = item["quantity_ordered"]
                PurchaseOrderItem.objects.create(
                    tenant=pharmacy,
                    order=order,
                    product=product,
                    quantity_ordered=qty,
                    quantity_received=0,
                    unit_purchase_price=unit_price,
                )
                total_ht += unit_price * qty

            order.total_amount_ht = total_ht
            order.save()

        return Response(PurchaseOrderSerializer(order).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Générer une proposition de commande selon les ventes et seuils critiques",
        parameters=[
            OpenApiParameter(name="period", description="Période d'analyse: 'today' ou 'week'", required=False, type=str),
            OpenApiParameter(name="supplier_id", description="ID du fournisseur grossiste", required=False, type=int),
        ],
        responses={200: PurchaseOrderSerializer}
    )
    @action(detail=False, methods=["post"], url_path="generate-from-sales")
    def generate_from_sales(self, request):
        pharmacy = request.user.pharmacy
        if not pharmacy:
            return Response({"error": "Utilisateur non rattaché à une officine."}, status=status.HTTP_400_BAD_REQUEST)

        period = request.query_params.get("period", "week").lower()
        supplier_id = request.query_params.get("supplier_id") or request.data.get("supplier_id")

        if supplier_id:
            supplier = Supplier.objects.filter(tenant=pharmacy, id=supplier_id, is_active=True).first()
        else:
            supplier = Supplier.objects.filter(tenant=pharmacy, is_active=True).first()

        if not supplier:
            return Response(
                {"error": "Aucun fournisseur disponible. Veuillez créer un fournisseur avant de générer une commande."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Date range
        now = timezone.now()
        start_date = now.date() if period == "today" else (now - timedelta(days=7)).date()

        # Find products sold during period
        sold_items = SaleItem.objects.filter(
            tenant=pharmacy,
            sale__created_at__date__gte=start_date,
            sale__status__in=["PAID", "CREDIT"]
        ).values("product_id").annotate(total_sold=Sum("quantity"))

        sold_map = {item["product_id"]: item["total_sold"] for item in sold_items}

        # Select products needing replenishment (low stock or recently sold)
        all_products = PharmacyProduct.objects.filter(tenant=pharmacy, is_active=True).prefetch_related("batches")
        suggested_items = []

        for p in all_products:
            current_stock = p.total_stock
            sold_qty = sold_map.get(p.id, 0)
            threshold = p.reorder_threshold

            # Condition: Stock is below/equal threshold OR sold > 0 and stock is low
            if current_stock <= threshold or (sold_qty > 0 and current_stock < threshold * 2):
                reorder_qty = max(threshold * 2 - current_stock, sold_qty, 10)
                suggested_items.append({
                    "product": p,
                    "quantity": reorder_qty,
                    "unit_price": p.purchase_price_ht,
                })

        if not suggested_items:
            return Response(
                {"detail": "Aucun produit n'a atteint son seuil de réapprovisionnement sur la période."},
                status=status.HTTP_200_OK
            )

        with transaction.atomic():
            order = PurchaseOrder.objects.create(
                tenant=pharmacy,
                supplier=supplier,
                order_number=generate_ticket_number("CMD"),
                status="DRAFT",
                total_amount_ht=Decimal("0.00"),
                notes=f"Proposition automatique générée selon l'historique des ventes ({period}).",
                created_by=request.user,
            )

            total_ht = Decimal("0.00")
            for item in suggested_items:
                p = item["product"]
                qty = item["quantity"]
                price = item["unit_price"]
                PurchaseOrderItem.objects.create(
                    tenant=pharmacy,
                    order=order,
                    product=p,
                    quantity_ordered=qty,
                    quantity_received=0,
                    unit_purchase_price=price,
                )
                total_ht += price * qty

            order.total_amount_ht = total_ht
            order.save()

        return Response(PurchaseOrderSerializer(order).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Importer le bon de livraison CSV et réceptionner le stock",
        description="Met à jour la commande en statut REÇU, crée les lots et dates de péremption, et incrémente le stock.",
        request={"multipart/form-data": {"type": "object", "properties": {"file": {"type": "string", "format": "binary"}}}},
        responses={200: OpenApiResponse(description="Résultat de la réception")}
    )
    @action(detail=True, methods=["post"], url_path="import-delivery-csv")
    def import_delivery_csv(self, request, pk=None):
        order = self.get_object()
        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response({"error": "Veuillez fournir un fichier CSV sous le champ 'file'."}, status=status.HTTP_400_BAD_REQUEST)

        pharmacy = request.user.pharmacy
        try:
            raw = file_obj.read()
            try:
                content = raw.decode("utf-8")
            except UnicodeDecodeError:
                content = raw.decode("iso-8859-1")

            sample = content[:2048]
            delimiter = ";" if ";" in sample and sample.count(";") > sample.count(",") else ","
            reader = csv.DictReader(io.StringIO(content), delimiter=delimiter)

            headers = {h.strip().lower(): h for h in (reader.fieldnames or [])}

            def get_col(row, *candidates):
                for cand in candidates:
                    for h_norm, h_orig in headers.items():
                        if cand.lower() in h_norm:
                            return row.get(h_orig, "").strip()
                return ""

            received_count = 0
            batches_created = 0

            with transaction.atomic():
                for row in reader:
                    barcode = get_col(row, "code-barre", "code 1", "code_1", "barcode", "cip")
                    product_name = get_col(row, "label", "désignation", "designation", "nom", "produit")
                    batch_num = get_col(row, "lot", "numéro de lot", "batch", "batch_number") or f"LIV-{timezone.now().strftime('%Y%m%d')}"
                    expiry_str = get_col(row, "péremption", "peremption", "date", "expiration", "expiry")
                    qty_str = get_col(row, "quantité reçue", "quantite reçue", "quantité", "quantite", "qty", "received")
                    price_str = get_col(row, "prix achat", "prix unitaire", "unit_price", "prix")

                    qty = int(float(qty_str)) if qty_str else 0
                    if qty <= 0:
                        continue

                    parsed_expiry = parse_flexible_date(expiry_str) or (date.today() + timedelta(days=365))
                    purchase_price = parse_decimal_safe(price_str)

                    # Match product
                    product = None
                    if barcode:
                        product = PharmacyProduct.objects.filter(
                            tenant=pharmacy,
                            barcode=barcode
                        ).first()

                    if not product and product_name:
                        product = PharmacyProduct.objects.filter(
                            tenant=pharmacy,
                            name__icontains=product_name
                        ).first()

                    if not product:
                        # Create product if completely new
                        product = PharmacyProduct.objects.create(
                            tenant=pharmacy,
                            barcode=barcode or f"PROD-{timezone.now().strftime('%Y%m%d%H%M%S')}",
                            name=product_name or f"Produit {barcode}",
                            purchase_price_ht=purchase_price,
                            selling_price=purchase_price * Decimal("1.30") if purchase_price > 0 else Decimal("1000.00"),
                            reorder_threshold=10,
                        )

                    # Update purchase order item if linked
                    order_item = PurchaseOrderItem.objects.filter(order=order, product=product).first()
                    if order_item:
                        order_item.quantity_received += qty
                        if purchase_price > 0:
                            order_item.unit_purchase_price = purchase_price
                        order_item.save()

                    # Create or update ProductBatch
                    batch, b_created = ProductBatch.objects.get_or_create(
                        tenant=pharmacy,
                        product=product,
                        batch_number=batch_num,
                        defaults={
                            "expiration_date": parsed_expiry,
                            "quantity_received": qty,
                            "quantity_current": qty,
                            "is_active": True,
                        }
                    )
                    if not b_created:
                        batch.quantity_received += qty
                        batch.quantity_current += qty
                        batch.expiration_date = parsed_expiry
                        batch.save()

                    batches_created += 1
                    received_count += qty

                    # Log StockMovement
                    StockMovement.objects.create(
                        tenant=pharmacy,
                        product=product,
                        batch=batch,
                        movement_type="IN_PURCHASE",
                        quantity=qty,
                        reference_doc=order.order_number,
                        created_by=request.user,
                        notes=f"Réception commande {order.order_number} - Grossiste {order.supplier.name}",
                    )

                order.status = "RECEIVED"
                order.save()

            return Response({
                "status": "success",
                "message": "Bon de livraison réceptionné avec succès et stock mis à jour.",
                "total_quantity_received": received_count,
                "batches_processed": batches_created,
                "order_status": order.status,
            })

        except Exception as e:
            return Response({"error": f"Erreur lors de la réception du bon de livraison: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Exporter la commande au format CSV pour portail grossiste (Laborex/Cophase...)",
        responses={200: OpenApiResponse(description="Fichier CSV prêt pour le portail grossiste")}
    )
    @action(detail=True, methods=["get"], url_path="export-csv")
    def export_csv(self, request, pk=None):
        order = self.get_object()
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        filename = f"commande-{order.order_number}-{order.supplier.name}.csv"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        writer = csv.writer(response, delimiter=";")
        writer.writerow(["Code CIP / Barcode", "Désignation Produit", "Quantité Commandée", "Prix Achat Estimé HT"])

        for item in order.items.all().select_related("product"):
            writer.writerow([
                item.product.barcode,
                item.product.name,
                item.quantity_ordered,
                f"{item.unit_purchase_price:.2f}",
            ])

        order.status = "EXPORTED"
        order.save()
        return response


class SupplierClaimViewSet(TenantModelViewSet):
    """
    Supplier delivery dispute and claims management.
    """
    queryset = SupplierClaim.objects.all().select_related("supplier", "order", "created_by")
    serializer_class = SupplierClaimSerializer
    permission_classes = [IsPharmacistOrAbove]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["product_name", "batch_number", "supplier__name", "description"]
    ordering_fields = ["created_at", "status"]
    ordering = ["-created_at"]

    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(tenant=user.pharmacy, created_by=user)
