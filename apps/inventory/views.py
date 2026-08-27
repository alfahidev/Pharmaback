"""
Views for Pharmacy Inventory, CSV Import/Export, and Batch Management.
"""
import csv
import io
from datetime import date, timedelta
from decimal import Decimal
from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
from common.viewsets import TenantModelViewSet, TenantAPIView
from common.utils import parse_flexible_date, parse_decimal_safe
from apps.inventory.models import PharmacyProduct, ProductBatch, StockMovement
from apps.inventory.serializers import (
    PharmacyProductSerializer,
    ProductBatchSerializer,
    StockMovementSerializer,
    QuickRestockSerializer,
)
from tenancy.permissions import IsPharmacistOrAbove

class PharmacyProductViewSet(TenantModelViewSet):
    """
    CRUD endpoints for pharmacy private products and stock.
    Supports filtering by low_stock, expiring_soon, and search.
    """
    queryset = PharmacyProduct.objects.all().prefetch_related("batches")
    serializer_class = PharmacyProductSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["barcode", "alternate_barcode", "name", "shelf_location"]
    ordering_fields = ["name", "barcode", "selling_price", "created_at"]
    ordering = ["name"]

    def get_queryset(self):
        qs = super().get_queryset()
        low_stock = self.request.query_params.get("low_stock")
        expiring = self.request.query_params.get("expiring_soon")

        if low_stock and low_stock.lower() in ("true", "1", "yes"):
            # Filter in Python / custom aggregation
            product_ids = [p.id for p in qs if p.is_low_stock]
            qs = qs.filter(id__in=product_ids)

        if expiring and expiring.lower() in ("true", "1", "yes"):
            today = date.today()
            cutoff = today + timedelta(days=90)
            qs = qs.filter(
                batches__is_active=True,
                batches__quantity_current__gt=0,
                batches__expiration_date__gte=today,
                batches__expiration_date__lte=cutoff,
            ).distinct()

        return qs

    @extend_schema(
        summary="Réapprovisionnement express d'un produit par code-barres",
        description="Permet d'ajouter une quantité reçue pour un produit scanné (par code principal ou alternatif) et met à jour instantanément le stock disponible et les lots FEFO.",
        request=QuickRestockSerializer,
        responses={200: PharmacyProductSerializer}
    )
    @action(detail=False, methods=["post"], url_path="quick-restock")
    def quick_restock(self, request):
        serializer = QuickRestockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        pharmacy = request.user.pharmacy
        if not pharmacy:
            return Response({"error": "Utilisateur non rattaché à une officine."}, status=status.HTTP_400_BAD_REQUEST)

        barcode = serializer.validated_data["barcode"].strip()
        quantity = serializer.validated_data["quantity"]
        batch_number = serializer.validated_data.get("batch_number", "").strip()
        expiration_date = serializer.validated_data.get("expiration_date")
        purchase_price_ht = serializer.validated_data.get("purchase_price_ht")
        selling_price = serializer.validated_data.get("selling_price")

        from django.db.models import Q
        product = PharmacyProduct.objects.filter(
            tenant=pharmacy,
            is_active=True
        ).filter(
            Q(barcode=barcode) | Q(alternate_barcode=barcode)
        ).prefetch_related("batches").first()

        if not product:
            return Response(
                {"error": f"Aucun produit trouvé avec le code-barres '{barcode}'."},
                status=status.HTTP_404_NOT_FOUND
            )

        with transaction.atomic():
            # Update prices if provided
            if purchase_price_ht is not None:
                product.purchase_price_ht = purchase_price_ht
            if selling_price is not None:
                product.selling_price = selling_price
            if purchase_price_ht is not None or selling_price is not None:
                product.save()

            # Resolve expiration date
            if not expiration_date:
                nearest = product.nearest_expiration_date
                expiration_date = nearest if nearest and nearest > date.today() else (date.today() + timedelta(days=365))

            # Resolve batch number
            if not batch_number:
                batch_number = f"LOT-REAP-{expiration_date.strftime('%Y%m')}-{product.barcode[-4:]}"

            # Create or increment ProductBatch
            batch, created = ProductBatch.objects.get_or_create(
                tenant=pharmacy,
                product=product,
                batch_number=batch_number,
                defaults={
                    "expiration_date": expiration_date,
                    "quantity_received": quantity,
                    "quantity_current": quantity,
                    "is_active": True,
                }
            )
            if not created:
                batch.quantity_received += quantity
                batch.quantity_current += quantity
                batch.expiration_date = expiration_date
                batch.is_active = True
                batch.save()

            # Record StockMovement audit trail
            StockMovement.objects.create(
                tenant=pharmacy,
                product=product,
                batch=batch,
                movement_type="IN_PURCHASE",
                quantity=quantity,
                reference_doc="REAPPRO_EXPRESS",
                created_by=request.user,
                notes=f"Réapprovisionnement express (+{quantity} unités) - Lot {batch_number}",
            )

        product.refresh_from_db()
        return Response(PharmacyProductSerializer(product).data, status=status.HTTP_200_OK)



