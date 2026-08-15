from django.db import models


class User(models.Model):
    name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128) 
    role = models.CharField(max_length=5, default='stu')

    def __str__(self):
        return f'{self.name} {self.last_name} ({self.email})'