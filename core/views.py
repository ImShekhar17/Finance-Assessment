from rest_framework import viewsets, status, permissions, filters
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from django.db.models import Sum
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.hashers import make_password
import random
from datetime import timedelta

from .models import User, FinancialRecord
from drf_spectacular.utils import extend_schema, OpenApiParameter
from .serializers import UserSerializer, FinancialRecordSerializer, ResetPasswordSerializer, SignupSerializer
from .permissions import IsAdmin, IsAnalyst, IsViewer, IsOwnerOrAdmin

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    
    def get_permissions(self):
        if self.action == 'create':
            return [permissions.AllowAny()]
        return [IsAdmin()]

class FinancialRecordViewSet(viewsets.ModelViewSet):
    queryset = FinancialRecord.objects.all()
    serializer_class = FinancialRecordSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ['type', 'category', 'date']
    search_fields = ['description', 'category']
    ordering_fields = ['date', 'amount']

    def get_queryset(self):
        user = self.request.user
        base_queryset = FinancialRecord.objects.filter(deleted_at__isnull=True)
        if user.role == 'ADMIN':
            return base_queryset
        return base_queryset.filter(user=user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsViewer()]
        if self.action == 'create':
            return [IsAnalyst()]
        return [IsOwnerOrAdmin()]

class DashboardSummaryView(APIView):
    permission_classes = [IsViewer]

    @extend_schema(responses={200: dict})
    def get(self, request):
        user = request.user
        records = FinancialRecord.objects.filter(deleted_at__isnull=True)
        if user.role != 'ADMIN':
            records = records.filter(user=user)

        income_agg = records.filter(type='INCOME').aggregate(Sum('amount'))['amount__sum'] or 0
        expense_agg = records.filter(type='EXPENSE').aggregate(Sum('amount'))['amount__sum'] or 0
        
        total_income = float(income_agg)
        total_expense = float(expense_agg)
        net_balance = total_income - total_expense

        category_totals = []
        for item in records.values('category', 'type').annotate(total=Sum('amount')).order_by('-total'):
            category_totals.append({
                'category': item['category'],
                'type': item['type'],
                'total': float(item['total'] or 0)
            })

        recent_activity = FinancialRecordSerializer(records.order_by('-date', '-created_at')[:5], many=True).data

        return Response({
            'total_income': total_income,
            'total_expense': total_expense,
            'net_balance': net_balance,
            'category_totals': category_totals,
            'recent_activity': recent_activity,
            'role': user.role
        })


class LoginAPIView(APIView):
    """ API to authenticate users using multiple login methods """
    permission_classes = [AllowAny]

    @extend_schema(request=dict, responses={200: dict})
    def post(self, request):
        email = request.data.get("email")
        mobile_number = request.data.get("mobile_number")
        application_id = request.data.get("application_id")
        membership_id = request.data.get("membership_id")
        password = request.data.get("password")
        otp = request.data.get("otp")

        session = request.session

        # Case 1: Login with Email & Password
        if email and password:
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                return Response({"error": "User with this email does not exist."}, status=status.HTTP_400_BAD_REQUEST)
            return self.verify_password_login(user, password)

        # Case 2: Login with Mobile Number & Password
        elif mobile_number and password:
            try:
                user = User.objects.get(mobile_number=mobile_number)
            except User.DoesNotExist:
                return Response({"error": "User with this mobile number does not exist."}, status=status.HTTP_400_BAD_REQUEST)
            return self.verify_password_login(user, password)

        # Case 3: Login with Application ID & Password
        elif application_id and password:
            try:
                user = User.objects.get(application_id=application_id)
            except User.DoesNotExist:
                return Response({"error": "User with this application ID does not exist."}, status=status.HTTP_400_BAD_REQUEST)
            return self.verify_password_login(user, password)
        
        # Case 4: Login with Membership ID & Password
        elif membership_id and password:
            try:
                user = User.objects.get(membership_id=membership_id)
            except User.DoesNotExist:
                return Response({"error": "User with this membership ID does not exist."}, status=status.HTTP_400_BAD_REQUEST)
            return self.verify_password_login(user, password)

        # Case 5: Login with Email & OTP
        elif email and otp:
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                return Response({"error": "User with this email does not exist."}, status=status.HTTP_400_BAD_REQUEST)
            return self.verify_otp_login(session, user, otp)

        # Case 6: Login with Application ID & OTP
        elif application_id and otp:
            try:
                user = User.objects.get(application_id=application_id)
            except User.DoesNotExist:
                return Response({"error": "User with this application ID does not exist."}, status=status.HTTP_400_BAD_REQUEST)
            return self.verify_otp_login(session, user, otp)

        else:
            return Response({"error": "Invalid login credentials."}, status=status.HTTP_400_BAD_REQUEST)

    def verify_password_login(self, user, password):
        if not user.is_active:
            return Response({"error": "User account is inactive. Verify OTP first."}, status=status.HTTP_403_FORBIDDEN)
        if not user.check_password(password):
            return Response({"error": "Invalid password."}, status=status.HTTP_400_BAD_REQUEST)
        return self.generate_login_response(user)

    def generate_login_response(self, user):
        """ Generate response upon successful login """
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        return Response({
            "message": "Login successful.",
            "user": {
                "id": user.id,
                "email": user.email,
                "mobile_number": user.mobile_number,
                "application_id": user.application_id,
                "membership_id": user.membership_id,
                "name": user.name
            },
            "access": access_token,
            "refresh": str(refresh)
        }, status=status.HTTP_200_OK)

    def verify_otp_login(self, session, user, otp_input):
        """ Verify OTP for login """
        stored_otp = session.get("otp")
        otp_expiry_str = session.get("otp_expires_at")

        if not stored_otp or stored_otp != otp_input:
            return Response({"error": "Invalid OTP."}, status=status.HTTP_400_BAD_REQUEST)

        if not otp_expiry_str:
            return Response({"error": "OTP expiration time not found. Request a new OTP."}, status=status.HTTP_400_BAD_REQUEST)

        otp_expiry = timezone.datetime.fromisoformat(otp_expiry_str) if isinstance(otp_expiry_str, str) else otp_expiry_str

        if timezone.now() > otp_expiry:
            return Response({"error": "OTP has expired. Request a new OTP."}, status=status.HTTP_400_BAD_REQUEST)

        # Clear OTP session after successful verification
        for key in ["otp", "otp_expires_at", "email"]:
            session.pop(key, None)
        session.modified = True

        return self.generate_login_response(user)

