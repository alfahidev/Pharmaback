"""
Views for Tenancy and SaaS Owner Subscription Management.
"""
from datetime import timedelta
from django.utils import timezone
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiResponse
from tenancy.models import Tenant, SubscriptionPlan, TenantSubscription
from tenancy.serializers import (
    TenantSerializer,
    TenantCreateSerializer,
    SubscriptionPlanSerializer,
    TenantSubscriptionSerializer,
)
from tenancy.permissions import IsSaasOwner, IsTenantStaff, IsTenantAdmin

class SaasTenantViewSet(viewsets.ModelViewSet):
    """
    SaaS Platform Owner endpoints to manage pharmacies and their subscriptions.
    """
    queryset = Tenant.objects.all().select_related("subscription", "subscription__plan")
    permission_classes = [IsSaasOwner]

    def get_serializer_class(self):
        if self.action == "create":
            return TenantCreateSerializer
        return TenantSerializer

    @extend_schema(
        summary="Prolonger ou modifier manuellement un abonnement",
        request=TenantSubscriptionSerializer,
        responses={200: TenantSubscriptionSerializer}
    )
    @action(detail=True, methods=["patch", "put", "post"], url_path="subscription")
    def manage_subscription(self, request, pk=None):
        tenant = self.get_object()
        subscription, _ = TenantSubscription.objects.get_or_create(
            tenant=tenant,
            defaults={
                "plan": SubscriptionPlan.objects.first() or SubscriptionPlan.objects.create(
                    name="PLAN UNIQUE PRO", code="standard_pro", price=30000.00
                ),
                "end_date": timezone.now() + timedelta(days=30),
            }
        )

        serializer = TenantSubscriptionSerializer(subscription, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        from django.core.cache import cache
        cache.delete(f"sub_valid:{tenant.id}")
        return Response(serializer.data)

    @extend_schema(
        summary="Prolonger l'abonnement d'un nombre de jours",
        responses={200: TenantSubscriptionSerializer}
    )
    @action(detail=True, methods=["post"], url_path="extend-subscription")
    def extend_subscription(self, request, pk=None):
        tenant = self.get_object()
        subscription = getattr(tenant, "subscription", None)
        if not subscription:
            return Response({"error": "Aucun abonnement trouvé pour cette officine."}, status=status.HTTP_404_NOT_FOUND)

        days = int(request.data.get("days", 30))
        # Extend from current end_date if in future, else from now
        base_date = subscription.end_date if subscription.end_date > timezone.now() else timezone.now()
        subscription.end_date = base_date + timedelta(days=days)
        subscription.status = "ACTIVE"
        subscription.is_active = True
        subscription.save()

        from django.core.cache import cache
        cache.delete(f"sub_valid:{tenant.id}")

        return Response(TenantSubscriptionSerializer(subscription).data)

    @extend_schema(
        summary="Créer ou réinitialiser le compte Titulaire / Admin pour cette officine",
        request=TenantCreateSerializer,
        responses={201: OpenApiResponse(description="Titulaire créé avec succès")}
    )
    @action(detail=True, methods=["post"], url_path="create-owner")
    def create_owner(self, request, pk=None):
        import secrets
        import string
        from django.contrib.auth import get_user_model

        User = get_user_model()
        tenant = self.get_object()

        username = request.data.get("username", "").strip()
        email = request.data.get("email", "").strip()
        password = request.data.get("password", "").strip()
        auto_gen = request.data.get("auto_generate_password", False)
        first_name = request.data.get("first_name", "").strip()
        last_name = request.data.get("last_name", "").strip()
        phone = request.data.get("phone", "").strip()

        if not username or not email:
            return Response({"error": "Le champ 'username' et 'email' sont obligatoires."}, status=status.HTTP_400_BAD_REQUEST)

        if not password or auto_gen:
            chars = string.ascii_letters + string.digits
            rand_str = "".join(secrets.choice(chars) for _ in range(8))
            password = f"Pharma@{rand_str}"
            plain_pass = password
        else:
            plain_pass = password

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "phone": phone,
                "role": "ADMIN",
                "pharmacy": tenant,
            }
        )
        if not created:
            user.email = email
            user.first_name = first_name or user.first_name
            user.last_name = last_name or user.last_name
            user.phone = phone or user.phone
            user.role = "ADMIN"
            user.pharmacy = tenant

        user.set_password(password)
        user.save()

        return Response({
            "status": "success",
            "message": f"Compte Titulaire {'créé' if created else 'mis à jour'} avec succès pour l'officine {tenant.name}.",
            "owner": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "phone": user.phone,
                "role": user.role,
                "pharmacy_id": str(tenant.id),
                "generated_password": plain_pass,
            }
        }, status=status.HTTP_201_CREATED)


