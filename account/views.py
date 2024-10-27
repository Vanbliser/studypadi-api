from django.shortcuts import render
from rest_framework.generics import GenericAPIView
from .serializers import UserRegisterSerializer, VerifyOTPSerializer, ResendOTPSerializer, LoginSerializer, ForgetPasswordSerializer
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .tasks import send_otp, verify_otp, generate_otp
from .models import User


# Create your views here.

class RegisterUserView(GenericAPIView):
    """User registration view
    """

    serializer_class = UserRegisterSerializer

    def post(self, request):
        """handle post request"""

        user_data = request.data
        serializer = self.serializer_class(data=user_data)

        if serializer.is_valid(raise_exception=True):
            serializer.save()
            user = serializer.data
            otp = generate_otp(user['email'])
            print(otp)
            send_otp.delay(otp, user['email'])
            return Response({
                'user': user,
                'message': "An OTP has been sent to the registered email"
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VerifyOTPView(GenericAPIView):

    serializer_class = VerifyOTPSerializer

    def post(self, request):
        user_data = request.data
        serializer = self.serializer_class(data=user_data)

        if serializer.is_valid(raise_exception=True):
            otp = request.data.get('otp')
            email = request.data.get("email")
            try:
                user = User.objects.get(email=email)
                if user.is_verified:
                    return Response({"message": "User already verified", "email": email})
                is_valid = verify_otp(int(otp), email)
                if is_valid:
                    user.is_verified=True
                    user.save()
                return Response({"message": is_valid, "email": user.email}, status=status.HTTP_200_OK)
            except User.DoesNotExist:
                return Response({'message': 'User does not exist', "email": email}, status=status.HTTP_400_BAD_REQUEST)
            except ValueError:
                return Response({'message': 'Too many attempts. Please try again later.', "email": email}, status=status.HTTP_200_OK)
            except:
                return Response({'message': 'Unknown error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ResendOTPView(GenericAPIView):
    serializer_class = ResendOTPSerializer

    def post(self, request):
        user_data = request.data
        serializer = self.serializer_class(data=user_data)

        if serializer.is_valid(raise_exception=True):
            email = request.data.get('email')
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                return Response({'email': email, 'message': 'Email does not exist'}, status=status.HTTP_400_BAD_REQUEST)
            if user.is_verified:
                return Response({"message": "User already verified", "email": email})
            otp = generate_otp(email)
            print(otp)
            send_otp.delay(otp, email)
            return Response({
                'email': user.email,
                'message': "An OTP has been sent to the registered email"
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class LoginView(GenericAPIView):
    serializer_class = LoginSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class TestAuthView(GenericAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = {
            'msg': 'working'
        }
        return Response(data=data, status=status.HTTP_200_OK)