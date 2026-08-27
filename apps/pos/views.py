"""
Views for POS Caisse, Ultra-Fast Barcode Scanning, Checkout, and Cash Sessions.
"""
from decimal import Decimal
from django.db.models import Q
from django.utils import timezone
from rest_framework import viewsets, permissions, status, filters
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
from common.viewsets import TenantModelViewSet, TenantAPIView
from apps.pos.models import CashSession, Sale, SaleItem
from apps.pos.serializers import (
    SaleSerializer,
    CashSessionSerializer,
    CashSessionOpenSerializer,
    CashSessionCloseSerializer,
    POSScanResponseSerializer,
    CheckoutRequestSerializer,
)
from apps.pos.services import process_pos_checkout
from apps.inventory.models import PharmacyProduct
from tenancy.permissions import IsCashierOrAbove

class POSScanView(TenantAPIView):
    """
    Ultra-Fast POS Barcode Scan Endpoint (< 20ms response time).
    Accepts EAN-13, CIP, or secondary barcode and returns product with FEFO batch indicators.
    """
    permission_classes = [IsCashierOrAbove]

    @extend_schema(
        summary="Scan rapide de code-barres pour caisse POS",
        parameters=[
            OpenApiParameter(
                name="barcode",
                description="Code-barres EAN-13, CIP ou code alternatif",
                required=True,
                type=str
            )
        ],
        responses={200: POSScanResponseSerializer}
    )
    def get(self, request):
        barcode = request.query_params.get("barcode", "").strip()
        if not barcode:
            return Response({"error": "Le paramètre 'barcode' est requis."}, status=status.HTTP_400_BAD_REQUEST)

        pharmacy = request.user.pharmacy
        if not pharmacy:
            return Response({"error": "Utilisateur non rattaché à une officine."}, status=status.HTTP_400_BAD_REQUEST)

        product = PharmacyProduct.objects.filter(
            tenant=pharmacy,
            is_active=True
        ).filter(
            Q(barcode=barcode) | Q(alternate_barcode=barcode)
        ).prefetch_related("batches").first()

        if not product:
            return Response(
                {"error": f"Aucun produit trouvé pour le code-barres '{barcode}'."},
                status=status.HTTP_404_NOT_FOUND
            )

        data = {
            "id": product.id,
            "barcode": product.barcode,
            "alternate_barcode": product.alternate_barcode,
            "name": product.name,
            "shelf_location": product.shelf_location,
            "selling_price": product.selling_price,
            "total_stock": product.total_stock,
            "is_low_stock": product.is_low_stock,
            "is_expiring_soon": product.is_expiring_soon,
            "months_until_expiry": product.months_until_expiry,
            "nearest_expiration_date": product.nearest_expiration_date,
        }
        return Response(data)


class POSCheckoutView(TenantAPIView):
    """
    Atomic Checkout Endpoint: Validates ticket, decrements FEFO batches,
    updates cash session, debits customer accounts, and logs movements.
    """
    permission_classes = [IsCashierOrAbove]

    @extend_schema(
        summary="Encaissement et validation atomique du ticket de caisse",
        request=CheckoutRequestSerializer,
        responses={201: SaleSerializer}
    )
    def post(self, request):
        serializer = CheckoutRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        pharmacy = request.user.pharmacy
        if not pharmacy:
            return Response({"error": "Utilisateur non rattaché à une officine."}, status=status.HTTP_400_BAD_REQUEST)

        sale = process_pos_checkout(pharmacy, request.user, serializer.validated_data)
        return Response(SaleSerializer(sale).data, status=status.HTTP_201_CREATED)


