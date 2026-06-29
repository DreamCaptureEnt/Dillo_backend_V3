from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Create or update a local demo staff user for the React admin dashboard.'

    def add_arguments(self, parser):
        parser.add_argument('--username', default='admin')
        parser.add_argument('--password', default='admin12345')
        parser.add_argument('--email', default='admin@dillo.local')

    def handle(self, *args, **options):
        User = get_user_model()
        user, _ = User.objects.get_or_create(username=options['username'])
        user.email = options['email']
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.set_password(options['password'])
        user.save()
        self.stdout.write(self.style.SUCCESS(f'Admin ready: {options["username"]} / {options["password"]}'))