class RequestPasswordResetAPIView(APIView):
    """ API to request password reset for logged-in user """
    permission_classes = [AllowAny]

    @extend_schema(request=dict, responses={200: dict})
    def post(self, request):
        email = request.data.get("email")
        if not email:
            return Response({"error": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"error": "User with this email does not exist."}, status=status.HTTP_400_BAD_REQUEST)

        # Generate a password reset token and encode user ID
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
        reset_url = f"{frontend_url}/reset-password/?uid={uid}&token={token}"

        # Send email with reset link
        send_mail(
            subject="Password Reset Request",
            message=f"Click the link to reset your password: {reset_url}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=True,
        )

        return Response({"message": "Password reset link sent to your email."}, status=status.HTTP_200_OK)


class ResetPasswordAPIView(APIView):
    """ API to reset password using token from query params """
    permission_classes = [AllowAny]

    @extend_schema(request=ResetPasswordSerializer, responses={200: dict})
    def post(self, request):
        uidb64 = request.query_params.get("uid")
        token = request.query_params.get("token")

        if not uidb64 or not token:
            return Response({"error": "Missing reset token or user ID."}, status=status.HTTP_400_BAD_REQUEST)

        # Decode user ID from base64
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (User.DoesNotExist, ValueError, TypeError):
            return Response({"error": "Invalid user ID."}, status=status.HTTP_400_BAD_REQUEST)

        # Validate the token
        if not default_token_generator.check_token(user, token):
            return Response({"error": "Invalid or expired token."}, status=status.HTTP_400_BAD_REQUEST)

        # Validate new password
        serializer = ResetPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Update user's password
        user.password = make_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])

        return Response({"message": "Password has been reset successfully."}, status=status.HTTP_200_OK)

def send_email_otp(email, otp_code):
    subject = "Your Verification OTP"
    message = f"Your verification code is: {otp_code}. It will expire in 5 minutes."
    from_email = settings.DEFAULT_FROM_EMAIL
    send_mail(subject, message, from_email, [email], fail_silently=True)