class CashSessionOpenView(TenantAPIView):
    """
    Opens a daily cash session for the cashier or retrieves the existing open session.
    """
    permission_classes = [IsCashierOrAbove]

    @extend_schema(
        summary="Ouvrir une session de caisse",
        request=CashSessionOpenSerializer,
        responses={200: CashSessionSerializer}
    )
    def post(self, request):
        pharmacy = request.user.pharmacy
        if not pharmacy:
            return Response({"error": "Utilisateur non rattaché à une officine."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = CashSessionOpenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        initial_cash = serializer.validated_data.get("initial_cash", Decimal("0.00"))
        notes = serializer.validated_data.get("notes", "")

        # Check existing open session
        existing_session = CashSession.objects.filter(
            tenant=pharmacy,
            cashier=request.user,
            status="OPEN"
        ).first()

        if existing_session:
            return Response(CashSessionSerializer(existing_session).data, status=status.HTTP_200_OK)

        session = CashSession.objects.create(
            tenant=pharmacy,
            cashier=request.user,
            session_date=timezone.now().date(),
            initial_cash=initial_cash,
            expected_cash=initial_cash,
            status="OPEN",
            notes=notes,
        )
        return Response(CashSessionSerializer(session).data, status=status.HTTP_201_CREATED)


class CashSessionCloseView(TenantAPIView):
    """
    Closes the cashier's active session and calculates cash difference.
    """
    permission_classes = [IsCashierOrAbove]

    @extend_schema(
        summary="Clôturer la session de caisse et calculer l'écart",
        request=CashSessionCloseSerializer,
        responses={200: CashSessionSerializer}
    )
    def post(self, request):
        pharmacy = request.user.pharmacy
        if not pharmacy:
            return Response({"error": "Utilisateur non rattaché à une officine."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = CashSessionCloseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        actual_cash = serializer.validated_data["actual_cash_counted"]
        notes = serializer.validated_data.get("notes", "")

        session = CashSession.objects.filter(
            tenant=pharmacy,
            cashier=request.user,
            status="OPEN"
        ).first()

        if not session:
            return Response({"error": "Aucune session de caisse ouverte trouvée pour ce caissier."}, status=status.HTTP_404_NOT_FOUND)

        session.actual_cash_counted = actual_cash
        session.cash_difference = actual_cash - session.expected_cash
        session.status = "CLOSED"
        session.closed_at = timezone.now()
        if notes:
            session.notes = f"{session.notes} | {notes}".strip(" |")
        session.save()

        return Response(CashSessionSerializer(session).data)


class CurrentCashSessionView(TenantAPIView):
    """
    Returns the currently active cash session for the cashier.
    """
    permission_classes = [IsCashierOrAbove]

    @extend_schema(
        summary="Session de caisse active du caissier connecté",
        responses={200: CashSessionSerializer}
    )
    def get(self, request):
        pharmacy = request.user.pharmacy
        if not pharmacy:
            return Response({"error": "Utilisateur non rattaché à une officine."}, status=status.HTTP_400_BAD_REQUEST)

        session = CashSession.objects.filter(
            tenant=pharmacy,
            cashier=request.user,
            status="OPEN"
        ).first()

        if not session:
            return Response({"detail": "Aucune session ouverte actuellement.", "has_open_session": False}, status=status.HTTP_200_OK)

        return Response(CashSessionSerializer(session).data)


class SaleViewSet(TenantModelViewSet):
    """
    ViewSet for consulting and retrieving sales tickets.
    """
    queryset = Sale.objects.all().select_related("cash_session", "cashier", "customer").prefetch_related("items", "items__product", "items__batch")
    serializer_class = SaleSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["ticket_number", "customer__name", "cashier__username"]
    ordering_fields = ["created_at", "total_ttc"]
    ordering = ["-created_at"]


class CashSessionViewSet(TenantModelViewSet):
    """
    ViewSet for reviewing all historical cash sessions (Admin / Titulaire / Comptable).
    """
    queryset = CashSession.objects.all().select_related("cashier").prefetch_related("sales")
    serializer_class = CashSessionSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["cashier__username", "session_date"]
    ordering_fields = ["session_date", "opened_at", "cash_difference"]
    ordering = ["-opened_at"]
