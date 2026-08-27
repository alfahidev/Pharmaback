"""
Serializers for Tenancy and SaaS Subscription Management.
"""
from datetime import timedelta
from django.utils import timezone
from rest_framework import serializers
from tenancy.models import Tenant, SubscriptionPlan, TenantSubscription

class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = [
            "id",
            "name",
            "code",
            "description",
            "price",
            "duration_days",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class TenantSubscriptionSerializer(serializers.ModelSerializer):
    plan_details = SubscriptionPlanSerializer(source="plan", read_only=True)
    is_valid = serializers.BooleanField(source="is_currently_valid", read_only=True)

    class Meta:
        model = TenantSubscription
        fields = [
            "id",
            "tenant",
            "plan",
            "plan_details",
            "status",
            "start_date",
            "end_date",
            "is_active",
            "is_valid",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "is_valid"]


class TenantSerializer(serializers.ModelSerializer):
    subscription = TenantSubscriptionSerializer(read_only=True)

    class Meta:
        model = Tenant
        fields = [
            "id",
            "name",
            "code",
            "license_number",
            "phone",
            "address",
            "city",
            "logo",
            "is_active",
            "subscription",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "subscription"]


class OwnerInputSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=False, allow_blank=True, min_length=8)
    auto_generate_password = serializers.BooleanField(required=False, default=False)
    first_name = serializers.CharField(required=False, allow_blank=True, default="")
    last_name = serializers.CharField(required=False, allow_blank=True, default="")
    phone = serializers.CharField(required=False, allow_blank=True, default="")


class TenantCreateSerializer(serializers.ModelSerializer):
    initial_duration_days = serializers.IntegerField(required=False, default=30, write_only=True)
    initial_status = serializers.ChoiceField(
        choices=TenantSubscription.STATUS_CHOICES,
        default="ACTIVE",
        write_only=True
    )
    owner = OwnerInputSerializer(required=False, write_only=True)

    class Meta:
        model = Tenant
        fields = [
            "id",
            "name",
            "code",
            "license_number",
            "phone",
            "address",
            "city",
            "logo",
            "is_active",
            "initial_duration_days",
            "initial_status",
            "owner",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def create(self, validated_data):
        import secrets
        import string
        from django.contrib.auth import get_user_model

        User = get_user_model()
        duration_days = validated_data.pop("initial_duration_days", 30)
        initial_status = validated_data.pop("initial_status", "ACTIVE")
        owner_data = validated_data.pop("owner", None)

        tenant = Tenant.objects.create(**validated_data)

        # Get or create the single plan
        plan, _ = SubscriptionPlan.objects.get_or_create(
            code="standard_pro",
            defaults={
                "name": "PLAN UNIQUE PRO",
                "price": 30000.00,
                "duration_days": 30,
                "description": "Plan complet POS, Stocks FEFO, Crédits & Comptabilité",
            }
        )

        # Attach default subscription
        start = timezone.now()
        end = start + timedelta(days=duration_days)
        subscription = TenantSubscription.objects.create(
            tenant=tenant,
            plan=plan,
            status=initial_status,
            start_date=start,
            end_date=end,
            is_active=True,
            notes="Abonnement initial créé à l'enregistrement de l'officine."
        )

        # Create Pharmacy Owner (Titulaire) if owner details provided
        if owner_data:
            auto_gen = owner_data.get("auto_generate_password", False)
            password = owner_data.get("password", "").strip()

            if not password or auto_gen:
                chars = string.ascii_letters + string.digits
                rand_str = "".join(secrets.choice(chars) for _ in range(8))
                password = f"Pharma@{rand_str}"
                self._owner_plain_password = password
            else:
                self._owner_plain_password = password

            owner_user = User.objects.create_user(
                username=owner_data["username"],
                email=owner_data["email"],
                first_name=owner_data.get("first_name", ""),
                last_name=owner_data.get("last_name", ""),
                phone=owner_data.get("phone", ""),
                role="ADMIN",
                pharmacy=tenant,
            )
            owner_user.set_password(password)
            owner_user.save()
            self._created_owner = owner_user

        return tenant

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if hasattr(self, "_created_owner"):
            owner = self._created_owner
            data["owner"] = {
                "id": owner.id,
                "username": owner.username,
                "email": owner.email,
                "first_name": owner.first_name,
                "last_name": owner.last_name,
                "phone": owner.phone,
                "role": owner.role,
                "generated_password": getattr(self, "_owner_plain_password", None),
            }
        if hasattr(instance, "subscription"):
            data["subscription"] = TenantSubscriptionSerializer(instance.subscription).data
        return data
