from django.db import models


class User(models.Model):
    name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128) 
    role = models.CharField(max_length=5, default='stu')

    def __str__(self):
        return f'{self.name} {self.last_name} ({self.email})'


class Notification(models.Model):
    TYPE_LOAN_DUE = 'loan_due'
    TYPE_LOAN_OVERDUE = 'loan_overdue'
    TYPE_RESERVATION_READY = 'reservation_ready'
    
    TYPE_CHOICES = [
        (TYPE_LOAN_DUE, 'Loan Due Soon'),
        (TYPE_LOAN_OVERDUE, 'Loan Overdue'),
        (TYPE_RESERVATION_READY, 'Reservation Ready for Pickup'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    related_loan_id = models.IntegerField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.title} - {self.user.email}'