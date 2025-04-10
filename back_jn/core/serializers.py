from rest_framework import serializers
from .models import User, Profile, Video, Certificado
from django.contrib.auth import get_user_model

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'matricula', 'email', 'password', 'created_at']

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User.objects.create(**validated_data)
        user.set_password(password)
        user.save()
        return user


User = get_user_model()

class ProfileSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())

    class Meta:
        model = Profile
        fields = ['id', 'user', 'level', 'area']

    def create(self, validated_data):
        user = validated_data.pop('user')

        # Se o perfil já existir, atualiza
        if hasattr(user, 'profile'):
            perfil = user.profile
            for attr, value in validated_data.items():
                setattr(perfil, attr, value)
            perfil.save()
            return perfil

        # Se não existir, cria normalmente
        profile = Profile.objects.create(user=user, **validated_data)
        return profile


class VideoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Video
        fields = '__all__'


class CertificadoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Certificado
        fields = '__all__'