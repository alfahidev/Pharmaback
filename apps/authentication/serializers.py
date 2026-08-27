"""
Serializers for Authentication, Custom JWT Claims, and User Management.
"""
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import get_user_model
from tenancy.serializers import TenantSerializer

User = get_user_model()

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom JWT Serializer adding tenant and role claims into access tokens.
    """
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Inject custom claims
        token["user_id"] = user.id
        token["username"] = user.username
        token["email"] = user.email
        token["role"] = user.role
        token["phone"] = user.phone

        if user.pharmacy:
            token["tenant_id"] = str(user.pharmacy.id)
            token["pharmacy_name"] = user.pharmacy.name
            token["pharmacy_code"] = user.pharmacy.code
            subscription = getattr(user.pharmacy, "subscription", None)
            if subscription:
                token["subscription_status"] = subscription.status
                token["subscription_valid"] = subscription.is_currently_valid()
            else:
                token["subscription_status"] = "NONE"
                token["subscription_valid"] = False
        else:
            token["tenant_id"] = None
            token["pharmacy_name"] = None
            token["subscription_status"] = None
            token["subscription_valid"] = True

        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user

        data["user"] = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "phone": user.phone,
            "is_superuser": user.is_superuser,
            "pharmacy": {
                "id": str(user.pharmacy.id) if user.pharmacy else None,
                "name": user.pharmacy.name if user.pharmacy else None,
                "code": user.pharmacy.code if user.pharmacy else None,
                "is_active": user.pharmacy.is_active if user.pharmacy else None,
            } if user.pharmacy else None,
        }

        # Subscription metadata
        if user.pharmacy and hasattr(user.pharmacy, "subscription"):
            sub = user.pharmacy.subscription
            data["subscription"] = {
                "status": sub.status,
                "end_date": sub.end_date,
                "is_valid": sub.is_currently_valid(),
            }
        else:
            data["subscription"] = None

        return data


class UserSerializer(serializers.ModelSerializer):
    pharmacy_details = TenantSerializer(source="pharmacy", read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "phone",
            "role",
            "pharmacy",
            "pharmacy_details",
            "is_active",
            "date_joined",
            "last_login",
        ]
        read_only_fields = ["id", "pharmacy_details", "date_joined", "last_login"]


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=True, min_length=8)
    auto_generate_password = serializers.BooleanField(required=False, default=False, write_only=True)
    generated_password = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "password",
            "auto_generate_password",
            "generated_password",
            "first_name",
            "last_name",
            "phone",
            "role",
            "is_active",
        ]
        read_only_fields = ["id", "generated_password"]

    def create(self, validated_data):
        import secrets
        import string

        auto_gen = validated_data.pop("auto_generate_password", False)
        password = validated_data.pop("password", "").strip()

        if not password or auto_gen:
            # Generate a secure 10-char password (e.g., Pharma#8249K)
            chars = string.ascii_letters + string.digits
            rand_str = "".join(secrets.choice(chars) for _ in range(8))
            password = f"Pharma@{rand_str}"
            self._plain_password = password
        else:
            self._plain_password = password

        request = self.context.get("request")
        if request and request.user and request.user.pharmacy:
            validated_data["pharmacy"] = request.user.pharmacy

        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        return user

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if hasattr(self, "_plain_password"):
            data["generated_password"] = self._plain_password
        return data


class UserProfileSerializer(serializers.ModelSerializer):
    pharmacy = TenantSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "phone",
            "role",
            "pharmacy",
            "is_active",
            "date_joined",
        ]
        read_only_fields = ["id", "role", "pharmacy", "date_joined"]
