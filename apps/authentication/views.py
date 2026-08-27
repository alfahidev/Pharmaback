"""
Views for JWT Login, User Profile, and Staff Management.
"""
from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from drf_spectacular.utils import extend_schema
from django.contrib.auth import get_user_model
from apps.authentication.serializers import (
    CustomTokenObtainPairSerializer,
    UserSerializer,
    UserCreateSerializer,
    UserProfileSerializer,
)
from tenancy.permissions import IsTenantAdmin

User = get_user_model()

class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Login endpoint returning access/refresh tokens with embedded tenant and role claims.
    """
    serializer_class = CustomTokenObtainPairSerializer

    @extend_schema(
        summary="Connexion utilisateur & obtention du token JWT",
        description="Authentifie l'utilisateur et renvoie les tokens JWT contenant les revendications d'officine et de rôle."
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class UserProfileView(APIView):
    """
    Endpoint for viewing and updating current user's profile.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Profil de l'utilisateur connecté",
        responses={200: UserProfileSerializer}
    )
    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)

    @extend_schema(
        summary="Mise à jour du profil de l'utilisateur",
        request=UserProfileSerializer,
        responses={200: UserProfileSerializer}
    )
    def patch(self, request):
        serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class PharmacyUserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Pharmacy Owners/Admins to manage their team members.
    """
    permission_classes = [IsTenantAdmin]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.role == "SAAS_OWNER":
            return User.objects.all().select_related("pharmacy")
        if user.pharmacy:
            return User.objects.filter(pharmacy=user.pharmacy).select_related("pharmacy")
        return User.objects.none()

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        return UserSerializer

    def perform_create(self, serializer):
        user = self.request.user
        if user.pharmacy:
            serializer.save(pharmacy=user.pharmacy)
        elif user.is_superuser:
            serializer.save()
