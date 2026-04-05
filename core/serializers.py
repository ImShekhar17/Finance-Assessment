from rest_framework import serializers
from .models import User, FinancialRecord

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'password', 'role', 
            'mobile_number', 'application_id', 'membership_id', 
            'name', 'is_active'
        ]

class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=5)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'mobile_number', 'name', 'role']

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            mobile_number=validated_data.get('mobile_number'),
            name=validated_data.get('name', ''),
            role=validated_data.get('role', 'VIEWER'),
            is_active=False  # Set to inactive until OTP is verified
        )
        return user

class FinancialRecordSerializer(serializers.ModelSerializer):
    user_name = serializers.ReadOnlyField(source='user.username')

    class Meta:
        model = FinancialRecord
        fields = [
            'id', 'user', 'user_name', 'amount', 'type', 
            'category', 'date', 'description', 'created_at'
        ]
        read_only_fields = ['user', 'created_at']

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value

class ResetPasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(write_only=True, min_length=5)
