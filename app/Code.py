from django.db import models

class Code(models.Model):
    id = models.AutoField(primary_key=True)
    code = models.CharField(max_length=30)
    active = models.DateField()
    expire = models.DateField()
    status = models.IntegerField()

    class Meta:
        db_table = 'pt.CODES'
        indexes = [
            models.Index(fields=['code'], name='code_index'),
        ]
