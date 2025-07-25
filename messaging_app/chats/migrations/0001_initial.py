# Generated by Django 5.2.4 on 2025-07-18 01:13

import django.contrib.auth.models
import django.contrib.auth.validators
import django.db.models.deletion
import django.utils.timezone
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="User",
            fields=[
                ("password", models.CharField(max_length=128, verbose_name="password")),
                (
                    "last_login",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="last login"
                    ),
                ),
                (
                    "is_superuser",
                    models.BooleanField(
                        default=False,
                        help_text="Designates that this user has all permissions without explicitly assigning them.",
                        verbose_name="superuser status",
                    ),
                ),
                (
                    "username",
                    models.CharField(
                        error_messages={
                            "unique": "A user with that username already exists."
                        },
                        help_text="Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.",
                        max_length=150,
                        unique=True,
                        validators=[
                            django.contrib.auth.validators.UnicodeUsernameValidator()
                        ],
                        verbose_name="username",
                    ),
                ),
                (
                    "first_name",
                    models.CharField(
                        blank=True, max_length=150, verbose_name="first name"
                    ),
                ),
                (
                    "last_name",
                    models.CharField(
                        blank=True, max_length=150, verbose_name="last name"
                    ),
                ),
                (
                    "email",
                    models.EmailField(
                        blank=True, max_length=254, verbose_name="email address"
                    ),
                ),
                (
                    "is_staff",
                    models.BooleanField(
                        default=False,
                        help_text="Designates whether the user can log into this admin site.",
                        verbose_name="staff status",
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=True,
                        help_text="Designates whether this user should be treated as active. Unselect this instead of deleting accounts.",
                        verbose_name="active",
                    ),
                ),
                (
                    "date_joined",
                    models.DateTimeField(
                        default=django.utils.timezone.now, verbose_name="date joined"
                    ),
                ),
                (
                    "user_id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        help_text="Unique identifier for the user",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "phone_number",
                    models.CharField(
                        blank=True,
                        help_text="User's phone number",
                        max_length=20,
                        null=True,
                    ),
                ),
                (
                    "profile_picture",
                    models.ImageField(
                        blank=True,
                        help_text="User's profile picture",
                        null=True,
                        upload_to="profile_pictures/",
                    ),
                ),
                (
                    "is_online",
                    models.BooleanField(
                        default=False, help_text="Indicates if user is currently online"
                    ),
                ),
                (
                    "last_seen",
                    models.DateTimeField(
                        auto_now=True, help_text="Last time user was active"
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, help_text="Account creation timestamp"
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True, help_text="Last account update timestamp"
                    ),
                ),
                (
                    "groups",
                    models.ManyToManyField(
                        blank=True,
                        help_text="The groups this user belongs to. A user will get all permissions granted to each of their groups.",
                        related_name="user_set",
                        related_query_name="user",
                        to="auth.group",
                        verbose_name="groups",
                    ),
                ),
                (
                    "user_permissions",
                    models.ManyToManyField(
                        blank=True,
                        help_text="Specific permissions for this user.",
                        related_name="user_set",
                        related_query_name="user",
                        to="auth.permission",
                        verbose_name="user permissions",
                    ),
                ),
            ],
            options={
                "verbose_name": "User",
                "verbose_name_plural": "Users",
                "db_table": "users",
                "ordering": ["-created_at"],
            },
            managers=[
                ("objects", django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name="Conversation",
            fields=[
                (
                    "conversation_id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        help_text="Unique identifier for the conversation",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "title",
                    models.CharField(
                        blank=True,
                        help_text="Optional conversation title/name",
                        max_length=255,
                        null=True,
                    ),
                ),
                (
                    "is_group",
                    models.BooleanField(
                        default=False,
                        help_text="Indicates if this is a group conversation",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, help_text="Conversation creation timestamp"
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True, help_text="Last conversation update timestamp"
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        help_text="User who created this conversation",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="created_conversations",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "participants",
                    models.ManyToManyField(
                        help_text="Users participating in this conversation",
                        related_name="conversations",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Conversation",
                "verbose_name_plural": "Conversations",
                "db_table": "conversations",
                "ordering": ["-updated_at"],
            },
        ),
        migrations.CreateModel(
            name="Message",
            fields=[
                (
                    "message_id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        help_text="Unique identifier for the message",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("content", models.TextField(help_text="The actual message content")),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, help_text="Message creation timestamp"
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True, help_text="Last message update timestamp"
                    ),
                ),
                (
                    "is_read",
                    models.BooleanField(
                        default=False,
                        help_text="Indicates if the message has been read",
                    ),
                ),
                (
                    "is_edited",
                    models.BooleanField(
                        default=False,
                        help_text="Indicates if the message has been edited",
                    ),
                ),
                (
                    "conversation",
                    models.ForeignKey(
                        help_text="Conversation this message belongs to",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="messages",
                        to="chats.conversation",
                    ),
                ),
                (
                    "reply_to",
                    models.ForeignKey(
                        blank=True,
                        help_text="Message this is a reply to",
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="replies",
                        to="chats.message",
                    ),
                ),
                (
                    "sender",
                    models.ForeignKey(
                        help_text="User who sent this message",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sent_messages",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Message",
                "verbose_name_plural": "Messages",
                "db_table": "messages",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="MessageReadStatus",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "read_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        help_text="Timestamp when the message was read",
                    ),
                ),
                (
                    "message",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="read_statuses",
                        to="chats.message",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="message_read_statuses",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Message Read Status",
                "verbose_name_plural": "Message Read Statuses",
                "db_table": "message_read_statuses",
            },
        ),
        migrations.AddIndex(
            model_name="message",
            index=models.Index(
                fields=["conversation", "-created_at"],
                name="messages_convers_38b855_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="message",
            index=models.Index(
                fields=["sender", "-created_at"], name="messages_sender__7375e3_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="message",
            index=models.Index(fields=["is_read"], name="messages_is_read_6a69c0_idx"),
        ),
        migrations.AlterUniqueTogether(
            name="messagereadstatus",
            unique_together={("message", "user")},
        ),
    ]