class SaasStatsView(APIView):
    """
    Overview statistics for the SaaS Platform Owner dashboard.
    """
    permission_classes = [IsSaasOwner]

    @extend_schema(
        summary="Statistiques globales de la plateforme SaaS",
        description="Renvoie le nombre d'officines actives, les abonnements en cours, le MRR estimé et le catalogue national."
    )
    def get(self, request):
        from apps.catalog.models import MedicamentCatalog
        total_tenants = Tenant.objects.count()
        active_subs = TenantSubscription.objects.filter(status="ACTIVE", is_active=True).count()
        trial_subs = TenantSubscription.objects.filter(status="TRIAL", is_active=True).count()
        expired_subs = TenantSubscription.objects.filter(status__in=["EXPIRED", "SUSPENDED"]).count()
        catalog_count = MedicamentCatalog.objects.count()

        # Monthly Recurring Revenue (MRR)
        plan = SubscriptionPlan.objects.first()
        mrr = (active_subs + trial_subs) * (plan.price if plan else Decimal("30000.00"))

        return Response({
            "total_pharmacies": total_tenants,
            "active_subscriptions": active_subs,
            "trial_subscriptions": trial_subs,
            "expired_subscriptions": expired_subs,
            "estimated_mrr": str(mrr),
            "catalog_medications_count": catalog_count,
        })


class SaasPlanViewSet(viewsets.ModelViewSet):
    """
    SaaS Owner endpoint to manage the unique subscription plan.
    """
    queryset = SubscriptionPlan.objects.all()
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [IsSaasOwner]


class PharmacySubscriptionStatusView(APIView):
    """
    Endpoint for tenant staff/admin to view their active subscription details.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Consulter l'état de l'abonnement de son officine",
        responses={200: TenantSubscriptionSerializer}
    )
    def get(self, request):
        user = request.user
        pharmacy = getattr(user, "pharmacy", None)
        if not pharmacy:
            return Response(
                {"detail": "L'utilisateur n'est rattaché à aucune officine."},
                status=status.HTTP_400_BAD_REQUEST
            )

        subscription = getattr(pharmacy, "subscription", None)
        if not subscription:
            return Response(
                {"detail": "Aucun abonnement enregistré pour cette officine.", "is_valid": False},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = TenantSubscriptionSerializer(subscription)
        return Response(serializer.data)


class PharmacyProfileView(APIView):
    """
    Endpoint for the pharmacy titular/admin to view and edit pharmacy information.
    """
    permission_classes = [IsTenantStaff]

    @extend_schema(
        summary="Consulter les informations de l'officine",
        responses={200: TenantSerializer}
    )
    def get(self, request):
        pharmacy = request.user.pharmacy
        if not pharmacy:
            return Response({"detail": "Aucune officine associée."}, status=400)
        return Response(TenantSerializer(pharmacy).data)

    @extend_schema(
        summary="Modifier les informations de l'officine (Titulaire/Admin uniquement)",
        request=TenantSerializer,
        responses={200: TenantSerializer}
    )
    def patch(self, request):
        if not (request.user.is_superuser or request.user.role in ("ADMIN", "TITULAIRE", "SAAS_OWNER")):
            return Response({"detail": "Permission refusée."}, status=status.HTTP_403_FORBIDDEN)
        pharmacy = request.user.pharmacy
        serializer = TenantSerializer(pharmacy, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