class SignupAPIView(APIView):
    permission_classes = [AllowAny]
    
    @extend_schema(request=SignupSerializer, responses={201: dict})
    def post(self, request):
        session = request.session
        email = request.data.get("email")

        if not email:
            return Response({
                "status_type": "missing_email",
                "message": "Email is required."
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)

            if user.is_active:
                return Response({
                    "status_type": "already_active",
                    "message": "User already registered with this email."
                }, status=status.HTTP_400_BAD_REQUEST)

            # User exists but is inactive -> resend OTP
            otp_code = str(random.randint(100000, 999999))
            now = timezone.now()
            session.update({
                "email": user.email,
                "otp": otp_code,
                "otp_expires_at": (now + timedelta(minutes=5)).isoformat(),
                "otp_requests": [now.isoformat()]
            })
            session.modified = True

            send_email_otp(user.email, otp_code)

            return Response({
                "status_type": "inactive_retry",
                "message": "User already exists but not verified. OTP has been resent."
            }, status=status.HTTP_200_OK)

        except User.DoesNotExist:
            # Brand new signup
            serializer = SignupSerializer(data=request.data)
            if not serializer.is_valid():
                return Response({
                    "status_type": "validation_error",
                    "errors": serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

            user = serializer.save()
            user.is_active = False
            user.save(update_fields=["is_active"])

            otp_code = str(random.randint(100000, 999999))
            now = timezone.now()
            session.update({
                "email": user.email,
                "otp": otp_code,
                "otp_expires_at": (now + timedelta(minutes=5)).isoformat(),
                "otp_requests": [now.isoformat()]
            })
            session.modified = True

            send_email_otp(user.email, otp_code)

            return Response({
                "status_type": "new_signup",
                "message": "Signup successful. OTP sent to your email."
            }, status=status.HTTP_201_CREATED)


class VerifyOTPAPIView(APIView):
    permission_classes = [AllowAny]
    
    @extend_schema(request=dict, responses={200: dict})
    def post(self, request):
        session = request.session
        otp_input = request.data.get("otp")
        email = request.data.get("email")

        if not email:
            return Response({"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)

        if not otp_input:
            return Response({"error": "Otp is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"error": "User with this email does not exist."}, status=status.HTTP_400_BAD_REQUEST)

        stored_otp = session.get("otp")
        otp_expiry_str = session.get("otp_expires_at")

        if not stored_otp or stored_otp != otp_input:
            return Response({"error": "Invalid OTP."}, status=status.HTTP_400_BAD_REQUEST)

        if not otp_expiry_str:
            return Response({"error": "OTP expiration time not found. Please request a new OTP."},
                            status=status.HTTP_400_BAD_REQUEST)

        # Convert string back to datetime
        otp_expiry = timezone.datetime.fromisoformat(otp_expiry_str)

        if timezone.now() > otp_expiry:
            return Response({"error": "OTP has expired. Request a new OTP."}, status=status.HTTP_400_BAD_REQUEST)

        # Activate user and generate application ID
        user.is_active = True
        if not user.application_id:
            user.application_id = user.generate_application_id()
        user.save(update_fields=["is_active", "application_id"])

        # Clear session data
        for key in ["otp", "otp_expires_at", "email"]:
            session.pop(key, None)
        session.modified = True

        # Send email to the user
        subject = "Your Application ID"
        message = f"Dear {user.name},\n\nYour application ID is: {user.application_id}.\n\nThank you for registering!"
        from_email = settings.DEFAULT_FROM_EMAIL
        recipient_list = [user.email]

        send_mail(subject, message, from_email, recipient_list)

        return Response({
            "message": "OTP verified. Signup complete. Application ID has been sent to your email.",
            "application_id": user.application_id
        }, status=status.HTTP_200_OK)

class ResendOTPAPIView(APIView):
    permission_classes = [AllowAny]
    
    @extend_schema(request=dict, responses={200: dict})
    def post(self, request):
        session = request.session
        email = session.get("email") or request.data.get("email")

        if not email:
            return Response({"error": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"error": "User with this email does not exist."}, status=status.HTTP_400_BAD_REQUEST)

        otp_requests = session.get("otp_requests", [])
        now = timezone.now()

        # Filter only recent (valid) OTP requests
        valid_otp_requests = [
            t for t in otp_requests
            if now - timezone.datetime.fromisoformat(t) < timedelta(minutes=10)
        ]

        if len(valid_otp_requests) >= 3:
            return Response({"error": "Too many OTP requests. Try again later."},
                            status=status.HTTP_429_TOO_MANY_REQUESTS)

        # Generate OTP
        otp_code = str(random.randint(100000, 999999))

        # Update session
        session["email"] = email
        session["otp"] = otp_code
        session["otp_expires_at"] = (now + timedelta(minutes=5)).isoformat()
        valid_otp_requests.append(now.isoformat())
        session["otp_requests"] = valid_otp_requests
        session.modified = True

        send_email_otp(email, otp_code)

        return Response({"message": "New OTP sent to your email."}, status=status.HTTP_200_OK)
