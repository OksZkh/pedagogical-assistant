import httpx
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from asgiref.sync import sync_to_async
from .models import ChatMessage
import json

# === Синхронные функции для ORM (обёрнуты в sync_to_async) ===
@sync_to_async
def create_user_sync(username, password):
    return User.objects.create_user(username=username, password=password)

@sync_to_async
def get_user_by_username_sync(username):
    try:
        return User.objects.get(username=username)
    except User.DoesNotExist:
        return None

@sync_to_async
def save_password_sync(user, new_password):
    user.set_password(new_password)
    user.save()

@sync_to_async
def get_chat_history_sync(user, limit=20):
    msgs = ChatMessage.objects.filter(user=user).order_by("-created_at")
    if limit is not None:
        queryset = msgs[:limit]
    return list(reversed(msgs))

@sync_to_async
def save_message_sync(user, role, content):
    return ChatMessage.objects.create(user=user, role=role, content=content)

# === Аутентификация (синхронная, так как регистрация редкая) ===
def register(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        password2 = request.POST["password2"]
        if password != password2:
            messages.error(request, "Пароли не совпадают")
            return render(request, "registration/register.html")
        if User.objects.filter(username=username).exists():
            messages.error(request, "Пользователь уже существует")
            return render(request, "registration/register.html")
        user = User.objects.create_user(username=username, password=password)
        login(request, user)
        return redirect("chat")
    return render(request, "registration/register.html")

def password_reset(request):
    if request.method == "POST":
        username = request.POST["username"]
        new_password = request.POST["new_password"]
        new_password2 = request.POST["new_password2"]
        if new_password != new_password2:
            messages.error(request, "Новые пароли не совпадают")
            return render(request, "registration/password_reset.html")
        try:
            user = User.objects.get(username=username)
            user.set_password(new_password)
            user.save()
            messages.success(request, "Пароль изменён. Войдите снова.")
            return redirect("login")
        except User.DoesNotExist:
            messages.error(request, "Пользователь не найден")
            return render(request, "registration/password_reset.html")
    return render(request, "registration/password_reset.html")

@login_required
def chat_page(request):
    return render(request, "chat.html")

@login_required
async def api_history(request):
    history = await get_chat_history_sync(request.user, limit=None)
    result = [
        {"role": msg.role, "content": msg.content}
        for msg in history
    ]
    return JsonResponse(result, safe=False)

@csrf_exempt
@require_http_methods(["POST"])
@login_required
async def send_message(request):
    data = json.loads(request.body)
    user_msg = data.get("message", "").strip()
    if not user_msg:
        return JsonResponse({"error": "Сообщение пустое"}, status=400)

    # Сохраняем сообщение пользователя
    await save_message_sync(request.user, "user", user_msg)

    # Получаем историю
    history = await get_chat_history_sync(request.user, limit=10)
    # Фильтруем историю: убираем повторяющиеся ошибки и проверяем последовательность
    messages_for_api = []
    last_role = None

    for msg in history:
        # Пропускаем подряд идущие сообщения от одного role
        if msg.role == last_role:
            continue
        messages_for_api.append({"role": msg.role, "content": msg.content})
        last_role = msg.role

    # Убедимся, что последнее сообщение - от пользователя
    if messages_for_api and messages_for_api[-1]["role"] != "user":
        messages_for_api.append({"role": "user", "content": user_msg})
    elif not messages_for_api:
        messages_for_api = [{"role": "user", "content": user_msg}]


    # Асинхронный вызов FastAPI
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                "https://YOUR_ADRESS/generate",
                json={"messages": messages_for_api, "max_new_tokens": 200},
            )
            if resp.status_code == 200:
                bot_response = resp.json()["response"]
            else:
                bot_response = "Ошибка генерации."
    except Exception as e:
        bot_response = "Не удалось подключиться к модели."

    # Сохраняем ответ
    await save_message_sync(request.user, "assistant", bot_response)

    return JsonResponse({"response": bot_response})