class ProductBatchViewSet(TenantModelViewSet):
    """
    Management of individual product batches / lots.
    """
    queryset = ProductBatch.objects.all().select_related("product")
    serializer_class = ProductBatchSerializer
    permission_classes = [IsPharmacistOrAbove]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["batch_number", "product__name", "product__barcode"]
    ordering_fields = ["expiration_date", "quantity_current", "created_at"]
    ordering = ["expiration_date"]


class StockMovementViewSet(TenantModelViewSet):
    """
    Audit log of all stock movements.
    """
    queryset = StockMovement.objects.all().select_related("product", "batch", "created_by")
    serializer_class = StockMovementSerializer
    permission_classes = [IsPharmacistOrAbove]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["product__name", "product__barcode", "reference_doc", "notes"]
    ordering = ["-created_at"]


class InventoryCSVImportView(TenantAPIView):
    """
    Imports stock CSV formatted according to the standard pharmacy schema:
    'Code 1', 'Code 2', 'Code géo', 'Label', 'Quantité', 'Prix unitaire d'achat HT',
    'Prix unitaire de vente', 'Date de péremption la plus proche'
    """
    permission_classes = [IsPharmacistOrAbove]

    @extend_schema(
        summary="Importation de stock depuis fichier CSV",
        description="Parse le fichier CSV d'export standard de stock et met à jour le catalogue privé et les lots FEFO.",
        request={"multipart/form-data": {"type": "object", "properties": {"file": {"type": "string", "format": "binary"}}}},
        responses={200: OpenApiResponse(description="Bilan de l'importation")}
    )
    def post(self, request):
        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response({"error": "Veuillez fournir un fichier CSV sous le champ 'file'."}, status=status.HTTP_400_BAD_REQUEST)

        pharmacy = getattr(request.user, "pharmacy", None)
        if not pharmacy:
            return Response({"error": "Utilisateur non rattaché à une officine."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Handle encoding
            raw_content = file_obj.read()
            try:
                decoded_file = raw_content.decode("utf-8")
            except UnicodeDecodeError:
                decoded_file = raw_content.decode("iso-8859-1")

            # Sniff delimiter
            sample = decoded_file[:2048]
            delimiter = ";" if ";" in sample and sample.count(";") > sample.count(",") else ","
            reader = csv.DictReader(io.StringIO(decoded_file), delimiter=delimiter)

            # Normalize headers
            headers = {h.strip().lower(): h for h in (reader.fieldnames or [])}

            def get_col(row, *candidates):
                for cand in candidates:
                    for h_norm, h_orig in headers.items():
                        if cand.lower() in h_norm:
                            return row.get(h_orig, "").strip()
                return ""

            created_count = 0
            updated_count = 0
            batches_created = 0
            errors = []

            with transaction.atomic():
                for idx, row in enumerate(reader, start=2):
                    barcode = get_col(row, "code 1", "code_1", "barcode", "cip", "code-barre")
                    if not barcode:
                        continue

                    name = get_col(row, "label", "désignation", "designation", "nom", "name") or f"Produit {barcode}"
                    alternate_barcode = get_col(row, "code 2", "code_2", "alternate")
                    shelf_location = get_col(row, "code géo", "code geo", "code_geo", "rayon", "emplacement")
                    purchase_price = parse_decimal_safe(get_col(row, "prix unitaire d'achat ht", "prix achat ht", "achat"))
                    selling_price = parse_decimal_safe(get_col(row, "prix unitaire de vente", "prix vente", "vente"), default=purchase_price)
                    qty_str = get_col(row, "quantité", "quantite", "qty", "quantity", "stock")
                    try:
                        qty = int(float(qty_str)) if qty_str else 0
                    except ValueError:
                        qty = 0

                    expiry_str = get_col(row, "date de péremption", "peremption", "expiry", "expiration")
                    parsed_expiry = parse_flexible_date(expiry_str) or (date.today() + timedelta(days=365))

                    # Update or create product
                    product, created = PharmacyProduct.all_objects.get_or_create(
                        tenant=pharmacy,
                        barcode=barcode,
                        defaults={
                            "name": name,
                            "alternate_barcode": alternate_barcode,
                            "shelf_location": shelf_location,
                            "purchase_price_ht": purchase_price,
                            "selling_price": selling_price,
                            "reorder_threshold": 10,
                            "is_active": True,
                        }
                    )

                    if created:
                        created_count += 1
                    else:
                        updated_count += 1
                        product.name = name or product.name
                        if alternate_barcode:
                            product.alternate_barcode = alternate_barcode
                        if shelf_location:
                            product.shelf_location = shelf_location
                        if purchase_price > 0:
                            product.purchase_price_ht = purchase_price
                        if selling_price > 0:
                            product.selling_price = selling_price
                        product.save()

                    # Create or update initial batch if quantity > 0
                    if qty > 0 or expiry_str:
                        batch_num = f"LOT-{parsed_expiry.strftime('%Y%m')}-{barcode[-4:]}"
                        batch, b_created = ProductBatch.all_objects.get_or_create(
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
                        if b_created:
                            batches_created += 1
                            StockMovement.all_objects.create(
                                tenant=pharmacy,
                                product=product,
                                batch=batch,
                                movement_type="IN_IMPORT",
                                quantity=qty,
                                reference_doc="IMPORT_CSV_INITIAL",
                                created_by=request.user,
                                notes="Importation initiale fichier CSV",
                            )

            return Response({
                "status": "success",
                "message": "Fichier CSV importé avec succès.",
                "created_products": created_count,
                "updated_products": updated_count,
                "batches_created": batches_created,
                "errors_count": len(errors),
            })

        except Exception as e:
            return Response({"error": f"Erreur lors du traitement du fichier CSV: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)


class InventoryCSVExportView(TenantAPIView):
    """
    Exports full pharmacy inventory to CSV format matching standard template.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Exportation du stock en CSV",
        description="Génère un fichier CSV contenant l'ensemble des stocks et dates de péremption de l'officine."
    )
    def get(self, request):
        pharmacy = getattr(request.user, "pharmacy", None)
        if not pharmacy:
            return Response({"error": "Utilisateur non rattaché à une officine."}, status=status.HTTP_400_BAD_REQUEST)

        response = HttpResponse(content_type="text/csv; charset=utf-8")
        filename = f"export-stocks-{pharmacy.code}-{timezone.now().strftime('%Y%m%d')}.csv"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        writer = csv.writer(response, delimiter=";")
        writer.writerow([
            "Code 1",
            "Code 2",
            "Code géo",
            "Label",
            "Quantité",
            "Prix unitaire d'achat HT",
            "Prix unitaire de vente",
            "Date de péremption la plus proche",
        ])

        products = PharmacyProduct.objects.filter(tenant=pharmacy, is_active=True).prefetch_related("batches")
        for product in products:
            nearest_exp = product.nearest_expiration_date
            exp_str = nearest_exp.strftime("%d/%m/%Y") if nearest_exp else ""
            writer.writerow([
                product.barcode,
                product.alternate_barcode,
                product.shelf_location,
                product.name,
                product.total_stock,
                f"{product.purchase_price_ht:.2f}",
                f"{product.selling_price:.2f}",
                exp_str,
            ])

        return response
